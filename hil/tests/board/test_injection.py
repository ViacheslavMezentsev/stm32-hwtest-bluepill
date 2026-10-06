"""
RU: Инъекции: подмена ответа ledIsOn() и отсчёта VREFINT; прошивка реагирует как на настоящий отказ.
EN: Injections: a substituted ledIsOn() answer and VREFINT sample; the firmware reacts as to a real fault.
"""
from stm32_gdbtest import case


# LED level for both boards: g_led names the ODR address, the pin mask and the active level.
LED_ON = "((*(unsigned int *)g_led.odr_address & g_led.mask) != 0) == (g_led.active_high != 0)"

# POST arithmetic (src/post.cpp): VREFINT is 1200 mV typical, the ADC is 12-bit.
VREFINT_MV = 1200
ADC_FULL_SCALE = 4095


# Verify that ledToggle() acts on what ledIsOn() reports: a substituted answer decides the next level.
@case("HW_LED_FORCED_STATE", timeout_s=20, labels=("blink", "injection"))
def led_forced_state(t):
    # TECH-004: each pass returns from ledIsOn() with a chosen answer; ledToggle() sets the opposite level.
    for reported in (1, 0):
        t.reach("board::ledIsOn")
        result = t.ret(reported)
        t.check(f"ledIsOn() answered {reported} to its caller", (result["caller"], result["applied"]),
                ("board::ledToggle", reported))
        t.check("ledToggle() returns to loop()", t.finish()["function"], "loop")
        t.check(f"LED level is the opposite of {reported}", t.evaluate(LED_ON), 1 - reported)


# Verify that POST reports a low VDDA and the application still starts when VREFINT reads high.
@case("HW_POST_VDDA_LOW", timeout_s=20, labels=("post", "injection"))
def post_vdda_low(t):
    raw = t.profile.get("user.injection.vrefint_raw")

    # TECH-013 and TECH-005: the watch point stops right after convert() stores the VREFINT average;
    # the stored sample is replaced before post::run() computes VDDA from it.
    with t.watch("g_post.vrefint_raw"):
        t.check("the stop is the watch point", t.resume()["stop"]["kind"], "watchpoint")
        names = [frame["name"] for frame in t.frames(4)["frames"]]
        t.check("the store happens during POST", "post::run" in names)
        t.write("g_post.vrefint_raw", raw)

    # setup() goes on after a failed POST: the application starts.
    t.reach("loop")

    # The failure stays in g_post and VDDA follows the substituted sample.
    t.check([
        ("VDDA computed from the substituted sample", "g_post.vdda_mv", VREFINT_MV * ADC_FULL_SCALE // raw),
        ("POST reports VDDA out of range", "g_post.status", "PostVddaOutOfRange"),
        ("setup still finished", "g_app.setup_done", 1)
    ])
