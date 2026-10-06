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
- Дымовой тест в Renode 1.16 (`ctest -L emu`, пресеты `Debug_*-emu`): UART, `setup()`, мигание;
  добавляется, только если Renode найден (`BLUEPILL_RENODE_TEST`, в HIL-пресетах выключен).
- Python для HIL ищется сначала по `PATH` (`Python3_FIND_REGISTRY=LAST`).

- Сценарий `HW_BOOT_CMSIS`: проверки загрузки через имена CMSIS (`RCC->CFGR & RCC_CFGR_SWS`,
  `DBGMCU_IDCODE_DEV_ID`, `FLASHSIZE_BASE`) и контракт `cmsis_boot_macros`, который проверяет
  наличие макросов в ELF без платы (`prepare.HW_BOOT_CMSIS`).

### Changed

- Внешний вид приведён к общему формату с stm32-hwtest-blackpill: схема работы, раздел «Документация» со
  ссылками на stm32-gdbtest v0.3.0 и навыки агентов, итог последнего аппаратного прогона в README.
- stm32-gdbtest обновлён до v0.3.0. Плату описывает конфигурация прогона `hil/sessions/<BOARD>.toml`
  (`SESSION_CONFIG` вместо `PROFILE`): описание MCU, общий `hil/api.toml` с параметрами сценариев и файл
  данных платы `hil/boards/<BOARD>.toml` (вывод и активный уровень светодиода, скорость UART).
- Сценарии переписаны на API 0.3.0: таблицы `check(rows)`, ожидания именами CMSIS и из файла данных платы,
  `read`/`evaluate` вместо `value`, контракты макросов для каждой группы сценариев; стиль проверяет тест модуля.
- Имя платы — глобальный массив `g_board_name` (было `static`): сценарии читают его как C-строку.

### Added

- Сценарии `HW_BOARD_PROFILE` (профиль прогона, строка платы, таблица векторов, отказ чтения периферии),
  `HW_GPIO_CONFIG`, `HW_UART_CONFIG`, `HW_TOGGLE_WRITERS` (точка наблюдения и цепочка кадров),
  `HW_LED_FORCED_STATE` (подмена возврата `ledIsOn()`) и `HW_POST_VDDA_LOW` (подмена отсчёта VREFINT).
- Навыки агентов stm32-gdbtest в `.claude/skills/`: подключение, сценарии, запуск.

### Fixed

- HIL-сборка с `-fno-eliminate-unused-debug-types`: без неё `HW_BOOT_CMSIS` падал на
  `DBGMCU->IDCODE` с ошибкой «No symbol "DBGMCU_TypeDef"» — неиспользуемый тип CMSIS не попадал
  в отладочную информацию.

- `g_led` объявлен `const volatile`: константа подставлялась в код, `--gc-sections` удалял
  переменную, и `HW_BLINK` завершался ошибкой «Missing ELF symbol "g_led"».
- GitHub Actions: форматирование, сборка шести пресетов, Renode, HIL-проверки без платы.
