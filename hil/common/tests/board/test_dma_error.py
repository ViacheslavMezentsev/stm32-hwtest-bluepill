"""
RU: Ошибка DMA имеет приоритет над TC; ошибочный блок не публикуется, сбор восстанавливается.
EN: DMA error takes priority over TC; no erroneous block publication and capture recovers.
"""
from pathlib import Path
import gdb
from stm32_gdbtest import case


# Якорь после чтения ISR и остановки передачи; не записываем read-only регистр ISR.
def status_point():
    lines = (Path(__file__).resolve().parents[4] / "src/monitor.cpp").read_text(encoding="utf-8").splitlines()
    start = lines.index('extern "C" void DMA1_Channel1_IRQHandler()')
    matches = [i + 1 for i in range(start, len(lines)) if lines[i].strip() == "DMA1->IFCR = DMA_IFCR_CGIF1;"]
    if len(matches) != 1:
        raise RuntimeError("DMA IRQ injection anchor changed")
    return f"monitor.cpp:{matches[0]}"


# Сначала настоящая норма, затем подмена локального снимка статуса в настоящем IRQ.
def inject_error(t, completed):
    point = status_point()
    try:
        t.reach("monitor::process")
        t.finish()
        t.check("baseline block accepted", t.read("g_monitor.accepted"), 1)
        t.check("baseline normal", t.read("g_monitor.normal"), 1)
        breakpoint = t.breakpoint(point)
        try:
            stop = t.resume()
            t.check("injection breakpoint reached", breakpoint.number in stop.get("stop", stop).get("breakpoints", []))
            t.check("injection handler frame", gdb.newest_frame().name(), "DMA1_Channel1_IRQHandler")
        finally:
            breakpoint.remove()

        # Проверяем контекст и освобождение периферии до изменения локального status.
        # Активное исключение — по SCB.ICSR.VECTACTIVE: имя регистра xPSR зависит от GDB-сервера.
        t.check("injection in DMA IRQ", t.mmio.read("SCB.ICSR") & t.evaluate("SCB_ICSR_VECTACTIVE_Msk"),
                t.evaluate("DMA1_Channel1_IRQn + 16"))
        t.check("real TC before injection", t.evaluate("(status & DMA_ISR_TCIF1) != 0"), 1)
        t.check("injection DMA stopped", t.mmio.read('DMA1_Channel1.CCR') & t.evaluate('DMA_CCR_EN'), 0)
        t.check("injection ADC stopped", t.mmio.read('ADC1.CR2') & t.evaluate('ADC_CR2_ADON'), 0)

        # Проверяем опубликованное состояние отдельно от MMIO-снимка.
        t.check([ ("no pending publication", "g_monitor.ready", 0) ])
        injected = t.evaluate("DMA_ISR_TEIF1 | DMA_ISR_TCIF1" if completed else "DMA_ISR_TEIF1")
        t.write("status", injected)
        t.record("dma.error.injection", {"status": t.evaluate("status"), "with_tc": completed})
        t.check("injected status readback", t.evaluate("status"), injected)

        # Следующий arm достигается после обработки ошибки, до новой передачи.
        t.reach("monitor::arm")
        t.record("dma.error.result", {"errors": t.read("g_monitor.dma_errors"),
                                      "ready": t.read("g_monitor.ready"), "accepted": t.read("g_monitor.accepted"),
                                      "irq_count": t.read("g_monitor.irq_count")})

        # Приоритет TE проверяется до начала следующей передачи.
        t.check([
            ("TE counted once", "g_monitor.dma_errors", 1),
            ("error publishes no ready", "g_monitor.ready", 0),
            ("error block not processed", "g_monitor.accepted", 1),
            ("TE takes priority over TC", "g_monitor.irq_count", 1),
            ("error cancels normal", "g_monitor.normal", 0),
            ("error state fault", "g_monitor.state", "MeasurementFault")
        ])
        t.check("error stops DMA", t.mmio.read('DMA1_Channel1.CCR') & t.evaluate('DMA_CCR_EN'), 0)
        t.check("error stops ADC",
                t.mmio.read('ADC1.CR2') & (t.evaluate("ADC_CR2_ADON | ADC_CR2_DMA | ADC_CR2_CONT | ADC_CR2_TSVREFE")),
                0)
        t.check("error clears channel flags",
                t.mmio.read('DMA1.ISR') & (t.evaluate("DMA_ISR_GIF1 | DMA_ISR_TCIF1 | DMA_ISR_HTIF1 | DMA_ISR_TEIF1")),
                0)

        # Проверяем опубликованное состояние отдельно от MMIO-снимка.
        t.check([ ("error is not timeout", "g_monitor.timeouts", 0) ])

        # Две последующие реальные передачи: нет повторного отказа и двойного принятия.
        for count in (2, 3):
            t.reach("monitor::process")
            t.finish()
            t.record("dma.error.recovery", {"accepted": t.read("g_monitor.accepted"),
                                            "irq_count": t.read("g_monitor.irq_count")})

            # Независимые счётчики исключают повторную публикацию и повторный отказ.
            t.check([
                ("recovered block accepted once", "g_monitor.accepted", count),
                ("recovered TC counted once", "g_monitor.irq_count", count),
                ("recovery restores normal", "g_monitor.normal", 1),
                ("error does not repeat", "g_monitor.dma_errors", 1),
                ("recovery has no timeout", "g_monitor.timeouts", 0)
            ])
    finally:
        # Сброс удаляет инъекцию и накопленное состояние; образ прошивки не меняем.
        t.reset()
        t.reach("loop")
        t.check("DMA error injection cleared", t.read("g_monitor.dma_errors"), 0)
        t.check("monitor reset after injection", t.read("g_monitor.initialized"), 0)


# Только TE: TC локально отсутствует.
@case("HW_DMA_ERROR", timeout_s=25, labels=("adc", "dma", "injection"))
def transfer_error(t):
    inject_error(t, False)


# TE и TC одновременно: завершение не должно перебить ошибку.
@case("HW_DMA_ERROR_TC", timeout_s=25, labels=("adc", "dma", "injection"))
def transfer_error_and_complete(t):
    inject_error(t, True)
