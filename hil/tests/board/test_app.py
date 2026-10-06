"""
RU: Прикладная логика: setup(), POST через АЦП, мигание светодиодом в loop() и кто пишет время переключения.
EN: Application logic: setup(), POST through the ADC, LED blinking in loop() and who writes the toggle time.
"""
from stm32_gdbtest import case, within


# HSI is the system clock; SysTick divides it down to 1 ms (SysTick_Config(SystemCoreClock / 1000)).
HSI_HZ = 8_000_000
SYSTICK_LOAD_1MS = HSI_HZ // 1000 - 1

# LED level for both boards: g_led names the ODR address, the pin mask and the active level.
LED_ON = "((*(unsigned int *)g_led.odr_address & g_led.mask) != 0) == (g_led.active_high != 0)"

# Polling in loop() sees every millisecond tick, so toggles are one half period apart, give or take a tick.
TICK_SLACK_MS = 1


# Verify that setup() returned and started the 1 ms system tick.
@case("HW_SETUP_DONE", timeout_s=10, labels=("setup",), contracts=("cmsis_core_macros",))
def setup_done(t):
    # The first entry of loop() means setup() returned without a fault or a hang.
    t.reach("loop")
    t.check("setup finished", t.read("g_app.setup_done"), 1)

    # board::millis() lives in board.cpp, where the core macros are visible.
    t.reach("board::millis")

    # Reading CTRL clears COUNTFLAG, which the firmware does not use: it counts SysTick interrupts.
    t.check([
        ("SysTick enabled", "SysTick->CTRL & SysTick_CTRL_ENABLE_Msk"),
        ("SysTick interrupt enabled", "SysTick->CTRL & SysTick_CTRL_TICKINT_Msk"),
        ("SysTick runs from the core clock", "SysTick->CTRL & SysTick_CTRL_CLKSOURCE_Msk"),
        ("SysTick period 1 ms", "SysTick->LOAD", SYSTICK_LOAD_1MS)
    ])


# Verify the power-on self test: VDDA and chip temperature in the room range, ADC off afterwards.
@case("HW_POST", timeout_s=10, labels=("setup", "post"), contracts=("cmsis_core_macros",))
def post(t):
    vdda_range = within(*t.profile.get("user.post.vdda_mv"))
    temperature_range = within(*t.profile.get("user.post.temp_c10"))
    t.reach("loop")

    # The measured values stay in g_post for the whole run.
    t.check([
        ("POST passed", "g_post.status", "PostOk"),
        ("VREFINT sampled", "g_post.vrefint_raw != 0"),
        ("VDDA in the room range, mV", "g_post.vdda_mv", vdda_range),
        ("chip temperature in the room range, 0.1 C", "g_post.temp_c10", temperature_range)
    ])
    t.record("post", t.read("g_post"))

    # POST switches the ADC and the internal channels off after measuring.
    t.reach("board::millis")
    t.check("ADC switched off after POST", t.evaluate("ADC1->CR2 & (ADC_CR2_ADON | ADC_CR2_TSVREFE)"), 0)


# Verify that loop() toggles the LED once per half period and counts the toggles.
@case("HW_BLINK", timeout_s=10, labels=("blink",))
def blink(t):
    half_period = t.profile.get("user.blink.half_period_ms")

    # Two consecutive toggles: loop() has stored the toggle time and not yet counted the toggle.
    t.reach("board::ledToggle")
    before, led_before = t.read("g_app"), t.evaluate(LED_ON)
    t.reach("board::ledToggle")
    after = t.read("g_app")

    # The LED level flipped, the counter advanced by one, the toggle times are a half period apart.
    t.check("LED state changed", t.evaluate(LED_ON) != led_before)
    t.check("blink counter advanced by one", after["blink_count"] - before["blink_count"], 1)
    t.check("toggles a half period apart, ms", after["last_toggle_ms"] - before["last_toggle_ms"],
            within(half_period, half_period + TICK_SLACK_MS))


# Find who writes the toggle time: setup() stores the start, loop() every toggle, both called from main().
@case("HW_TOGGLE_WRITERS", timeout_s=20, labels=("blink", "watch"))
def toggle_writers(t):
    writers = []

    # TECH-013: a write watch point on the field stops right after each store that changes it.
    with t.watch("g_app.last_toggle_ms"):
        # The first change comes from setup(), the second from the first toggle in loop().
        for _ in range(2):
            stop = t.resume()["stop"]
            t.check("the stop is the watch point", stop["kind"], "watchpoint")
            chain = t.frames(4)["frames"]
            writers.append([frame["name"] for frame in chain[:2]])
            t.record("writer", dict(frames=chain, value=t.read("g_app.last_toggle_ms")))

    t.check("setup() stores the start time, called from main()", writers[0], ["setup", "main"])
    t.check("loop() stores the toggle time, called from main()", writers[1], ["loop", "main"])
    t.check("setup() finished before the first toggle", t.read("g_app.setup_done"), 1)
