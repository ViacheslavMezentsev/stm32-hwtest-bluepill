# Rules for developers and AI agents

Communicate with the owner in Russian. Documentation is bilingual: Russian is primary
(`*.md`), English is the translation (`*.en.md`); this file is English only.

## Project

A small demo of [stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest)
(DDTT: debugger-driven testing on target) on STM32F103 boards, built with CMake and
CMSIS only. Boards: `F103C8_PC13` (common Blue Pill, LED PC13 active low) and
`F103CB_PB2` (WeAct BluePill-Plus v1.1, LED PB2 active high).

| Path | Contents |
| --- | --- |
| `src/` | Application C++17: `setup()`/`loop()`, board, POST (ADC), UART |
| `cmsis/` | Unmodified CMSIS subset from STM32CubeF1 v1.8.7; do not edit or reformat |
| `ld/` | Own linker script template (Flash size from `BOARD`) |
| `cmake/` | Toolchain (`arm-gcc.cmake`) and HIL integration (`hil.cmake`) |
| `emu/renode/`, `tools/renode_smoke.py` | Renode model and smoke test (`ctest -L emu`) |
| `hil/` | HIL: `sessions/` (run configuration per board), `profiles/` (MCU descriptions), `boards/` (board data), `api.toml`, `tests/` (scenarios, requirements, contracts), `stands/` (examples), `tools/` |
| `.claude/skills/` | Copies of the stm32-gdbtest skills (`stm32-gdbtest-integrate`, `-scenarios`, `-run`); refresh with the submodule |
| `modules/stm32-gdbtest` | Git submodule, pinned to v0.3.0 |

## Build and checks

```powershell
cmake --preset Debug_F103C8; cmake --build --preset Debug_F103C8
cmake --preset HIL_F103CB;  cmake --build --preset HIL_F103CB
ctest --preset Debug_F103CB-emu         # Renode smoke test (RENODE_BINARY or PATH)
ctest --preset HIL_F103CB-host          # no board: traceability and prepare.*
ctest --preset HIL_F103CB-hw            # on the board, needs hil/stands/F103CB.local.toml
clang-format --dry-run --Werror src/*.cpp src/*.hpp
```

Requirements: CMake ≥ 3.25, Ninja, xPack GNU Arm 14.2.1-1.1 (`ARM_TOOLCHAIN_ROOT` or
`%USERPROFILE%/xpack-arm-none-eabi-gcc-14.2.1-1.1`), Python ≥ 3.11 for HIL.

## Rules

1. Keep `setup()`/`loop()` and the global state (`g_app`, `g_post`, `g_led`) readable
   from GDB: the HIL scenarios depend on these names. Renaming them means updating
   `hil/tests` and `hil/tests/requirements.md` in the same commit. Data read only by the
   scenarios must survive optimization and `--gc-sections`: `g_led` is `const volatile` for
   this reason (a plain `const` was folded away and HW_BLINK failed with "Missing ELF symbol").
2. Every `@case` ID has a `## HW_...` section in `hil/tests/requirements.md`. Scenarios follow
   the stm32-gdbtest API of the pinned submodule (v0.3.0) and its scenario style
   (`skills/stm32-gdbtest-scenarios` in the module; check with
   `python modules/stm32-gdbtest/tests/host/test_scenario_style.py hil/tests/board/*.py`).
   Board-specific expectations belong in `hil/boards/<BOARD>.toml`, scenario parameters in `hil/api.toml`.
3. No LTO (see `hil/README.md`). No HAL; registers through CMSIS names.
4. Format `src/` with the repository `.clang-format`; never reformat `cmsis/`.
5. Never commit `*.local.toml` stands, probe serial numbers, personal paths or `build/`.
6. Update `CHANGELOG.md` and `CHANGELOG.en.md` (`[Unreleased]`) for user-visible changes;
   keep RU and EN documents in sync.
7. Branches `<agent>/<task>` from an up-to-date `main`; signed Conventional Commits in
   English without links to chat sessions, ending with one `Co-authored-by:` line of the agent
   that took part. Push, `git land`, tags and releases are done by the owner, after the CI of the
   published branch is green.
8. Do not claim hardware results that were not run; state what was checked and how.
