# HIL-тесты stm32-hwtest-bluepill

[English](README.en.md)

Сценарии [stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) проверяют
работающую прошивку на плате: runner на Windows запускает GDB-сервер отладчика, GDB
сбрасывает MCU, останавливается в `main()` и выполняет сценарий на Python. Отчёты — JSON и
JUnit. В прошивку тестовый код не добавляется.

## Состав

```text
hil/
  profiles/F103C8_PC13.toml   описание MCU: Flash 64 КиБ, DEV_ID 0x410, 6 точек останова
  profiles/F103CB_PB2.toml    то же, Flash 128 КиБ
  tests/requirements.md       требования HW_* (общие для обеих плат)
  tests/contracts.json        контракт cmsis_boot_macros: макросы CMSIS в отладочной информации ELF
  tests/board/test_boot.py    HW_BOOT — загрузка, тактирование от HSI 8 МГц (адреса регистров)
  tests/board/test_boot_cmsis.py  HW_BOOT_CMSIS — то же через имена CMSIS
  tests/board/test_app.py     HW_SETUP_DONE, HW_POST, HW_BLINK
  stands/*.example.toml       примеры стендов: ST-LINK GDB Server, OpenOCD, J-Link
  tools/results.py            сводка результатов запусков
```

Плата выбирается сборкой: пресеты `HIL_F103C8` и `HIL_F103CB` задают `BOARD` и
`BLUEPILL_HIL=ON`, `cmake/hil.cmake` подключает stm32-gdbtest (`modules/stm32-gdbtest`) с
описанием MCU `hil/profiles/<BOARD>.toml` и общими сценариями `hil/tests`.

## Стенд

Стенд — локальный файл с отладчиком платы. Скопируйте нужный пример и укажите серийный
номер отладчика (файлы `*.local.toml` не коммитятся):

| Плата | Файл стенда | Пресеты |
| --- | --- | --- |
| Blue Pill (F103C8_PC13) | `hil/stands/F103C8.local.toml` | `HIL_F103C8`, `HIL_F103C8-host`, `HIL_F103C8-hw` |
| BluePill-Plus (F103CB_PB2) | `hil/stands/F103CB.local.toml` | `HIL_F103CB`, `HIL_F103CB-host`, `HIL_F103CB-hw` |

| Отладчик | Пример | Серийный номер |
| --- | --- | --- |
| ST-Link, ST-LINK GDB Server (STM32CubeCLT) | `stlink.example.toml` | `STM32_Programmer_CLI -l st` |
| ST-Link, OpenOCD | `openocd.example.toml` | тот же серийный номер ST-Link |
| J-Link | `jlink.example.toml` | десятичный номер из J-Link Commander |

Проверка окружения без обращения к плате:

```powershell
python -B modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/stands/F103CB.local.toml
```

## Запуск

```powershell
cmake --preset HIL_F103CB
cmake --build --preset HIL_F103CB
ctest --preset HIL_F103CB-host     # без платы: трассировка требований и prepare.*
ctest --preset HIL_F103CB-hw       # на плате: все hw.* (5 сценариев)
python hil/tools/results.py --runs build/HIL_F103CB/hwtest/runs
```

Тестовые пресеты задают политику идентичности `strict`: DEV_ID кристалла должен совпасть с
описанием MCU. Прошивка записывается, только если образ во Flash отличается
(`flash = "if-different"` в стенде). В VS Code те же действия — задачи «HIL: …» (плата
выбирается из списка) и панель «Testing», где каждый сценарий виден как `hw.<ID>` и
`prepare.<ID>`.

| Сценарий | Что проверяет |
| --- | --- |
| `HW_BOOT` | остановка в `main()`, SYSCLK от HSI, `SystemCoreClock = 8000000` |
| `HW_BOOT_CMSIS` | то же через CMSIS: `(RCC->CFGR & RCC_CFGR_SWS) == RCC_CFGR_SWS_HSI`, `DBGMCU->IDCODE & DBGMCU_IDCODE_DEV_ID`, `FLASHSIZE_BASE` |
| `HW_SETUP_DONE` | `setup()` завершилась, `g_app.setup_done = 1`, SysTick 1 мс |
| `HW_POST` | `g_post.status = PostOk`, VDDA 2900–3600 мВ, температура −10…+85 °C |
| `HW_BLINK` | между двумя вызовами `board::ledToggle()` светодиод переключился, счётчик +1 |

## Особенности

**Макросы CMSIS в сценариях.** GDB раскрывает макросы (`RCC`, `RCC_CFGR_SWS`, …), если
сборка с `-g3` (Debug, все HIL-пресеты) и текущая точка остановки находится в единице
трансляции, которая включает `stm32f1xx.h`. `main.cpp` его не включает, поэтому
`HW_BOOT_CMSIS` сначала доходит до `board::init()`. Контракт `cmsis_boot_macros` проверяет
наличие макросов в ELF ещё в `prepare.HW_BOOT_CMSIS`, без платы: если макрос пропал (другой
заголовок, сборка без `-g3`), ошибка будет до записи Flash, а не в середине сценария.
Контекст контракта — функция с простым именем из той же единицы трансляции
(`SysTick_Handler`), имена вида `board::init` в контрактах не поддерживаются.

Макрос вроде `DBGMCU` раскрывается в приведение к типу (`(DBGMCU_TypeDef *)…`). Типы, которые
прошивка не использует, GCC в отладочную информацию не пишет, и GDB отвечает `No symbol
"DBGMCU_TypeDef"`. Поэтому HIL-сборка компилируется с `-fno-eliminate-unused-debug-types`
(`cmake/hil.cmake`): растёт только отладочная информация, код тот же. С подмодулем stm32-gdbtest
новее v0.1.0-rc.1 контракт проверяет и тип раскрытия (`whatis`): без этого флага
`prepare.HW_BOOT_CMSIS` сообщит «typed DBGMCU (No symbol "DBGMCU_TypeDef" …)» ещё без платы.

**LTO не используется.** С LTO компилятор встраивает и переставляет функции между
единицами трансляции, создаёт клоны (`[clone .constprop.0]`) и убирает функции без
внешних вызовов. Точки останова тогда ставятся не туда или не ставятся вовсе, порядок
шагов в сценарии перестаёт соответствовать исходному коду. Проекту демонстрации размер
Flash не критичен, поэтому LTO нет ни в одной сборке. Если LTO нужен в рабочей сборке,
делайте отдельную HIL-сборку без него (так устроен проект на STM32G474, описанный в
документации stm32-gdbtest).

**STM32F103C8 со 128 КиБ.** Регистр размера Flash у многих C8 показывает 128 КиБ.
stm32-gdbtest сообщает об этом предупреждением даже при `strict`: DEV_ID совпадает.

**J-Link и F103CB.** Имя устройства J-Link `STM32F103CB` для MCU `STM32F103CBT6` есть в
stm32-gdbtest после v0.1.0-rc.1. С подмодулем на теге v0.1.0-rc.1 J-Link на профиле
`F103CB_PB2` отклоняется («mapping not validated»); используйте ST-Link или обновите
подмодуль до `main`.

**OpenOCD и «неожиданный» IDCODE.** Если OpenOCD сообщает `UNEXPECTED idcode` (обычно это
клон MCU или редкая ревизия), для ручной отладки можно отключить проверку: создайте файл
`target/stm32f1x-anyid.cfg` в каталоге скриптов OpenOCD (`share/openocd/scripts`):

```tcl
set CPUTAPID 0
source [find target/stm32f1x.cfg]
```

и укажите его в `configFiles` конфигурации «Debug (ocd/stlink)». Для HIL-тестов замените
`openocd_target` в локальной копии описания MCU. Клоны MCU проектом не поддерживаются:
проверка DEV_ID при `strict` для них всё равно даст ERROR.

**Python.** Нужен Python ≥ 3.11. CMake ищет его сначала по `PATH`, затем в реестре Windows
(`Python3_FIND_REGISTRY=LAST`), поэтому Python из Visual Studio не мешает. Другой интерпретатор:
`-DPython3_EXECUTABLE=<путь>`; после смены — «Delete Cache and Reconfigure».

**Результаты.** Каталог запуска `build/HIL_<плата>/hwtest/runs/<время>-<ID>-<pid>/`
содержит `result.json`, журналы GDB и сервера, снимок ELF и build manifest.
