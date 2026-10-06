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

- `HW_BOOT_CMSIS` scenario: boot checks through CMSIS names (`RCC->CFGR & RCC_CFGR_SWS`,
  `DBGMCU_IDCODE_DEV_ID`, `FLASHSIZE_BASE`) and the `cmsis_boot_macros` contract that checks the
  macros in the ELF without a board (`prepare.HW_BOOT_CMSIS`).

### Changed

- stm32-gdbtest updated to v0.3.0. The board is described by the run configuration `hil/sessions/<BOARD>.toml`
  (`SESSION_CONFIG` instead of `PROFILE`): the MCU description, the shared `hil/api.toml` with scenario
  parameters and the board data file `hil/boards/<BOARD>.toml` (LED pin and active level, UART speed).
- Scenarios rewritten on API 0.3.0: `check(rows)` tables, expectations by CMSIS names and from the board data
  file, `read`/`evaluate` instead of `value`, macro contracts per scenario group; the module test checks the style.
- The board name is the global array `g_board_name` (was `static`): scenarios read it as a C string.

### Added

- Scenarios `HW_BOARD_PROFILE` (run profile, board string, vector table, refused peripheral read),
  `HW_GPIO_CONFIG`, `HW_UART_CONFIG`, `HW_TOGGLE_WRITERS` (watch point and frame chain),
  `HW_LED_FORCED_STATE` (substituted `ledIsOn()` return) and `HW_POST_VDDA_LOW` (substituted VREFINT sample).
- stm32-gdbtest agent skills in `.claude/skills/`: integration, scenarios, runs.

### Fixed

- The HIL build uses `-fno-eliminate-unused-debug-types`: without it `HW_BOOT_CMSIS` failed on
  `DBGMCU->IDCODE` with "No symbol \"DBGMCU_TypeDef\"" — the unused CMSIS type was not in the
  debug info.

- `g_led` is `const volatile`: the constant was folded into the code, `--gc-sections` removed
  the variable and `HW_BLINK` failed with "Missing ELF symbol \"g_led\"".
- GitHub Actions: formatting, six presets built, Renode, HIL checks without a board.
