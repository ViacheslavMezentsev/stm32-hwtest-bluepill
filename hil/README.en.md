# stm32-hwtest-bluepill HIL tests

[Русский](README.md)

[stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) scenarios check the
running firmware on the board: the runner on Windows starts the debugger's GDB server, GDB
resets the MCU, stops in `main()` and runs a Python scenario. Reports are JSON and JUnit.
No test code is added to the firmware.

## Contents

```text
hil/
  common/tests/       board/test_*.py, requirements.md, contracts.json
  common/plans/       DDTT
  F103C8/             session.toml, target.toml, board.toml, stands/
  F103CB/             session.toml, target.toml, board.toml, stands/
  templates/          *.example.toml
  tools/              results.py
  api.toml
```

The board is chosen by the build: presets `f103c8-hil` and `f103cb-hil` set `BOARD` and
`BLUEPILL_HIL=ON`; `cmake/hil.cmake` attaches stm32-gdbtest `a7b0951` (API 3, 0.5.0 final candidate) (`modules/stm32-gdbtest`) with
the run configuration `hil/<MCU>/session.toml` (`SESSION_CONFIG`) and the shared scenarios `hil/common/tests`.
The configuration ties the MCU description, the shared `api.toml` and the board data file together;
scenarios read them through `t.profile` (`t.profile.data["board"]`, `t.profile.get("user.post.vdda_mv")`),
so one scenario serves both boards and board-specific expectations live in data, not in code.
The scenarios use the pinned module API (API_VERSION=3) and pass the module style test:
`python modules/stm32-gdbtest/tests/host/test_scenario_style.py hil/common/tests/board/*.py`.

## Stand

A stand is a local file describing the board's debugger. Copy an example and set the
debugger serial number (`*.local.toml` files are not committed):

| Board | Stand file | Presets |
| --- | --- | --- |
| Blue Pill (F103C8_PC13) | `hil/F103C8/stands/local.toml` | `f103c8-hil`, `f103c8-hil-host`, `f103c8-hil-hw` |
| BluePill-Plus (F103CB_PB2) | `hil/F103CB/stands/local.toml` | `f103cb-hil`, `f103cb-hil-host`, `f103cb-hil-hw` |

| Debugger | Example | Serial number |
| --- | --- | --- |
| ST-Link, ST-LINK GDB Server (STM32CubeCLT) | `stlink.example.toml` | `STM32_Programmer_CLI -l st` |
| ST-Link, OpenOCD | `openocd.example.toml` | the same ST-Link serial |
| J-Link | `jlink.example.toml` | decimal number from J-Link Commander |

Environment check without accessing the board:

```powershell
python -B modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/F103CB/stands/local.toml
```

## Running

```powershell
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host     # no board: requirement traceability and prepare.*
ctest --preset f103cb-hil-hw       # on the board: all hw.* (28 scenarios)
python hil/tools/results.py --runs build/f103cb-hil/hwtest/runs
```

The test presets use the `strict` identity policy: the chip DEV_ID must match the MCU
description. The firmware is programmed only if the Flash image differs
(`flash = "if-different"` in the stand). In VS Code the same actions are the "HIL: …"
tasks (the board is picked from a list) and the Testing panel, where every scenario shows
up as `hw.<ID>` and `prepare.<ID>`.

| Scenario | Checks | Techniques ([catalogue](https://github.com/ViacheslavMezentsev/stm32-gdbtest/blob/a7b09516abac467839ee9efc8ee286835c6001e0/docs/en/TESTING_TECHNIQUES.md)) |
| --- | --- | --- |
| `HW_BOOT` | DEV_ID and F_SIZE at the MCU description addresses, SYSCLK from HSI, `SystemCoreClock` | `t.profile`, `evaluate`, `read` |
| `HW_BOOT_CMSIS` | the same with CMSIS names on entry to `board::init()` | `check(rows)` table, contract, TECH-001 |
| `HW_BOARD_PROFILE` | `g_board_name` string = name in the board data, `BOARD_*` in the build, vector table, refused peripheral read | TECH-017, TECH-018, `memory`, `refused` |
| `HW_GPIO_CONFIG` | LED pin from the board data: clock, mode, `g_led` | expectations from `profile.data`, TECH-001 |
| `HW_UART_CONFIG` | USART1: clocks, PA9, BRR divider for the board data speed, TE/RE, TC | table, contract |
| `HW_SETUP_DONE` | `setup()` returned, SysTick 1 ms | `read`, table |
| `HW_POST` | `PostOk`, VDDA and temperature within the `api.toml` limits, ADC off | `within`, `profile.get`, `record` |
| `HW_BLINK` | LED level flips, counter +1, interval is a half period | struct `read`, `within` |
| `HW_TOGGLE_WRITERS` | `g_app.last_toggle_ms` is written by `setup()` and `loop()`, both from `main()` | `watch`, `frames`, TECH-013 |
| `HW_LED_FORCED_STATE` | `ledToggle()` sets the level opposite to the `ledIsOn()` answer | `ret`, `finish`, TECH-004 |
| `HW_POST_VDDA_LOW` | a substituted VREFINT sample gives VDDA 1638 mV and `PostVddaOutOfRange`, the application starts | `watch`, `write`, TECH-005 |

## Notes

**CMSIS macros in scenarios.** GDB expands macros (`RCC`, `RCC_CFGR_SWS`, …) when the build
uses `-g3` (Debug, all HIL presets) and the current stop is in a translation unit that
includes `stm32f1xx.h`. `main.cpp` does not include it, so `HW_BOOT_CMSIS` first reaches
`board::init()`. The `cmsis_boot_macros` contract checks that the macros are in the ELF already
in `prepare.HW_BOOT_CMSIS`, without a board: if a macro disappears (another header, a build
without `-g3`), the error comes before Flash programming, not in the middle of a scenario. The
contract context is a function with a plain name from the same translation unit
(`SysTick_Handler`); names like `board::init` are not supported in contracts.

A macro such as `DBGMCU` expands to a cast (`(DBGMCU_TypeDef *)…`). GCC omits types the firmware
does not use from the debug info, and GDB answers `No symbol "DBGMCU_TypeDef"`. So the HIL build
uses `-fno-eliminate-unused-debug-types` (`cmake/hil.cmake`): only the debug info grows, the
code is the same. With the stm32-gdbtest submodule newer than v0.1.0-rc.1 the contract also checks
the type of the expansion (`whatis`): without this flag `prepare.HW_BOOT_CMSIS` reports "typed DBGMCU
(No symbol \"DBGMCU_TypeDef\" …)" before any board is used.

**No LTO.** With LTO the compiler inlines and reorders functions across translation
units, creates clones (`[clone .constprop.0]`) and drops functions without external
calls. Breakpoints then land in the wrong place or cannot be set, and the step order of a
scenario no longer follows the source. Flash size does not matter for this demo, so no
build uses LTO. If a production build needs LTO, keep a separate HIL build without it (as
the STM32G474 project described in the stm32-gdbtest documentation does).

**STM32F103C8 with 128 KiB.** Many C8 chips report 128 KiB in the Flash size register.
stm32-gdbtest reports this as a warning even with `strict`: the DEV_ID matches.

**A watch point stops slightly after the write.** The Cortex-M3 DWT reports a write after the
next instruction. In `loop()` the store to `g_app.last_toggle_ms` is directly followed by the call of
`board::ledToggle()`, so `HW_TOGGLE_WRITERS` may stop at the entry of `ledToggle()`; the scenario then
takes the caller as the writer.

**A string from an array without a bound.** Translation units that see only the declaration
`extern const char g_board_name[]` give the array no size, and GDB may pick that type.
`HW_BOARD_PROFILE` therefore reads the string through a pointer: `(const char *)g_board_name`.

**OpenOCD and an "unexpected" IDCODE.** If OpenOCD reports `UNEXPECTED idcode` (usually an
MCU clone or a rare revision), manual debugging can skip the check: create
`target/stm32f1x-anyid.cfg` in the OpenOCD scripts directory (`share/openocd/scripts`):

```tcl
set CPUTAPID 0
source [find target/stm32f1x.cfg]
```

and use it in `configFiles` of the "Debug (ocd/stlink)" configuration. For HIL tests change
`openocd_target` in a local copy of the MCU description. MCU clones are not supported by
this project: the `strict` DEV_ID check still reports ERROR for them.

**Python.** Python ≥ 3.11 is required. CMake looks on `PATH` first and then in the Windows
registry (`Python3_FIND_REGISTRY=LAST`), so a Visual Studio Python does not interfere. Another
interpreter: `-DPython3_EXECUTABLE=<path>`; after a change use "Delete Cache and Reconfigure".

**Results.** A run directory `build/<mcu>-hil/hwtest/runs/<time>-<ID>-<pid>/` contains
`result.json`, GDB and server logs, the ELF snapshot and the build manifest.

## Development through DDTT

[Plan](common/plans/ddtt-feedback.en.md) and [cycle results](common/plans/ddtt-feedback-results.en.md):
the scenario first exposes the defect in baseline firmware, then checks its fix and regression.
Skill: `.claude/skills/stm32-gdbtest-develop/SKILL.md`; this branch includes a trial copy while
the module gitlink is now a7b0951, the final 0.5.0 candidate (version 0.5.0), not yet tagged. The six local skill copies are refreshed from modules/stm32-gdbtest/skills.
Unlike stand-loop execution, development needs a source checkout and compiler, not just a ZIP.
Profiles use target schema 2 with `[openocd]`; sessions enable `[results] capture = true`.

New scenario: `HW_POST_ADC_CLEANUP` (`tests/board/test_ddtt_feedback.py`).


[Developer environment](../docs/DEVELOPER_ENVIRONMENT.en.md).

New cases: `HW_STARTUP_ORDER`, `HW_SYSTICK_PROGRESS`, `HW_ADC_INITIALIZATION`.
WeAct PB2 map and rationale: [DDTT_STARTUP](../docs/DDTT_STARTUP.en.md).

[ADC/DMA, фильтрация и HTML DDTT / processing and evidence report](../docs/ADC_DMA.en.md).

Indication: HW_INDICATOR_NORMAL, HW_INDICATOR_INVALID, HW_INDICATOR_RANGE. [Behaviour and report themes](../docs/MEASUREMENT_LED.en.md).

[KEY, virtual presses and current DDTT export](../docs/BUTTON.en.md).

[DMA error and recovery](../docs/DMA_ERROR.en.md).

[POST timeouts](../docs/POST_TIMEOUT.en.md).

[Portable source highlighting for Pages (local only)](../docs/DDTT_PAGES.en.md).

[MMIO/SVD: scope, effects and offline checks](../docs/MMIO_SVD.en.md).
