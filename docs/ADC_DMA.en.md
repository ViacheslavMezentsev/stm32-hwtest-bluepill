# ADC/DMA and sample processing

[Русский](ADC_DMA.md) · [Startup DDTT](DDTT_STARTUP.en.md)

After POST, loop polls a monitor. ADC1 scans VREFINT(17)/temperature(16); DMA1 Channel1 transfers
8 halfword pairs to g_monitor.raw in normal mode. TC ISR stops ADC/DMA before publishing ready.
CPU processes a stable block. New blocks start no faster than every 100 ms; internal sensor
stabilization takes 2 ms. A >10 ms timeout releases resources and allows retry. TE is counted
separately, but actual TE was not injected in this series and that branch remains uncoloured.
POST calibration is reused; the monitor does not recalibrate. LED now follows measurements; see [indication](MEASUREMENT_LED.en.md).

[Processing](../src/monitor_processing.cpp) has no CMSIS dependency: average 8 pairs, VDDA with
1200 mV typical VREFINT, temperature with 1430 mV at 25 C and 4.3 mV/C. Independent scalar
filters use Q=1,R=4,Pinitial=1 in each channel: a demonstration, not a tuned sensor noise model.
First sample seeds the state. Reject null/bad count, zero VREFINT or values >4095 before changing
filters. Normal is 2900..3600 mV and -10..85 C. This does not calibrate sensor accuracy.

## Verified 2026-10-15

WeAct F103CB_PB2, OpenOCD 0.12.0/ST-Link, xPack 14.2.1-1.1/GDB 15.2.90. Full hardware suite
21/21 PASS, command 0, capture SAVED; C8 and CB host/prepare 22/22. C8 hardware not run.
CB Renode smoke PASS proves boot/fault indication without ADC/DMA, not DMA modelling. CB release built. New source
formatted with supplied clang-format 23.1.3 rules; user's .clang-format change remains uncommitted.

- HW_DMA_CAPTURE: scan/DMA registers, actual TC IRQ/CNDTR=0, three blocks and publications,
  disabled ADC/DMA before CPU reads. Example VREFINT 1492..1494, temperature 1771..1774.
- HW_DMA_PROCESS: 1500/1800 -> 3276 mV and 22.6744 C; second 1560/1800 -> 3150 mV raw,
  3234 mV filtered. Bad blocks leave filters intact; full MonitorState restored.
- HW_DMA_TIMEOUT: disable ADC DMA requests, one timeout/no publication, next block accepted.
  This models absent requests, not physical DMA failure.
- Native C++: same processing function; first/second samples, null, length, zero tail, >4095,
  unchanged filter on rejection.
- Negative control: local copy expecting 9999 mV produces FAIL and verified finally recovery;
  this is not an original defect in the newly added feature.

Initial HW_DMA_PROCESS attempt was ERROR because Target.call rejects namespaces. RAM recovery
passed. The scenario now invokes gdb.parse_and_eval("monitor::process(...)") on GDB's main
thread and records the bool result as processing.call. This direct GDB route is not support for
C++ names in call; it does not add a call mutation entry. Records and checks are its evidence.
No firmware test wrappers were added.

## More than green marks

64 confirmed mappings on 55 lines; untested branches remain unmarked. After binding/exporting
as described in [Startup DDTT](DDTT_STARTUP.en.md), run:

```powershell
python hil/tools/ddtt_report.py --runs "$campaign/runs" --view build/ddtt-view
```

Coverage Gutters: Watch shows marks; Preview Report opens build/ddtt-view/index.html. Also open
it in a browser; the embedded preview may restrict local file and vscode protocol links.
HTML includes source/line, assertion, scenario-definition link, selected attempt/date/age,
actual/expected (including repeated checks), result/records links, selected campaign attempt
counts (total and same ELF), history, search/state filter and GitHub-style dark/light/auto theme.
Age is computed at report generation. Counts are not lifetime totals; matching ELF is not PASS.
The exporter remains responsible for evidence selection; HTML verifies the selected result hash
and clears stale output on errors. LCOV DA stays Boolean, not an attempt counter. Coverage Gutters
does not infer these links from LCOV. Host tests cover links/escaping and changed-result refusal.

```powershell
python hil/tools/check_monitor.py
python -m unittest discover -s hil/tools -p test_ddtt_report.py
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host
ctest --preset f103cb-hil-hw
```

For isolated campaigns/map refresh follow DDTT_STARTUP. Do not mix old ELF results. Native g++
is needed only for numerical vectors; firmware uses Arm GCC. The button and further failure branches remain future work. LED indication is described
in [Measurement indication](MEASUREMENT_LED.en.md).
