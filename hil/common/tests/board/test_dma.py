"""
RU: ADC/DMA: владение блоком, реальная передача, обработка и отказ по таймауту.
EN: ADC/DMA block ownership, real transfer, processing and timeout recovery.

Конечный DMA-блок наблюдаем после отключения канала. Инъекции обработки выполняются
до старта DMA с полным снимком g_monitor; периферия в этих вызовах не участвует.
"""
import struct

import gdb

from stm32_gdbtest import case, within


# Восемь пар halfword: VREFINT, температура. Точность сравнения учитывает float32.
WORDS = 16
PAIRS = 8
FLOAT_EPS = 0.02


# call() пока не принимает namespace; прямой GDB исполняется в его основном потоке.
def process_block(t, count):
    result = bool(gdb.parse_and_eval(f"monitor::process(&g_monitor.raw[0], {count})"))
    t.record("processing.call", {"function": "monitor::process", "count": count, "returned": result})
    return result


# Настоящие DMA request/IRQ, неподвижный буфер и три последовательных блока.
@case("HW_DMA_CAPTURE", timeout_s=20, labels=("adc", "dma"))
def dma_capture(t):
    t.reach("monitor::arm")
    t.reach("board::delayMs")
    t.record("dma.config", {"ccr": t.evaluate("DMA1_Channel1->CCR"), "cr2": t.evaluate("ADC1->CR2")})

    # В момент стабилизации датчика DMA ещё выключен, CNDTR уже установлен.
    t.check([
        ("DMA clock enabled", "(RCC->AHBENR & RCC_AHBENR_DMA1EN) != 0", 1),
        ("DMA block length", "DMA1_Channel1->CNDTR", WORDS),
        ("DMA halfword normal mode", "DMA1_Channel1->CCR",
         "DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE"),
        ("DMA peripheral address", "DMA1_Channel1->CPAR", "(unsigned int)&ADC1->DR"),
        ("DMA owned buffer address", "DMA1_Channel1->CMAR", "(unsigned int)&g_monitor.raw[0]"),
        ("ADC scans two channels", "ADC1->SQR1 & ADC_SQR1_L", "ADC_SQR1_L_0"),
        ("ADC channel order", "ADC1->SQR3", 17 | (16 << 5)),
        ("ADC scan enabled", "ADC1->CR1 & ADC_CR1_SCAN", "ADC_CR1_SCAN"),
        ("ADC requests enabled", "ADC1->CR2 & ADC_CR2_DMA", "ADC_CR2_DMA")
    ])
    ccr = t.evaluate("(unsigned int)&DMA1_Channel1->CCR")
    cr2 = t.evaluate("(unsigned int)&ADC1->CR2")
    adc_mask = t.evaluate("ADC_CR2_ADON | ADC_CR2_DMA")
    t.reach("DMA1_Channel1_IRQHandler")

    # TC выставлен аппаратурой; чтение DR здесь не делаем, чтобы не менять состояние ADC.
    t.check([
        ("DMA IRQ context", "$xPSR & 511", "DMA1_Channel1_IRQn + 16"),
        ("DMA transfer completed", "(DMA1->ISR & DMA_ISR_TCIF1) != 0", 1),
        ("DMA count exhausted", "DMA1_Channel1->CNDTR", 0)
    ])

    # Пока процессор стоит в process, DMA остановлен и не меняет блок за спиной сценария.
    for number in range(1, 4):
        t.reach("monitor::process")
        address = int(gdb.parse_and_eval("&g_monitor.raw[0]"))
        data = t.memory(address, WORDS * 2)
        t.check("DMA snapshot complete", len(data), WORDS * 2)
        samples = list(struct.unpack("<16H", data))
        t.record("dma.block", {"number": number, "samples": samples, "irq": t.read("g_monitor.irq_count")})
        t.check("DMA disabled during processing", t.evaluate(f"*(unsigned int *){ccr}") & 1, 0)
        t.check("ADC stopped during processing", t.evaluate(f"*(unsigned int *){cr2}") & adc_mask, 0)
        t.check("all ADC samples are 12 bit", all(0 < value <= 4095 for value in samples))
        t.check("one IRQ per block", t.read("g_monitor.irq_count"), number)
        t.finish()
        t.check("block accepted exactly once", t.read("g_monitor.accepted"), number)
        t.check("DMA voltage plausible", t.evaluate("g_monitor.vdda_mv", as_type=float), within(2900, 3600))
        t.check("DMA temperature plausible", t.evaluate("g_monitor.temp_c", as_type=float), within(-10, 85))

    # Отсутствие ошибок — отдельное утверждение, а не вывод из среднего напряжения.
    t.check([
        ("no DMA transfer errors", "g_monitor.dma_errors", 0),
        ("no DMA timeouts", "g_monitor.timeouts", 0),
        ("monitor normal", "g_monitor.normal", 1)
    ])


# Подготовленные векторы проверяют C++ обработку на MCU независимо от аналогового шума.
@case("HW_DMA_PROCESS", timeout_s=20, labels=("adc", "processing", "injection"))
def dma_process(t):
    t.reach("monitor::poll")
    t.check("monitor not started", t.read("g_monitor.initialized"), 0)
    address = int(gdb.parse_and_eval("&g_monitor"))
    size = int(gdb.lookup_type("MonitorState").sizeof)
    saved = t.memory(address, size)
    t.check("whole monitor snapshot", len(saved), size)
    raw = int(gdb.parse_and_eval("&g_monitor.raw[0]"))

    # Функция не ждёт IRQ и не обращается к MMIO; передаём типизированный указатель GDB.
    try:
        t.memory(raw, struct.pack("<16H", *([1500, 1800] * PAIRS)))
        process_block(t, WORDS)
        voltage = t.evaluate("g_monitor.vdda_mv", as_type=float)
        temp = t.evaluate("g_monitor.temp_c", as_type=float)
        t.record("processing.first", {"vdda_mv": voltage, "temp_c": temp})
        t.check("first voltage seeds filter", abs(voltage - 3276.0) < FLOAT_EPS)
        t.check("temperature conversion", abs(temp - 22.6744186) < FLOAT_EPS)
        t.memory(raw, struct.pack("<16H", *([1560, 1800] * PAIRS)))
        process_block(t, WORDS)
        voltage = t.evaluate("g_monitor.vdda_mv", as_type=float)
        t.record("processing.second", {"vdda_mv": voltage})
        t.check("Kalman second voltage", abs(voltage - 3234.0) < FLOAT_EPS)
        process_block(t, WORDS - 1)
        t.memory(raw, struct.pack("<16H", *([1560, 1800] * 7 + [0, 1800])))
        process_block(t, WORDS)

        # Недопустимый последний отсчёт не должен частично обновлять фильтр.
        t.check([
            ("two valid blocks accepted", "g_monitor.accepted", 2),
            ("two invalid blocks rejected", "g_monitor.rejected", 2),
            ("bad block preserves filter", "g_monitor.vdda_mv", within(3234.0 - FLOAT_EPS, 3234.0 + FLOAT_EPS))
        ])
    finally:
        t.memory(address, saved)
        t.check("monitor state restored", t.memory(address, size), saved)


# Отключаем только генерацию DMA request: это модель отсутствующих данных, не поломка контроллера.
@case("HW_DMA_TIMEOUT", timeout_s=20, labels=("adc", "dma", "injection"))
def dma_timeout(t):
    t.reach("monitor::arm")
    t.reach("board::delayMs")
    saved = t.evaluate("ADC1->CR2")
    mask = t.evaluate("ADC_CR2_DMA")
    address = t.evaluate("(unsigned int)&ADC1->CR2")

    # Следующий arm сам вернёт штатную конфигурацию; finally возвращает бит и при исключении.
    try:
        t.write("ADC1->CR2", "ADC1->CR2 & ~ADC_CR2_DMA")
        t.reach("monitor::arm")
        t.record("dma.timeout", {"timeouts": t.read("g_monitor.timeouts"), "accepted": t.read("g_monitor.accepted")})

        # Таймаут освобождает оба устройства, но не выдаёт фиктивный результат.
        t.check([
            ("missing requests timed out", "g_monitor.timeouts", 1),
            ("timeout stops DMA", "DMA1_Channel1->CCR & DMA_CCR_EN", 0),
            ("timeout stops ADC", "ADC1->CR2 & ADC_CR2_ADON", 0),
            ("timeout publishes no block", "g_monitor.accepted", 0)
        ])
        t.reach("monitor::process")
        t.finish()
        t.check("next block recovers", t.read("g_monitor.accepted"), 1)
    finally:
        # Не запускаем ADC прежним CR2: возвращаем только изменённый бит в текущем состоянии.
        current = t.evaluate(f"*(unsigned int *){address}")
        t.write(f"*(unsigned int *){address}", (current & ~mask) | (saved & mask))
