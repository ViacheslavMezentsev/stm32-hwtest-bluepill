# DDTT cycle: verification plan

Requirement: POST with a zero VREFINT sample retains PostAdcTimeout, continues setup and clears ADON/TSVREFE before loop.

Add `HW_POST_ADC_CLEANUP` before changing firmware. Expect the target assertion to FAIL (ADC cleanup
for BluePill, code 6 for BlackPill), not an infrastructure ERROR. Apply a minimal fix,
repeat the unchanged scenario, then run the complete host and hardware regression.

Scope: application sources and HIL, without test hooks. BluePill: F103CB/PB2;
BlackPill: F411CE and F401CC. Windows, OpenOCD, USB/SWD and on-board peripherals only.
Use strict identity; no mass erase or option bytes. Reset ends the injections.
Leave the corrected project firmware running after normal BOOT and LED verification.

Budget: up to three fixes and one diagnostic retry for an environment failure. Stop
hardware retries on USB ERROR, wrong MCU or failed recovery.

Keep local builds/evidence in `build/ddtt-baseline-*`, `build/ddtt-candidate-*`;
command logs and input snapshots in `build/ddtt-feedback/`. Sessions enable capture.
Preserve original FAIL artifacts. Final report: `ddtt-feedback-results.en.md` next to this plan.
Debugger stops and injections do not establish natural physical failures or real-time deadlines.

## Repeat the corrected check

The local stand file must match the connected board.

```powershell
cmake --preset HIL_F103CB -B build/ddtt-candidate-f103cb
cmake --build build/ddtt-candidate-f103cb
ctest --test-dir build/ddtt-candidate-f103cb -L host -j 1 --output-on-failure
python modules/stm32-gdbtest/stm32_gdbtest/cli.py run --session build/ddtt-candidate-f103cb/hwtest/session.json --test HW_POST_ADC_CLEANUP --stand hil/stands/F103CB-openocd.local.toml --identity-policy strict
```
