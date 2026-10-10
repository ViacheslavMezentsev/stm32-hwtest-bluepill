"""
RU: После недопустимого отсчёта POST отключает ADC и внутренние датчики.
EN: POST disables the ADC and internal sensors after an invalid sample.
"""
from stm32_gdbtest import case


# Reject a zero reference sample and release ADC resources before the application starts.
@case("HW_POST_ADC_CLEANUP", labels=("post", "injection"), contracts=("cmsis_core_macros",))
def post_adc_cleanup(t):
    # POST clears its result before adcInit() waits for sensor stabilization.
    t.reach("board::delayMs")
    t.check("sensor initialization is inside POST", "post::run" in [f["name"] for f in t.frames(4)["frames"]])

    # Expand CMSIS macros in board.cpp; loop() belongs to a translation unit without those macros.
    adc_cr2 = t.evaluate("(unsigned int)&ADC1->CR2")
    enable_mask = t.evaluate("ADC_CR2_ADON | ADC_CR2_TSVREFE")

    # Stop after the real conversion stores its average, then inject an invalid reference.
    with t.watch("g_post.vrefint_raw"):
        t.check("reference publication reached", t.resume()["stop"]["kind"], "watchpoint")
        t.check("real reference is nonzero", t.read("g_post.vrefint_raw") > 0)
        t.write("g_post.vrefint_raw", 0)

    # Observe the early failure path at the application entry, retaining evidence before assertions.
    t.reach("loop")
    cr2 = t.evaluate(f"*(volatile unsigned int *){adc_cr2}")
    t.record("post.failure", {"status": t.read("g_post.status"), "cr2": cr2, "enable_mask": enable_mask})

    # Validate the failure path and application progress before checking resource cleanup.
    t.check([
        ("invalid reference follows POST failure path", "g_post.status", "PostAdcTimeout"),
        ("application still starts", "g_app.setup_done", 1)
    ])
    t.check("ADC and internal sensors released", cr2 & enable_mask, 0)
