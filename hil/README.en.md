# stm32-hwtest-bluepill HIL tests

[Русский](README.md)

[stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) scenarios check the
running firmware on the board: the runner on Windows starts the debugger's GDB server, GDB
resets the MCU, stops in `main()` and runs a Python scenario. Reports are JSON and JUnit.
No test code is added to the firmware.

## Contents

```text
hil/
  sessions/<BOARD>.toml        board run configuration: MCU description, api.toml, board data file
  profiles/F103C8_PC13.toml    MCU description: Flash 64 KiB, DEV_ID 0x410, 6 breakpoints
  profiles/F103CB_PB2.toml     the same, Flash 128 KiB
  boards/<BOARD>.toml          board data file: name, LED pin and active level, UART speed
  api.toml                     scenario parameters: blink half period, POST limits, injection value
  tests/requirements.md        HW_* requirements (shared by both boards)
  tests/contracts.json         contracts: CMSIS macros in the ELF debug info
  tests/board/test_boot.py     HW_BOOT, HW_BOOT_CMSIS, HW_BOARD_PROFILE — chip, clock, profile
  tests/board/test_board.py    HW_GPIO_CONFIG, HW_UART_CONFIG — LED pin and USART1
  tests/board/test_app.py      HW_SETUP_DONE, HW_POST, HW_BLINK, HW_TOGGLE_WRITERS
  tests/board/test_injection.py  HW_LED_FORCED_STATE, HW_POST_VDDA_LOW — injections
  stands/*.example.toml        stand examples: ST-LINK GDB Server, OpenOCD, J-Link
  tools/results.py             run results summary
```

The board is chosen by the build: presets `HIL_F103C8` and `HIL_F103CB` set `BOARD` and
`BLUEPILL_HIL=ON`; `cmake/hil.cmake` attaches stm32-gdbtest v0.3.0 (`modules/stm32-gdbtest`) with
the run configuration `hil/sessions/<BOARD>.toml` (`SESSION_CONFIG`) and the shared scenarios `hil/tests`.
The configuration ties the MCU description, the shared `api.toml` and the board data file together;
scenarios read them through `t.profile` (`t.profile.data["board"]`, `t.profile.get("user.post.vdda_mv")`),
so one scenario serves both boards and board-specific expectations live in data, not in code.
The scenarios use API 0.3.0 and pass the module style test:
`python modules/stm32-gdbtest/tests/host/test_scenario_style.py hil/tests/board/*.py`.

## Stand

A stand is a local file describing the board's debugger. Copy an example and set the
debugger serial number (`*.local.toml` files are not committed):

| Board | Stand file | Presets |
| --- | --- | --- |
| Blue Pill (F103C8_PC13) | `hil/stands/F103C8.local.toml` | `HIL_F103C8`, `HIL_F103C8-host`, `HIL_F103C8-hw` |
| BluePill-Plus (F103CB_PB2) | `hil/stands/F103CB.local.toml` | `HIL_F103CB`, `HIL_F103CB-host`, `HIL_F103CB-hw` |

| Debugger | Example | Serial number |
| --- | --- | --- |
| ST-Link, ST-LINK GDB Server (STM32CubeCLT) | `stlink.example.toml` | `STM32_Programmer_CLI -l st` |
| ST-Link, OpenOCD | `openocd.example.toml` | the same ST-Link serial |
| J-Link | `jlink.example.toml` | decimal number from J-Link Commander |

Environment check without accessing the board:

```powershell
python -B modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/stands/F103CB.local.toml
```

## Running

```powershell
cmake --preset HIL_F103CB
cmake --build --preset HIL_F103CB
ctest --preset HIL_F103CB-host     # no board: requirement traceability and prepare.*
ctest --preset HIL_F103CB-hw       # on the board: all hw.* (11 scenarios)
python hil/tools/results.py --runs build/HIL_F103CB/hwtest/runs
```

The test presets use the `strict` identity policy: the chip DEV_ID must match the MCU
description. The firmware is programmed only if the Flash image differs
(`flash = "if-different"` in the stand). In VS Code the same actions are the "HIL: …"
tasks (the board is picked from a list) and the Testing panel, where every scenario shows
up as `hw.<ID>` and `prepare.<ID>`.

| Scenario | Checks | Techniques ([catalogue](https://github.com/ViacheslavMezentsev/stm32-gdbtest/blob/v0.3.0/docs/en/TESTING_TECHNIQUES.md)) |
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

**Results.** A run directory `build/HIL_<board>/hwtest/runs/<time>-<ID>-<pid>/` contains
`result.json`, GDB and server logs, the ELF snapshot and the build manifest.
