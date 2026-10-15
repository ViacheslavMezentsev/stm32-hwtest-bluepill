# POST timeouts

[Русский](POST_TIMEOUT.md)

Three scenarios in [test_post_timeout.py](../hil/common/tests/board/test_post_timeout.py):
`HW_POST_RSTCAL_TIMEOUT`, `HW_POST_CAL_TIMEOUT`, `HW_POST_EOC_TIMEOUT`.
Firmware is unchanged. Three actual POST failure paths run on WeAct F103CB/OpenOCD.

A unique while source anchor and DWARF locate each point. Preflight checks a narrow ELF
instruction contract: pointer load, CR2/SR read, TST mask and branch direction.
Compiler changes may reject the preflight; do not guess replacement machine code.
Negative host vectors verify this guard.

Only the CPU copy of the completed MMIO read is replaced: RSTCAL/CAL appear busy or EOC
appears absent. The scenario does not write hardware flags or Flash, move PC or replace
adcInit/convert returns. board::millis returns start+10 then start+11. At 10 ms the same
wait loop must be reached again; at 11 the function must actually return false and reach
post::run cleanup. Checks require PostAdcTimeout, completed setup, no samples and cleared
ADON/TSVREFE. Finally removes breakpoints, resets MCU and requires a normal PostOk.

Limits: this models a stuck peripheral read result, not a physical ADC fault. Real
RSTCAL/CAL may have completed already. EOC targets the first VREFINT sample; a failed
temperature conversion or later sample is not claimed. 10/11 are software time values,
not SWD experiment durations.

Each while is linked to continued waiting and false return, ADC cleanup to disabled bits,
and status publication to PostAdcTimeout. Blank/comment lines are excluded. Other assertions
remain visible in the scenario's HTML details.

Validation on 2026-10-15: 28/28 WeAct hardware PASS, saved captures; 29/29 F103CB host preparation PASS; three negative/positive preflight unit tests and four DDTT report/export tests PASS. Map: 94 confirmed links across 72 lines. No production fix needed; other boards were not tested.
