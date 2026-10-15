# WeAct BluePill-Plus startup colouring

[Русский](DDTT_STARTUP.md) · [Environment](DEVELOPER_ENVIRONMENT.en.md)

F103CB_PB2, active-high PB2. [Map](../hil/ddtt-f103cb.template.json),
[scenarios](../hil/common/tests/board/test_startup.py). The map is specific to WeAct GPIOB;
shared scenarios also prepare for C8, but do not apply this map to PC13.

## Added checks

- HW_STARTUP_ORDER: main starts with zero state; setup is called from main, board init and
  POST from setup. GPIO/SysTick ready before UART, UART before POST, setup published before loop.
- HW_SYSTICK_PROGRESS: two consecutive ISR entries, exception 15, exactly one counter increment.
  Checks configuration and handler behaviour, not wall-clock timing.
- HW_ADC_INITIALIZATION: ADC on, /2, software trigger, calibration complete, long internal-channel
  sampling, VREFINT before temperature. Observe the existing C++ convert; never call init again.

Russian comments follow the owner's preference. Structure follows mcu_power_board:
preconditions → observation → records → assertion tables. Table strings are GDB expressions;
scalar check strings are Python data. Compare masks with masks, normalize booleans explicitly.
CMSIS is evaluated in the owning compilation unit. Records use ordinary numbers and string keys.
Macro preflight uses SysTick_Handler because the pinned validator rejects C++ post::run as
macros.context; actual ADC observations occur in convert in post.cpp.

## Verified on 2026-10-15

Windows, OpenOCD 0.12.0/ST-Link, WeAct F103CB, xPack 14.2.1-1.1 (GDB 15.2.90), module eb085b3
(post-v0.4.1 main; Python package still says 0.4.1, not released 0.4.2). All 15 hardware cases
PASS, capture SAVED, command 0. Both profiles host 16/16. Map: 33 CONFIRMED links on 28 lines,
zero FAILED/UNKNOWN. This is the selected mapping, not full firmware coverage. C/C++ unchanged;
C8 hardware was not run. The initial preflight contract ERROR is preserved locally; no target
was involved. Existing watchpoint inferred_stop warnings remain in the evidence.

## Mapping rationale

Function call sites map to confirmed caller frames; initialization writes map to state before the
next phase; publications map to observed values; failure branches map to existing injections.
No whole-body colouring merely from reaching an entry. CAL completion is not mapped to the line
setting CAL: completion alone does not prove that write occurred. Channel order and calibration
still remain assertions in the report.

| Source line | Scenario | Exact assertion name |
| --- | --- | --- |
| [src/app.cpp:50](../src/app.cpp#L50) | `HW_BLINK` | toggles a half period apart, ms |
| [src/app.cpp:51](../src/app.cpp#L51) | `HW_BLINK` | LED state changed |
| [src/app.cpp:52](../src/app.cpp#L52) | `HW_BLINK` | blink counter advanced by one |
| [src/app.cpp:42](../src/app.cpp#L42) | `HW_POST_VDDA_LOW` | setup still finished |
| [src/app.cpp:42](../src/app.cpp#L42) | `HW_SETUP_DONE` | setup finished |
| [src/app.cpp:41](../src/app.cpp#L41) | `HW_TOGGLE_WRITERS` | setup() stores the start time, called from main() |
| [src/app.cpp:50](../src/app.cpp#L50) | `HW_TOGGLE_WRITERS` | loop() stores the toggle time, called from main() |
| [src/main.cpp:6](../src/main.cpp#L6) | `HW_STARTUP_ORDER` | setup called from main |
| [src/main.cpp:9](../src/main.cpp#L9) | `HW_STARTUP_ORDER` | loop called from main |
| [src/app.cpp:32](../src/app.cpp#L32) | `HW_STARTUP_ORDER` | board init called from setup |
| [src/app.cpp:33](../src/app.cpp#L33) | `HW_STARTUP_ORDER` | UART transmitter before POST |
| [src/app.cpp:38](../src/app.cpp#L38) | `HW_STARTUP_ORDER` | POST called from setup |
| [src/app.cpp:42](../src/app.cpp#L42) | `HW_STARTUP_ORDER` | setup published before loop |
| [src/board.cpp:34](../src/board.cpp#L34) | `HW_STARTUP_ORDER` | LED clock before UART |
| [src/board.cpp:36](../src/board.cpp#L36) | `HW_STARTUP_ORDER` | LED initially off |
| [src/board.cpp:38](../src/board.cpp#L38) | `HW_STARTUP_ORDER` | LED output before UART |
| [src/board.cpp:52](../src/board.cpp#L52) | `HW_STARTUP_ORDER` | SysTick reload before UART |
| [src/board.cpp:52](../src/board.cpp#L52) | `HW_STARTUP_ORDER` | SysTick enabled before UART |
| [src/board.cpp:94](../src/board.cpp#L94) | `HW_SYSTICK_PROGRESS` | SysTick handler increments once |
| [src/uart.cpp:9](../src/uart.cpp#L9) | `HW_STARTUP_ORDER` | UART clocks before POST |
| [src/uart.cpp:12](../src/uart.cpp#L12) | `HW_STARTUP_ORDER` | UART pin before POST |
| [src/uart.cpp:14](../src/uart.cpp#L14) | `HW_STARTUP_ORDER` | UART divider before POST |
| [src/uart.cpp:15](../src/uart.cpp#L15) | `HW_STARTUP_ORDER` | UART transmitter before POST |
| [src/post.cpp:51](../src/post.cpp#L51) | `HW_ADC_INITIALIZATION` | ADC clock divider |
| [src/post.cpp:52](../src/post.cpp#L52) | `HW_ADC_INITIALIZATION` | ADC clock enabled before sample |
| [src/post.cpp:56](../src/post.cpp#L56) | `HW_ADC_INITIALIZATION` | ADC independent single conversion |
| [src/post.cpp:57](../src/post.cpp#L57) | `HW_ADC_INITIALIZATION` | ADC enabled with internal sensors |
| [src/post.cpp:57](../src/post.cpp#L57) | `HW_ADC_INITIALIZATION` | ADC software trigger |
| [src/post.cpp:59](../src/post.cpp#L59) | `HW_ADC_INITIALIZATION` | internal channels long sampling |
| [src/post.cpp:60](../src/post.cpp#L60) | `HW_ADC_INITIALIZATION` | one regular conversion |
| [src/post.cpp:100](../src/post.cpp#L100) | `HW_POST_VDDA_LOW` | VDDA computed from the substituted sample |
| [src/post.cpp:107](../src/post.cpp#L107) | `HW_POST_VDDA_LOW` | POST reports VDDA out of range |
| [src/post.cpp:95](../src/post.cpp#L95) | `HW_POST_ADC_CLEANUP` | ADC and internal sensors released |
| [src/app.cpp:55](../src/app.cpp#L55) | `HW_DMA_CAPTURE` | block accepted exactly once |
| [src/monitor.cpp:21](../src/monitor.cpp#L21) | `HW_DMA_CAPTURE` | DMA clock enabled |
| [src/monitor.cpp:26](../src/monitor.cpp#L26) | `HW_DMA_CAPTURE` | ADC scan enabled |
| [src/monitor.cpp:28](../src/monitor.cpp#L28) | `HW_DMA_CAPTURE` | ADC scans two channels |
| [src/monitor.cpp:30](../src/monitor.cpp#L30) | `HW_DMA_CAPTURE` | ADC channel order |
| [src/monitor.cpp:31](../src/monitor.cpp#L31) | `HW_DMA_CAPTURE` | DMA halfword normal mode |
| [src/monitor.cpp:32](../src/monitor.cpp#L32) | `HW_DMA_CAPTURE` | DMA peripheral address |
| [src/monitor.cpp:33](../src/monitor.cpp#L33) | `HW_DMA_CAPTURE` | DMA owned buffer address |
| [src/monitor.cpp:48](../src/monitor.cpp#L48) | `HW_DMA_CAPTURE` | DMA block length |
| [src/monitor.cpp:97](../src/monitor.cpp#L97) | `HW_DMA_CAPTURE` | DMA transfer completed |
| [src/monitor.cpp:107](../src/monitor.cpp#L107) | `HW_DMA_CAPTURE` | one IRQ per block |
| [src/monitor.cpp:109](../src/monitor.cpp#L109) | `HW_DMA_CAPTURE` | block accepted exactly once |
| [src/monitor.cpp:84](../src/monitor.cpp#L84) | `HW_DMA_TIMEOUT` | missing requests timed out |
| [src/monitor_processing.cpp:9](../src/monitor_processing.cpp#L9) | `HW_DMA_PROCESS` | first voltage seeds filter |
| [src/monitor_processing.cpp:17](../src/monitor_processing.cpp#L17) | `HW_DMA_PROCESS` | Kalman second voltage |
| [src/monitor_processing.cpp:50](../src/monitor_processing.cpp#L50) | `HW_DMA_PROCESS` | temperature conversion |
| [src/monitor_processing.cpp:55](../src/monitor_processing.cpp#L55) | `HW_DMA_PROCESS` | two valid blocks accepted |
| [src/monitor_processing.cpp:26](../src/monitor_processing.cpp#L26) | `HW_DMA_PROCESS` | two invalid blocks rejected |
| [src/monitor_processing.cpp:38](../src/monitor_processing.cpp#L38) | `HW_DMA_PROCESS` | bad block preserves filter |
| [src/monitor_processing.cpp:51](../src/monitor_processing.cpp#L51) | `HW_DMA_CAPTURE` | DMA voltage plausible |
| [src/monitor_processing.cpp:52](../src/monitor_processing.cpp#L52) | `HW_DMA_CAPTURE` | DMA temperature plausible |

## Repeat and view in VS Code

Open the project folder, run Coverage Gutters → Watch and open src/main.cpp, board.cpp, uart.cpp
or post.cpp. Workspace discovery is limited to build/ddtt-view/lcov.info, with no personal
absolute paths. For stale marks use Remove Coverage then Watch (or Display Coverage).
Green means a confirmed assertion, red an executed failed assertion; unmarked means no trusted
evidence. See build/ddtt-view/ddtt-evidence.json for reasons. Source/ELF hashes are checked.
After source edits, rebuild and rerun; rebinding alone is insufficient. Use an isolated campaign.
The following PowerShell commands run from the project root, clear old marks before the run,
stop on a failed command, and export retained evidence even after FAIL/ERROR. The selected
cases come from the map; use ctest --preset f103cb-hil-hw for the full hardware suite.

```powershell
# Из корня проекта; новая папка кампании при каждом повторении.
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host
$campaign = "build/ddtt-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force "$campaign/runs", build/ddtt-view | Out-Null
# Удаляем старые цветные отметки до новой серии, включая случай её аварийного завершения.
Set-Content build/ddtt-view/lcov.info -Value ''
$session = Get-Content build/f103cb-hil/hwtest/session.json -Raw | ConvertFrom-Json
$session.out = (Resolve-Path "$campaign/runs").Path
$session | ConvertTo-Json -Depth 20 | Set-Content "$campaign/session.json" -Encoding utf8
python modules/stm32-gdbtest/examples/ddtt-coverage/bind_map.py --project . --elf build/f103cb-hil/stm32_hwtest_bluepill.elf --template hil/ddtt-f103cb.template.json --out "$campaign/map.json"
# Все сценарии, указанные картой; остальные аппаратные проверки — ctest --preset f103cb-hil-hw.
$cases = (Get-Content hil/ddtt-f103cb.template.json -Raw | ConvertFrom-Json).points.scenario | Sort-Object -Unique
foreach ($case in $cases) {
    python modules/stm32-gdbtest/stm32_gdbtest/cli.py run --session "$campaign/session.json" --stand hil/F103CB/stands/local.toml --identity-policy strict --test $case
    if ($LASTEXITCODE -ne 0) { break } # Сохраняем отказ; сначала разбираем его причину.
}
# Выполнить и при FAIL/ERROR: неизвестное не станет зелёным или фиктивным нулём.
python modules/stm32-gdbtest/tools/ddtt_coverage.py --project . --map "$campaign/map.json" --runs "$campaign/runs" --out build/ddtt-view
```

## Limits

ODR does not prove physical light; UART configuration/TC do not prove pin waveforms. ADC settings
are not sensor accuracy; debugger stops do not measure real-time deadlines. DMA, filtering and
the button are future work. New scenarios do not inject SRAM or modify peripheral registers.

Current stage: [ADC/DMA and HTML report](ADC_DMA.en.md), 64 links on 55 lines; the acceptance above describes the original startup series.
