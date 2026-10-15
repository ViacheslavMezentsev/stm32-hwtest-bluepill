# POST timeout plan

WeAct F103CB/OpenOCD. No firmware changes. Check instructions from DWARF before injection.
Replace CPU value after MMIO read before TST: RSTCAL/CAL busy or EOC missing.
Return start+10 then start+11 from millis; require repeat wait at 10 and false/cleanup at 11.
Check PostAdcTimeout, no samples, setup complete, ADON/TSVREFE clear. Finally reset and PostOk.
No MMIO/Flash writes by the scenario, no PC jumps, no physical ADC fault claim.
Prepare/style before hardware, three candidate corrections maximum, one environment diagnosis.
Stop on USB/identity/recovery error. Preserve every attempt in build/ddtt-post-timeout-*.
No known production defect: original PASS is acceptable. Full regression and fresh DDTT export.

Validation on 2026-10-15: 28/28 WeAct hardware PASS, saved captures; 29/29 F103CB host preparation PASS; three negative/positive preflight unit tests and four DDTT report/export tests PASS. Map: 94 confirmed links across 72 lines. No production fix needed; other boards were not tested.
