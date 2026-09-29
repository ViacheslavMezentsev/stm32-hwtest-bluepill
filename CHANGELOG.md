# Changelog

Все заметные изменения документируются в этом файле ([English](CHANGELOG.en.md)).
Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/), версии — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- Демонстрационный проект stm32-gdbtest на STM32F103: профили `F103C8_PC13` (Blue Pill,
  светодиод PC13) и `F103CB_PB2` (WeAct BluePill-Plus v1.1, светодиод PB2).
- Сборка CMake ≥ 3.25 + Ninja + xPack GCC 14.2.1, только CMSIS (подмножество STM32CubeF1
  v1.8.7), свой скрипт компоновщика; пресеты Debug/Release/HIL для обеих плат, VS Code.
- Прошивка на C++17: `setup()`/`loop()`, мигание светодиодом 1 Гц от HSI 8 МГц, POST через
  АЦП (VDDA по VREFINT и температура кристалла), вывод в USART1 (PA9, 115200).
- HIL: stm32-gdbtest подмодулем, сценарии `HW_BOOT`, `HW_SETUP_DONE`, `HW_POST`, `HW_BLINK`,
  примеры стендов ST-LINK GDB Server, OpenOCD и J-Link для Windows.
- Дымовой тест в Renode 1.16 (`ctest -L emu`, пресеты `Debug_*-emu`): UART, `setup()`, мигание.
- GitHub Actions: форматирование, сборка шести пресетов, Renode, HIL-проверки без платы.
