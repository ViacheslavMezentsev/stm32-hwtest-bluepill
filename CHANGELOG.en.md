# Changelog

All notable changes are documented in this file ([Русский](CHANGELOG.md)).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), versions follow [SemVer](https://semver.org/).

## [Unreleased]

- Added RSTCAL/CAL/EOC POST timeout scenarios: 10/11 ms boundaries, ADC cleanup, normal reboot, ELF instruction preflight and twelve DDTT links. Firmware unchanged.

- Added TE and TE+TC DMA handler scenarios with real-transfer recovery and eight DDTT links; no firmware changes.

- Button: debounced hold forces the LED on; release restores measurement indication. Two HIL scenarios, 23/23 WeAct PASS; DDTT 74 links / 65 lines. Export rejects comments and stale source bindings, clears old LCOV on failure.

- Measurement LED: pending/normal/fault with recovery; three HIL scenarios, 21/21 WeAct PASS and DDTT map 64/55. GitHub-style HTML defaults to dark with a round dark/light/auto button.

- Added periodic ADC1/DMA1 capture of eight pairs, averaging and scalar Kalman filters. Three new cases, full WeAct suite 18/18, both profiles host 19/19. DDTT map: 54 links/49 lines; HTML shows scenarios, evidence and selected campaign attempts.

- Added three startup/peripheral hardware cases with Russian comments; the WeAct PB2 DDTT map now links 33 assertions to 28 source lines. Updated the submodule to accepted main eb085b3 (post-v0.4.1, not release 0.4.2). F103CB/OpenOCD: all 15 cases PASS; both profiles: host 16/16.

- Moved both developer environment guides from `hil/` to `docs/` and updated links.

- Aligned f103c8/f103cb-debug/release/hil presets, VS Code tasks and compact HIL profiles. CI uses the new names and Renode 1.17.0; firmware is unchanged.

- Pinned the module to v0.4.0, target schema 2 and capture; refreshed skills and added a trial DDTT development loop.
- POST releases ADC/sensors on early failure too. Added HW_POST_ADC_CLEANUP; the existing VDDA injection arms its watchpoint after result initialization.

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
