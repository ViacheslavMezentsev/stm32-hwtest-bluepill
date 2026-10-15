"""
RU: KEY WeAct: конфигурация входа, виртуальные нажатия, дребезг и принудительный LED.
EN: WeAct KEY input, virtual presses, debounce and forced LED.
"""
from stm32_gdbtest import case


# Уровень LED нормализован по описанию платы, регистр IDR сценарий не изменяет.
LED_ON = "((*(unsigned int *)g_led.odr_address & g_led.mask) != 0) == (g_led.active_high != 0)"


# У обычной Blue Pill пользовательская KEY отсутствует; это не отказ платы.
def require_button(t):
    if not t.profile.data["board"]["button"]["present"]:
        t.skip("This board profile has no user KEY")


# Возвращаем значение штатного чтения, затем задаём время одного вычисления debounce.
def sample(t, pressed, tick):
    t.reach("board::buttonPressed")
    result = t.ret(int(pressed))
    t.check("button sample returns to loop", result["caller"], "loop")
    t.reach("ButtonState::update")
    t.write("now", tick)
    t.check("injected timestamp readback", t.evaluate("now"), tick)
    t.finish()
    t.finish()
    t.record("button.sample", {"pressed": pressed, "tick": tick, "state": t.read("g_button"),
                               "led": t.evaluate(LED_ON)})


# Аппаратные настройки и настоящий отпущенный вход, отдельно от подмены функции.
@case("HW_BUTTON_CONFIG", timeout_s=15, labels=("button", "gpio"))
def config(t):
    require_button(t)
    t.reach("board::buttonPressed")

    # Проверяем подтяжку и настоящий IDR до любой подмены чтения.
    t.check([
        ("KEY clock enabled", "(RCC->APB2ENR & RCC_APB2ENR_IOPAEN) != 0", 1),
        ("KEY input with pull", "GPIOA->CRL & (GPIO_CRL_MODE0 | GPIO_CRL_CNF0)", "GPIO_CRL_CNF0_1"),
        ("KEY pull down", "GPIOA->ODR & GPIO_ODR_ODR0", 0),
        ("KEY physically released", "GPIOA->IDR & GPIO_IDR_IDR0", 0)
    ])
    t.finish()


# Временные векторы проверяют порог и единичность события, а не скорость SWD.
@case("HW_BUTTON_VIRTUAL", timeout_s=30, labels=("button", "injection"))
def virtual(t):
    require_button(t)
    try:
        sample(t, True, 0)
        sample(t, True, 29)
        t.check("short press rejected", t.read("g_button.presses"), 0)
        sample(t, False, 29)
        sample(t, True, 30)
        sample(t, True, 59)
        t.check("bounce restarts debounce", t.read("g_button.presses"), 0)
        sample(t, True, 60)
        t.check("stable press counted", t.read("g_button.presses"), 1)
        t.check("held KEY lights LED", t.evaluate(LED_ON), 1)

        # Даже просроченное мигание не гасит LED при удержании.
        before = t.read("g_app.blink_count")
        t.write("g_app.last_toggle_ms", 0xffff0000)
        sample(t, True, 1000)
        t.check("hold does not repeat press", t.read("g_button.presses"), 1)
        t.check("hold suppresses blinking", t.read("g_app.blink_count"), before)
        t.check("held LED stays on", t.evaluate(LED_ON), 1)
        sample(t, False, 1001)
        sample(t, False, 1030)
        t.check("short release ignored", t.read("g_button.stable"), True)
        sample(t, False, 1031)
        t.check("stable release accepted", t.read("g_button.stable"), False)

        # После отпускания реальные измерения и обычный loop вновь управляют LED.
        t.reach("board::ledToggle")
        previous = t.evaluate(LED_ON)
        t.reach("board::ledToggle")
        t.check("release restores blinking", t.evaluate(LED_ON) != previous)
    finally:
        t.reset()
        t.reach("loop")
        t.check("button injection reset", t.read("g_button.presses"), 0)
