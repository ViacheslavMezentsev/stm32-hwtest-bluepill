"""
RU: Запуск: порядок инициализации, начальный светодиод, SysTick и ADC до первого отсчёта.
EN: Startup order, initial LED state, SysTick and ADC before the first sample.

Наблюдаем штатный код, не вызываем init повторно и не меняем регистры периферии.
Остановки GDB проверяют порядок и состояния, но не длительность свободного запуска.
"""
from stm32_gdbtest import case


# Номинальная частота HSI; SysTick должен делить её до 1000 прерываний в секунду.
HSI_HZ = 8_000_000
TICK_HZ = 1000
SYSTICK_BITS = 'SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk'

# Внутренние каналы STM32F103: сначала VREFINT (17), затем температура (16).
VREF_CHANNEL = 17
TEMP_CHANNEL = 16


# Проверяем границы стадий: каждая периферия готова до входа в следующую стадию.
@case("HW_STARTUP_ORDER", timeout_s=20, labels=("startup", "gpio", "uart"))
def startup_order(t):
    board = t.profile.data["board"]["board"]
    port, pin = board["led_port"], board["led_pin"]
    cr = "CRL" if pin < 8 else "CRH"

    # Runner остановился в main; нулевые данные ещё не заменены результатами setup.
    t.check("entry is main", t.frames(2)["frames"][0]["name"], "main")

    # Нулевое состояние глобальных результатов до setup.
    t.check([
        ("setup not published at main", "g_app.setup_done", 0),
        ("no blink at main", "g_app.blink_count", 0),
        ("no reference sample at main", "g_post.vrefint_raw", 0)
    ])
    t.reach("setup")
    t.check("setup called from main", t.frames(3)["frames"][1]["name"], "main")
    t.reach("board::init")
    t.check("board init called from setup", t.frames(3)["frames"][1]["name"], "setup")

    # В uart.cpp доступны CMSIS-макросы. board::init уже завершился, UART ещё не настроен.
    t.reach("uart::init")
    t.record("startup.before_uart", {"apb2enr": t.mmio.read('RCC.APB2ENR'),
                                     "led_odr": t.mmio.read(f"{port}.ODR"),
                                     "systick_load": t.mmio.read('SysTick.LOAD')})

    # Проверяем именно начальное выключенное состояние, а не состояние после первого мигания.
    t.check("LED clock before UART", (t.mmio.read("RCC.APB2ENR") & t.evaluate(f"RCC_APB2ENR_IOP{port[-1]}EN")) != 0, 1)
    t.check("LED output before UART",
            t.mmio.read(f"{port}.{cr}") & t.evaluate(f"GPIO_{cr}_MODE{pin} | GPIO_{cr}_CNF{pin}"),
            t.evaluate(f"GPIO_{cr}_MODE{pin}_1"))
    t.check("LED initially off",
            (t.mmio.read(f"{port}.ODR") & t.evaluate(f"GPIO_ODR_ODR{pin}")) != 0,
            int(not board["led_active_high"]))
    t.check("SysTick reload before UART", t.mmio.read('SysTick.LOAD'), HSI_HZ // TICK_HZ - 1)
    t.check("SysTick enabled before UART",
            t.mmio.read('SysTick.CTRL', allow_effects=True) & (t.evaluate(SYSTICK_BITS)),
            t.evaluate(SYSTICK_BITS))
    t.check("UART clock not enabled early", t.mmio.read('RCC.APB2ENR') & t.evaluate('RCC_APB2ENR_USART1EN'), 0)

    # Проверяем опубликованное состояние отдельно от MMIO-снимка.
    t.check([ ("setup pending before UART", "g_app.setup_done", 0) ])

    # Вход в POST доказывает возврат из UART init и печати заголовка; USART DR не читаем.
    t.reach("post::run")
    t.check("POST called from setup", t.frames(3)["frames"][1]["name"], "setup")
    t.record("startup.before_post", {"brr": t.mmio.read('USART1.BRR'), "cr1": t.mmio.read('USART1.CR1')})
    baud = t.profile.data["board"]["uart"]["baud"]

    # USART SR допускает эффект последовательности SR→DR; DR не читаем.
    # Ожидания масок из CMSIS; частота и скорость заданы независимо от прочитанного делителя.
    t.check("UART clocks before POST",
            t.mmio.read('RCC.APB2ENR') & (t.evaluate("RCC_APB2ENR_IOPAEN | RCC_APB2ENR_USART1EN")),
            t.evaluate("RCC_APB2ENR_IOPAEN | RCC_APB2ENR_USART1EN"))
    t.check("UART pin before POST",
            t.mmio.read('GPIOA.CRH') & (t.evaluate("GPIO_CRH_MODE9 | GPIO_CRH_CNF9")),
            t.evaluate("GPIO_CRH_MODE9 | GPIO_CRH_CNF9_1"))
    t.check("UART divider before POST", t.mmio.read('USART1.BRR'), (HSI_HZ + baud // 2) // baud)
    t.check("UART transmitter before POST",
            t.mmio.read('USART1.CR1') & (t.evaluate("USART_CR1_UE | USART_CR1_TE | USART_CR1_RE")),
            t.evaluate("USART_CR1_UE | USART_CR1_TE"))
    t.check("banner transmission completed",
            t.mmio.read('USART1.SR', allow_effects=True) & t.evaluate('USART_SR_TC') != 0,
            1)
    t.check("ADC clock not enabled early", t.mmio.read('RCC.APB2ENR') & t.evaluate('RCC_APB2ENR_ADC1EN'), 0)

    # Проверяем опубликованное состояние отдельно от MMIO-снимка.
    t.check([ ("setup pending before POST", "g_app.setup_done", 0) ])

    # Только после POST и публикации setup_done разрешён первый проход loop.
    t.reach("loop")
    t.record("startup.first_loop", t.read("g_app"))
    t.check("loop called from main", t.frames(3)["frames"][1]["name"], "main")
    t.check("setup published before loop", t.read("g_app.setup_done"), 1)
    t.check("no blink before first loop", t.read("g_app.blink_count"), 0)


# Два соседних входа в ISR: между ними обработчик увеличивает программный счётчик ровно один раз.
@case("HW_SYSTICK_PROGRESS", timeout_s=10, labels=("startup", "irq"), contracts=("cmsis_core_macros",))
def systick_progress(t):
    t.reach("SysTick_Handler")
    before = t.read("g_ticks")
    # Активное исключение — по SCB.ICSR.VECTACTIVE: имя регистра xPSR зависит от GDB-сервера.
    t.check("SysTick exception context", t.mmio.read("SCB.ICSR") & t.evaluate("SCB_ICSR_VECTACTIVE_Msk"), 15)
    t.reach("SysTick_Handler")
    after = t.read("g_ticks")
    t.record("startup.systick", {"before": before, "after": after, "delta": (after - before) & 0xFFFFFFFF})
    t.check("SysTick handler increments once", (after - before) & 0xFFFFFFFF, 1)

    # COUNTFLAG при чтении CTRL сбрасывается; прошивка его не использует.
    t.check("SysTick nominal reload", t.mmio.read('SysTick.LOAD'), HSI_HZ // TICK_HZ - 1)
    t.check("SysTick interrupt source",
            t.mmio.read('SysTick.CTRL', allow_effects=True) & (t.evaluate(SYSTICK_BITS)),
            t.evaluate(SYSTICK_BITS))


# Наблюдаем существующий C++ convert по символу ELF: init и калибровка уже завершились.
@case("HW_ADC_INITIALIZATION", timeout_s=15, labels=("startup", "adc"), contracts=("cmsis_adc_init",))
def adc_initialization(t):
    t.reach("(anonymous namespace)::convert")
    t.record("startup.adc", {"channel": t.read("channel"), "cr2": t.mmio.read('ADC1.CR2'),
                             "smpr1": t.mmio.read('ADC1.SMPR1'), "cfgr": t.mmio.read('RCC.CFGR')})
    t.check("conversion belongs to POST", "post::run" in [f["name"] for f in t.frames(4)["frames"]])

    # Каналы по одному; калибровка закончена, DMA/непрерывное преобразование здесь не используются.
    t.check("ADC clock enabled before sample", t.mmio.read('RCC.APB2ENR') & t.evaluate('RCC_APB2ENR_ADC1EN') != 0, 1)
    t.check("ADC clock divider",
            t.mmio.read('RCC.CFGR') & t.evaluate('RCC_CFGR_ADCPRE'),
            t.evaluate("RCC_CFGR_ADCPRE_DIV2"))
    t.check("ADC independent single conversion", t.mmio.read('ADC1.CR1'), 0)
    t.check("ADC enabled with internal sensors",
            t.mmio.read('ADC1.CR2') & (t.evaluate("ADC_CR2_ADON | ADC_CR2_TSVREFE")),
            t.evaluate("ADC_CR2_ADON | ADC_CR2_TSVREFE"))
    t.check("ADC software trigger",
            t.mmio.read('ADC1.CR2') & (t.evaluate("ADC_CR2_EXTSEL | ADC_CR2_EXTTRIG")),
            t.evaluate("ADC_CR2_EXTSEL | ADC_CR2_EXTTRIG"))
    t.check("ADC calibration completed", t.mmio.read('ADC1.CR2') & (t.evaluate("ADC_CR2_CAL | ADC_CR2_RSTCAL")), 0)
    t.check("ADC polling mode", t.mmio.read('ADC1.CR2') & (t.evaluate("ADC_CR2_DMA | ADC_CR2_CONT")), 0)
    t.check("internal channels long sampling",
            t.mmio.read('ADC1.SMPR1') & (t.evaluate("ADC_SMPR1_SMP16 | ADC_SMPR1_SMP17")),
            t.evaluate("ADC_SMPR1_SMP16 | ADC_SMPR1_SMP17"))
    t.check("one regular conversion", t.mmio.read('ADC1.SQR1') & t.evaluate('ADC_SQR1_L'), 0)

    # Проверяем опубликованное состояние отдельно от MMIO-снимка.
    t.check([ ("reference channel first", "channel", VREF_CHANNEL) ])

    # Повторный вход означает завершение первого преобразования; буфер назначения задан C++-ссылкой.
    t.reach("(anonymous namespace)::convert")
    t.record("startup.adc_second", {"channel": t.read("channel"), "vrefint_raw": t.read("g_post.vrefint_raw")})
    t.check("temperature channel second", t.read("channel"), TEMP_CHANNEL)
    t.check("reference published before temperature", t.read("g_post.vrefint_raw") > 0)
