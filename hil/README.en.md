# stm32-hwtest-bluepill HIL tests

[Русский](README.md)

[stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) scenarios check the
running firmware on the board: the runner on Windows starts the debugger's GDB server, GDB
resets the MCU, stops in `main()` and runs a Python scenario. Reports are JSON and JUnit.
No test code is added to the firmware.

## Contents

```text
hil/
  profiles/F103C8_PC13.toml   MCU description: Flash 64 KiB, DEV_ID 0x410, 6 breakpoints
  profiles/F103CB_PB2.toml    the same, Flash 128 KiB
  tests/requirements.md       HW_* requirements (shared by both boards)
  tests/board/test_boot.py    HW_BOOT — boot, HSI 8 MHz clock
  tests/board/test_app.py     HW_SETUP_DONE, HW_POST, HW_BLINK
  stands/*.example.toml       stand examples: ST-LINK GDB Server, OpenOCD, J-Link
  tools/results.py            run results summary
```

The board is chosen by the build: presets `HIL_F103C8` and `HIL_F103CB` set `BOARD` and
`BLUEPILL_HIL=ON`; `cmake/hil.cmake` attaches stm32-gdbtest (`modules/stm32-gdbtest`) with
the MCU description `hil/profiles/<BOARD>.toml` and the shared scenarios `hil/tests`.

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
ctest --preset HIL_F103CB-hw       # on the board: hw.HW_BOOT, hw.HW_SETUP_DONE, hw.HW_POST, hw.HW_BLINK
python hil/tools/results.py --runs build/HIL_F103CB/hwtest/runs
```

The test presets use the `strict` identity policy: the chip DEV_ID must match the MCU
description. The firmware is programmed only if the Flash image differs
(`flash = "if-different"` in the stand). In VS Code the same actions are the "HIL: …"
tasks (the board is picked from a list) and the Testing panel, where every scenario shows
up as `hw.<ID>` and `prepare.<ID>`.

| Scenario | Checks |
| --- | --- |
| `HW_BOOT` | stop in `main()`, SYSCLK from HSI, `SystemCoreClock = 8000000` |
| `HW_SETUP_DONE` | `setup()` returned, `g_app.setup_done = 1`, SysTick 1 ms |
| `HW_POST` | `g_post.status = PostOk`, VDDA 2900–3600 mV, temperature −10…+85 °C |
| `HW_BLINK` | between two `board::ledToggle()` calls the LED toggled, the counter +1 |

## Notes

**No LTO.** With LTO the compiler inlines and reorders functions across translation
units, creates clones (`[clone .constprop.0]`) and drops functions without external
calls. Breakpoints then land in the wrong place or cannot be set, and the step order of a
scenario no longer follows the source. Flash size does not matter for this demo, so no
build uses LTO. If a production build needs LTO, keep a separate HIL build without it (as
the STM32G474 project described in the stm32-gdbtest documentation does).

**STM32F103C8 with 128 KiB.** Many C8 chips report 128 KiB in the Flash size register.
stm32-gdbtest reports this as a warning even with `strict`: the DEV_ID matches.

**J-Link and F103CB.** The J-Link device name `STM32F103CB` for the `STM32F103CBT6` MCU is
available in stm32-gdbtest after v0.1.0-rc.1. With the submodule at tag v0.1.0-rc.1, J-Link
is rejected for the `F103CB_PB2` profile ("mapping not validated"); use ST-Link or update
the submodule to `main`.

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

**Results.** A run directory `build/HIL_<board>/hwtest/runs/<time>-<ID>-<pid>/` contains
`result.json`, GDB and server logs, the ELF snapshot and the build manifest.
