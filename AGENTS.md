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
| `hil/` | HIL: `F103C8/`, `F103CB/` (session/target/board and private stands), `common/tests/`, `common/plans/`, `templates/`, `tools/`, `api.toml` |
| `.claude/skills/` | Copies of the stm32-gdbtest skills (integration, scenarios, run, results, stand-loop and develop); refresh with the submodule |
| `modules/stm32-gdbtest` | Git submodule |

## Build and checks

```powershell
cmake --preset f103c8-debug; cmake --build --preset f103c8-debug
cmake --preset f103cb-hil;  cmake --build --preset f103cb-hil
ctest --preset f103cb-debug-emulator         # Renode smoke test (RENODE_BINARY or PATH)
ctest --preset f103cb-hil-host          # no board: traceability and prepare.*
ctest --preset f103cb-hil-hw            # on the board, needs hil/F103CB/stands/local.toml
clang-format --dry-run --Werror src/*.cpp src/*.hpp
```

Requirements: CMake ≥ 3.25, Ninja, xPack GNU Arm 14.2.1-1.1 (`ARM_TOOLCHAIN_ROOT` or
`%USERPROFILE%/xpack-arm-none-eabi-gcc-14.2.1-1.1`), Python ≥ 3.11 for HIL.

## Rules

1. Keep `setup()`/`loop()` and the global state (`g_app`, `g_post`, `g_led`) readable
   from GDB: the HIL scenarios depend on these names. Renaming them means updating
   `hil/common/tests` and `hil/common/tests/requirements.md` in the same commit. Data read only by the
   scenarios must survive optimization and `--gc-sections`: `g_led` is `const volatile` for
   this reason (a plain `const` was folded away and HW_BLINK failed with "Missing ELF symbol").
2. Every `@case` ID has a `## HW_...` section in `hil/common/tests/requirements.md`. Scenarios follow
   the stm32-gdbtest API of the pinned submodule (0.5.0 candidate, API_VERSION=3, 8fdbb58) and its scenario style
   (`skills/stm32-gdbtest-scenarios` in the module; check with
   `python modules/stm32-gdbtest/tests/host/test_scenario_style.py hil/common/tests/board/*.py`).
   Board-specific expectations belong in `hil/<MCU>/board.toml`, scenario parameters in `hil/api.toml`.
3. No LTO (see `hil/README.md`). No HAL. Firmware uses CMSIS; scenarios access registers through t.mmio and the project SVD.
4. Format `src/` with the repository `.clang-format`; never reformat `cmsis/`.
5. Never commit `*.local.toml` stands, probe serial numbers, personal paths or `build/`.
6. Update `CHANGELOG.md` and `CHANGELOG.en.md` (`[Unreleased]`) for user-visible changes;
   keep RU and EN documents in sync.
7. Branches `<agent>/<task>` from an up-to-date `main`; signed Conventional Commits in
   English without links to chat sessions. Push, tags and releases are done by the owner.
8. Do not claim hardware results that were not run; state what was checked and how.

## DDTT development loop

For firmware changes with target feedback, read `.claude/skills/stm32-gdbtest-develop/SKILL.md`
and `hil/common/plans/ddtt-feedback.en.md`. The develop skill is a trial copy accompanying this branch;
the module is pinned to main 8fdbb58 (version 0.5.0, API_VERSION=3; release candidate, not yet tagged). Preserve red attempts, then verify the unchanged
assertion and adjacent scenarios after fixing production code. No test hooks.

Developer workflows: [docs/DEVELOPER_ENVIRONMENT.en.md](docs/DEVELOPER_ENVIRONMENT.en.md).

New scenario comments may be in Russian, as requested by the owner; retain RU/EN module summaries.
