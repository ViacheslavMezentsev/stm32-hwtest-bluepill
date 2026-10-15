# Measurement indication and DDTT report

[Русский](MEASUREMENT_LED.md) · [ADC/DMA](ADC_DMA.en.md)

| State | WeAct PB2 | Evidence |
| --- | --- | --- |
| MeasurementPending | Off | No monitor result yet |
| MeasurementNormal | 500 ms half-period blink | Filtered VDDA 2900..3600 mV and T −10..85 C |
| MeasurementFault | Steady on | Invalid block, out of range, timeout or DMA TE |

`g_monitor.state` is the latest state; `g_app.indication` is the state displayed by loop.
Errors retain filters. Each valid block re-evaluates health; recovery from out-of-range may
require multiple blocks. Error counts remain history. Recovered blinking uses the previous
last_toggle_ms rather than starting a new phase. A change is displayed in the next loop.
This educational indicator is not independent protection against an MCU hang.

## WeAct verification, 2026-10-15

[Plan](../hil/common/plans/measurement-led.en.md). Original HW_INDICATOR_INVALID failed at
`fault lights LED`: LED remained off after a normal block followed by zero VREFINT.
Buffer restored and clean startup verified in finally. Same assertion passed after the fix.
Original and intermediate failed attempts remain in local artifacts.

- HW_INDICATOR_NORMAL: off after the first loop, then blink with actual normal measurements.
- HW_INDICATOR_INVALID: zero VREFINT after normal, steady LED, stale normal cleared,
  actual valid block and blinking recovery.
- HW_INDICATOR_RANGE: VREFINT=3000 (1638 mV before filtering), filtered range fault,
  recovery within ten actual blocks without resetting filters.
- HW_DMA_TIMEOUT: missing ADC DMA requests produces timeout and steady LED; next block accepted.

Inject only into a stable block after DMA stops; verify writes and restore before restart.
Finally reset removes injected filter state. Full suite: **21/21 HW PASS**, capture SAVED;
C8/CB preparation **22/22 PASS**. Native C++ checks invalidate and recovery. CB release built;
Renode 1.17 passes boot/fault indication with no ADC/DMA model. C8 hardware not tested.
Actual DMA TE was not injected or coloured. ODR is not an optical measurement, and debugger
stops do not establish free-running timing guarantees.

Map: **64 links / 55 lines**, confirmed by the fresh full hardware campaign. These are author-
approved assertion-to-code links, not instruction tracing. Export: [DDTT_STARTUP](DDTT_STARTUP.en.md).

```powershell
python hil/tools/ddtt_report.py --runs "$campaign/runs" --view build/ddtt-view
```

## Report theme

GitHub-style HTML defaults to dark. Round button beside filters cycles
**☾ dark → ☀ light → ◐ auto**. localStorage remembers selection where allowed; with blocked
storage the button still works until reload. Auto uses VS Code theme classes when supplied
inside the document, otherwise the system scheme. An isolated preview iframe may not know
the editor theme: select dark explicitly. No external CSS/JS/CDN dependencies.
Reopen Preview Report or reload the browser after HTML regeneration.

Host tests verify links/SHA and execute the actual theme JavaScript using Node.js: cycle,
persistence, VS Code precedence and blocked storage. Visual appearance in the owner's
specific VS Code preview still needs manual verification.
