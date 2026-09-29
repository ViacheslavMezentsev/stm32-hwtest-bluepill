"""Прикладная логика: setup(), POST через АЦП и мигание светодиодом в loop()."""
from stm32_gdbtest import case

# SysTick (ARMv7-M): CTRL 0xE000E010, LOAD 0xE000E014.
SYSTICK_CTRL = "*(unsigned int *)0xE000E010"
SYSTICK_LOAD = "*(unsigned int *)0xE000E014"
# Уровень вывода светодиода: g_led описывает порт и маску для обеих плат.
LED_ON = "(((*(unsigned int *)g_led.odr_address & g_led.mask) != 0) == (g_led.active_high != 0))"


@case("HW_SETUP_DONE", timeout_s=10, labels=("setup",))
def setup_done(t):
    # Первый вход в loop() означает, что setup() вернулся без HardFault и без зависания.
    t.reach("loop")
    t.check("g_app.setup_done", t.value("g_app.setup_done"), 1)
    t.check("SysTick enabled", t.value(f"{SYSTICK_CTRL} & 1"), 1)
    t.check("SysTick 1 ms at 8 MHz", t.value(SYSTICK_LOAD), 7999)


@case("HW_POST", timeout_s=10, labels=("setup", "post"))
def post(t):
    t.reach("loop")
    t.check("g_post.status == PostOk", t.value("g_post.status"), 1)
    vdda = t.value("g_post.vdda_mv")
    t.check(f"VDDA {vdda} mV in 2900..3600", 2900 <= vdda <= 3600, True)
    temp = t.value("g_post.temp_c10")
    t.check(f"T {temp / 10:.1f} C in -10..85", -100 <= temp <= 850, True)


@case("HW_BLINK", timeout_s=10, labels=("blink",))
def blink(t):
    # Два соседних переключения: состояние светодиода меняется, счётчик растёт на 1.
    t.reach("board::ledToggle")
    led_before = t.value(LED_ON)
    count_before = t.value("g_app.blink_count")
    t.reach("board::ledToggle")
    t.check("LED state changed", t.value(LED_ON) != led_before, True)
    t.check("g_app.blink_count advanced", t.value("g_app.blink_count") - count_before, 1)
