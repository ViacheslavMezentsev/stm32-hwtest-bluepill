"""
RU: Светодиод отражает норму, отказ обработки и восстановление измерений.
EN: LED follows normal measurements, processing failure and recovery.
"""
import struct
import gdb
from stm32_gdbtest import case


# Нормализованное состояние вывода с учётом активного уровня платы.
def led_on(t):
    port = t.profile.data["board"]["board"]["led_port"]
    return bool(t.mmio.read(f"{port}.ODR") & t.read("g_led.mask")) == bool(t.read("g_led.active_high"))


# Отказ вводим после настоящего нормального блока, чтобы поймать устаревшую «норму».
def fault_and_recovery(t, reference):
    t.reach("monitor::process")
    t.finish()
    t.check("initial measurements normal", t.read("g_monitor.normal"), 1)
    t.reach("monitor::process")
    t.check("injection owns stopped buffer", t.read("g_monitor.active"), 0)
    raw = int(gdb.parse_and_eval("&g_monitor.raw[0]"))
    saved = t.memory(raw, 32)
    t.check("complete injection snapshot", len(saved), 32)
    try:
        block = struct.pack("<16H", *([reference, 1800] * 8))
        t.memory(raw, block)
        t.check("injected block readback", t.memory(raw, 32), block)
        t.record("indicator.injection", {"reference": reference, "temperature": 1800})
        t.finish()

        # Буфер уже прочитан; восстанавливаем его до следующего запуска DMA.
        t.check("buffer still released", t.read("g_monitor.active"), 0)
        t.memory(raw, saved)
        t.check("sample buffer restored", t.memory(raw, 32), saved)
        t.reach("loop")
        t.finish()
        t.record("indicator.fault", {"led": led_on(t), "normal": t.read("g_monitor.normal")})
        t.check("fault lights LED", led_on(t), 1)
        t.check("fault clears old normal", t.read("g_monitor.normal"), 0)

        # Следующий loop не должен погасить аварийную индикацию.
        count = t.read("g_app.blink_count")
        t.reach("loop")
        t.finish()
        t.check("fault stays lit", led_on(t), 1)
        t.check("fault does not count toggles", t.read("g_app.blink_count"), count)

        # После низкого напряжения фильтр восстанавливается постепенно, не сбрасываем его.
        for number in range(10):
            t.reach("monitor::process")
            t.finish()
            t.record("indicator.recovery", {"block": number + 1, "normal": t.read("g_monitor.normal"),
                                            "vdda_mv": t.evaluate("g_monitor.vdda_mv", as_type=float)})
            if t.read("g_monitor.normal"):
                break
        t.check("measurements recover within ten blocks", t.read("g_monitor.normal"), 1)
        t.reach("board::ledToggle")
        before = led_on(t)
        t.reach("board::ledToggle")
        t.check("recovered LED blinks", led_on(t) != before)
    finally:
        # Сброс безопасно удаляет также последствия инъекции в фильтре и счётчиках.
        t.reset()
        t.reach("loop")
        t.check("fresh startup after injection", t.read("g_monitor.initialized"), 0)


# Нулевой VREFINT недопустим даже после успешного измерения.
@case("HW_INDICATOR_INVALID", timeout_s=30, labels=("indicator", "adc", "injection"))
def invalid(t):
    fault_and_recovery(t, 0)


# Допустимые коды ADC могут соответствовать недопустимому напряжению.
@case("HW_INDICATOR_RANGE", timeout_s=30, labels=("indicator", "adc", "injection"))
def out_of_range(t):
    # VREFINT=3000 даёт 1638 мВ до фильтра; второй результат уже ниже 2900 мВ.
    fault_and_recovery(t, 3000)


# До первого блока показываем ожидание, затем наблюдаем штатное мигание.
@case("HW_INDICATOR_NORMAL", timeout_s=15, labels=("indicator", "adc"))
def normal(t):
    t.reach("loop")
    t.finish()
    t.check("pending LED off", led_on(t), 0)
    t.reach("board::ledToggle")
    t.check("blinking requires normal measurements", t.read("g_monitor.normal"), 1)
    before = led_on(t)
    t.reach("board::ledToggle")
    t.check("normal LED blinks", led_on(t) != before)
