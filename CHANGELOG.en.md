# Changelog

All notable changes are documented in this file ([Русский](CHANGELOG.md)).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added

- An stm32-gdbtest demo project on STM32F103: profiles `F103C8_PC13` (Blue Pill, LED PC13)
  and `F103CB_PB2` (WeAct BluePill-Plus v1.1, LED PB2).
- Build with CMake ≥ 3.25 + Ninja + xPack GCC 14.2.1, CMSIS only (a subset of STM32CubeF1
  v1.8.7), own linker script; Debug/Release/HIL presets for both boards, VS Code.
- C++17 firmware: `setup()`/`loop()`, 1 Hz LED blink on HSI 8 MHz, POST through the ADC
  (VDDA via VREFINT and the die temperature), output on USART1 (PA9, 115200).
- HIL: stm32-gdbtest as a submodule, scenarios `HW_BOOT`, `HW_SETUP_DONE`, `HW_POST`,
  `HW_BLINK`, Windows stand examples for ST-LINK GDB Server, OpenOCD and J-Link.
- Renode 1.16 smoke test (`ctest -L emu`, `Debug_*-emu` presets): UART, `setup()`, blink;
  added only when Renode is found (`BLUEPILL_RENODE_TEST`, off in the HIL presets).
- Python for HIL is looked up on `PATH` first (`Python3_FIND_REGISTRY=LAST`).

### Fixed

- `g_led` is `const volatile`: the constant was folded into the code, `--gc-sections` removed
  the variable and `HW_BLINK` failed with "Missing ELF symbol \"g_led\"".
- GitHub Actions: formatting, six presets built, Renode, HIL checks without a board.
