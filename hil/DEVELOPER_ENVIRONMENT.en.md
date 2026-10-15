# Developer environment

[Русский](DEVELOPER_ENVIRONMENT.md) · [HIL](README.en.md)

The project uses its own CMake/CMSIS build, without stm32-cmake-yml. Firmware and scenario code
are unchanged. BOARD selects F103C8_PC13 or F103CB_PB2.

## Presets and tools

| Presets | Purpose |
| --- | --- |
| f103c8-debug / f103cb-debug | Debug, Renode and manual debugging |
| f103c8-release / f103cb-release | Release without HIL/emulation |
| f103c8-hil / f103cb-hil | Debug with CMSIS types, host/prepare and separate HW runs |

Old Debug_*, Release_* and HIL_* names are removed. Old build directories/results are retained
but not used by the new tasks. Without a preset BOARD still defaults to F103C8_PC13.
Requires CMake >= 3.25, Ninja, Python >= 3.11. ARM_TOOLCHAIN_ROOT can be a cache variable or
environment variable; fallback is xPack 14.2.1-1.1 under USERPROFILE on Windows or HOME on Linux,
then PATH. Use a fresh build directory or Delete Cache and Reconfigure when changing compilers.
Renode 1.17.0 is selected through RENODE_BINARY, RENODE_EXECUTABLE or PATH/ProgramFiles.

## Visual VS Code workflow

1. Open the project folder and install recommended CMake Tools, Microsoft C/C++ and Cortex-Debug.
   clangd is not required.
2. CMake: Select Configure Preset, e.g. f103cb-debug; Configure, select the matching Build Preset,
   then Build. cmake.useVsDeveloperEnvironment=never prevents automatic MSVC activation.
3. IntelliSense uses CMake Tools. The active compile database is copied to build/compile_commands.json.
   Code for the other BOARD may be inactive; this is expected.
4. Filter Tasks: Run Task by «Сборка:», «Проверка:», «Эмуляция:», «Прошивка:», «HIL:».
   HIL task names explicitly identify the board, avoiding different board choices in dependency dialogs.
5. Refresh Testing after switching presets. Old green icons do not certify a new run; rerun the set.
   Default HIL test presets select host only; *-hw explicitly selects hardware. Clicking an individual
   hw.* test in Testing is a hardware request; preset filters are not an access-control mechanism.
6. For manual debugging choose «Плата: OpenOCD / ST-Link». device, svdFile and toolchain are independent
   of the preset: check MCU and ELF. Set STM32F103C8 or STM32F103CB respectively. SVD is optional.
   If nested config substitutions do not expand, set gdbPath explicitly. On Linux replace USERPROFILE
   with HOME in the custom toolchain setting. With multiple probes, explicitly select serial in your
   OpenOCD configuration. Manual debugging does not automatically use the HIL stand or lock.

## Terminal without a board

```sh
cmake --preset f103cb-debug
cmake --build --preset f103cb-debug
ctest --preset f103cb-debug-emulator
cmake --build --preset f103cb-debug --target emulate
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host
```

Replace f103cb with f103c8 for C8. emulate prints UART and smoke results; logs are under
build/<preset>/renode. ADC is not modelled: UART POST FAIL is expected. Smoke checks boot,
setup completion and blinking. No mismatched QEMU board configuration is provided.

## Renode debugging

Select a debug preset and «Эмуляция: Renode (GDB)», then F5. The pre-launch task builds and starts
Renode on port 3334. Cortex-Debug connects to the loaded ELF and stops at main.
UART log: build/<preset>/renode-debug/uart.log. Disconnect may leave the server running;
enter quit in Renode or terminate that specific task before the next F5. Do not start two servers
on the same port. F5/breakpoint UI verification is separate from terminal smoke tests.

## Compact HIL layout

```text
hil/
  common/tests/          scenarios, requirements.md, contracts.json
  common/plans/          retained DDTT plans/results
  F103C8/                session.toml, target.toml, board.toml
  F103CB/                session.toml, target.toml, board.toml
    stands/              local.toml, remote.toml (ignored)
  templates/             debugger server examples
  tools/                 results viewer
  api.toml               common scenario parameters
```

Both boards share common/tests. Copy a stand template, preferring OpenOCD for ST-Link HIL.
Existing private stands were preserved under their board. F103CB selects the previously used
OpenOCD configuration. Recheck F103C8 against the actual connection before hardware use;
preserving its configuration does not certify the connected probe.

```sh
python modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/F103CB/stands/local.toml
ctest --preset f103cb-hil-hw
# After configuring remote.toml with SSH:
ctest --preset f103cb-hil-hw-remote
python hil/tools/results.py --runs build/f103cb-hil/hwtest/runs
```

Doctor does not replace a hardware test. HW is sequential with strict identity. Each attempt
has a separate runs directory; records capture is enabled. Submodule stays pinned to v0.4.1.
New feature scenarios and the DDTT map are the next stage.

## CI and acceptance

GitHub CI uses the same six presets, GCC 14.2.1, HIL host/prepare and Debug Renode 1.17.0.
The Linux Renode archive has a pinned SHA-256 and no old -dotnet filename suffix.
No hardware tests run in CI. GitHub dependency installation requires network access.
Existing src formatting remains a separate job. The user's .clang-format is not edited here;
publishing those new rules also requires aligning CI clang-format with them. Local 23.1.3
differs from Ubuntu's clang-format.

Before hardware: both Debug/Release/HIL builds, both host sets and both Renode smoke tests.
Manual VS Code checks: profile/IntelliSense switching, Testing refresh, Renode F5 and repeated launch.
Physical and remote board routes require confirming the actual connection first.

## Migration verification (2026-10-15)

Windows: all six configure/build pairs, two host sets (13/13 each), both Renode smoke tests PASS.
Linux in stm32-universal-builder using a Docker volume: the same matrix, all 16 commands successful.
Renode 1.17 + GDB reached main initially and again after Reset. A reset macro reloads the ELF and
sets VectorTableOffset; the original failed experiment is retained. GDB emitted CP1252 and SP alias
warnings, but both stops succeeded with exit 0. The emulate target prints UART and passes smoke.
Firmware, CMSIS, linker script, submodule and Python scenario code are unchanged. These checks do
not replace GitHub's network installation or VS Code UI verification. No hardware runs at this stage.
