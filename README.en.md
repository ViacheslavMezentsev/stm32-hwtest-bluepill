# stm32-hwtest-bluepill

[Русский](README.md)

A demo project for [stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest):
checks of running firmware on an STM32F103 board (the "Blue Pill" and similar boards)
through GDB and an SWD debugger, written as Python scenarios — the DDTT method
(Debugger-Driven Testing on Target). There is no test code in the firmware.

The firmware is deliberately simple: `setup()` runs once after reset, performs a POST
(supply voltage and die temperature through the ADC) and prints the result to UART;
`loop()` blinks the user LED at 1 Hz. The only library is CMSIS.

## Boards

| Profile (`BOARD`) | Board | MCU | Flash | LED |
| --- | --- | --- | --- | --- |
| `F103C8_PC13` | common Blue Pill | STM32F103C8T6 | 64 KiB | PC13, active low |
| `F103CB_PB2` | [WeAct BluePill-Plus](https://github.com/WeActStudio/BluePill-Plus) v1.1 | STM32F103CBT6 | 128 KiB | PB2, active high |

Many STM32F103C8 chips actually contain 128 KiB of Flash (the size register reads 128):
the C8 firmware targets 64 KiB, and the identity check reports a warning, not an error.
MCU clones (CKS32, GD32, APM32 and others) are not supported: their DEV_ID and ADC differ.

## Requirements (Windows)

- [xPack GNU Arm Embedded GCC 14.2.1-1.1](https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack/releases/tag/v14.2.1-1.1)
  unpacked into `%USERPROFILE%\xpack-arm-none-eabi-gcc-14.2.1-1.1`, or its path in the
  `ARM_TOOLCHAIN_ROOT` variable;
- CMake ≥ 3.25 and Ninja on `PATH`;
- for HIL tests, Python ≥ 3.11 and one of the debuggers: ST-Link (STM32CubeCLT or OpenOCD)
  or J-Link (SEGGER J-Link Software);
- optionally [Renode 1.16.1](https://github.com/renode/renode/releases/tag/v1.16.1) for the emulator smoke test;
- optionally VS Code with CMake Tools, C/C++ and Cortex-Debug.

## Getting and building

```powershell
git clone --recursive https://github.com/ViacheslavMezentsev/stm32-hwtest-bluepill.git
cd stm32-hwtest-bluepill
cmake --preset Debug_F103C8
cmake --build --preset Debug_F103C8
```

If the repository was cloned without `--recursive`: `git submodule update --init`.

| Preset | Purpose |
| --- | --- |
| `Debug_F103C8`, `Release_F103C8` | build for the Blue Pill (`build/<preset>`) |
| `Debug_F103CB`, `Release_F103CB` | build for the BluePill-Plus |
| `HIL_F103C8`, `HIL_F103CB` | Debug build with stm32-gdbtest HIL tests |

Test presets: `Debug_F103C8-emu`, `Debug_F103CB-emu` (Renode), `HIL_*-host` and `HIL_*-hw`.

Output: `build/<preset>/stm32_hwtest_bluepill.elf`, `.hex`, `.bin`, `.map`. In VS Code the
preset is selected in the CMake Tools status bar; flashing and debugging use the
"Прошить (…)" tasks and the launch configurations for ST-Link, OpenOCD and J-Link.

## UART output

USART1, TX on PA9, 115200 baud, 8N1. After reset the board name and the POST result are
printed:

```text
stm32-hwtest-bluepill F103CB_PB2
POST: VDDA=3297 mV, T=31.4 C, OK
```

If your ST-Link has a virtual COM port (ST-Link V2-1 on Nucleo, ST-Link V3), connect the
board's PA9 to the debugger's RX (VCP_RX) and GND — the output appears on the debugger's
COM port. Common ST-Link V2 clones have no COM port: use a separate USB-UART adapter
(PA9 → RX). The POST is coarse: STM32F103 has no factory calibration of the temperature
sensor and VREFINT, the calculation uses typical datasheet values.

## Renode emulator (no board)

The smoke test runs the built firmware in [Renode](https://renode.io) 1.16: the model
`emu/renode/stm32f103.repl` (Cortex-M3 core, Flash, SRAM, SysTick, USART1; other
peripherals are stubs) and checks the UART output, `setup()` completion and the blink in
`loop()`. The ADC is not modelled, so the POST prints `FAIL` in the emulator — this is
expected.

```powershell
ctest --preset Debug_F103C8-emu          # or the VS Code task "Эмулятор: дымовой тест (Renode)"
```

The test exists only when CMake finds Renode: `RENODE_BINARY`, `PATH` or `%ProgramFiles%\Renode`;
the HIL presets and `-DBLUEPILL_RENODE_TEST=OFF` leave it out.
Logs go to `build/<preset>/renode/`. The approach and the Renode version follow
[stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml). QEMU is not used
here: its Cortex-M3 machines (`netduino2` — STM32F205, `stm32vldiscovery` — STM32F100 with
8 KiB SRAM) do not match STM32F103 memory and peripheral addresses, and the firmware reports
through USART1 rather than semihosting.

## HIL tests

The scenarios in `hil/tests/board` check the firmware on the board: boot and clock,
`setup()` completion, POST results and the LED blink. Without a board the requirement
traceability and run preparation are checked (`ctest --preset HIL_F103C8-host`); on the
board run `ctest --preset HIL_F103C8-hw` after setting up a stand. Details:
[hil/README.en.md](hil/README.en.md).

## Layout

```text
src/            firmware (C++17): main, setup/loop, board, POST, UART
cmsis/          CMSIS subset from STM32CubeF1 (unmodified)
ld/             linker script (Flash size per board)
cmake/          toolchain and HIL integration
emu/renode/     Renode model for the smoke test
tools/          renode_smoke.py — smoke test runner
hil/            MCU profiles, scenarios and requirements, stand examples, tools
modules/        stm32-gdbtest (Git submodule)
.vscode/        tasks, debug configurations, settings
.github/        GitHub Actions: formatting, build, Renode, HIL without a board
```

Development rules — [AGENTS.md](AGENTS.md), changes — [CHANGELOG.en.md](CHANGELOG.en.md).

## License

MIT ([LICENSE](LICENSE)). Files in `cmsis/` are by Arm and STMicroelectronics, Apache-2.0
([cmsis/README.md](cmsis/README.md)).
