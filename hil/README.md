# HIL-тесты stm32-hwtest-bluepill

[English](README.en.md)

Сценарии [stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) проверяют
работающую прошивку на плате: runner на Windows запускает GDB-сервер отладчика, GDB
сбрасывает MCU, останавливается в `main()` и выполняет сценарий на Python. Отчёты — JSON и
JUnit. В прошивку тестовый код не добавляется.

## Состав

```text
hil/
  common/tests/       board/test_*.py, requirements.md, contracts.json
  common/plans/       DDTT
  F103C8/             session.toml, target.toml, board.toml, stands/
  F103CB/             session.toml, target.toml, board.toml, stands/
  templates/          *.example.toml
  tools/              results.py
  api.toml
```

Плата выбирается сборкой: пресеты `f103c8-hil` и `f103cb-hil` задают `BOARD` и
`BLUEPILL_HIL=ON`, `cmake/hil.cmake` подключает stm32-gdbtest `eb085b3` (post-v0.4.1) (`modules/stm32-gdbtest`) с
конфигурацией прогона `hil/<MCU>/session.toml` (`SESSION_CONFIG`) и общими сценариями `hil/common/tests`.
Конфигурация связывает описание MCU, общий `api.toml` и файл данных платы: сценарии читают их
через `t.profile` (`t.profile.data["board"]`, `t.profile.get("user.post.vdda_mv")`), поэтому один
сценарий обслуживает обе платы, а ожидания, зависящие от платы, лежат в данных, а не в коде.
Сценарии используют API закреплённого модуля (API_VERSION=2) и проверяются тестом стиля модуля:
`python modules/stm32-gdbtest/tests/host/test_scenario_style.py hil/common/tests/board/*.py`.

## Стенд

Стенд — локальный файл с отладчиком платы. Скопируйте нужный пример и укажите серийный
номер отладчика (файлы `*.local.toml` не коммитятся):

| Плата | Файл стенда | Пресеты |
| --- | --- | --- |
| Blue Pill (F103C8_PC13) | `hil/F103C8/stands/local.toml` | `f103c8-hil`, `f103c8-hil-host`, `f103c8-hil-hw` |
| BluePill-Plus (F103CB_PB2) | `hil/F103CB/stands/local.toml` | `f103cb-hil`, `f103cb-hil-host`, `f103cb-hil-hw` |

| Отладчик | Пример | Серийный номер |
| --- | --- | --- |
| ST-Link, ST-LINK GDB Server (STM32CubeCLT) | `stlink.example.toml` | `STM32_Programmer_CLI -l st` |
| ST-Link, OpenOCD | `openocd.example.toml` | тот же серийный номер ST-Link |
| J-Link | `jlink.example.toml` | десятичный номер из J-Link Commander |

Проверка окружения без обращения к плате:

```powershell
python -B modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/F103CB/stands/local.toml
```

## Запуск

```powershell
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host     # без платы: трассировка требований и prepare.*
ctest --preset f103cb-hil-hw       # на плате: все hw.* (28 сценариев)
python hil/tools/results.py --runs build/f103cb-hil/hwtest/runs
```

Тестовые пресеты задают политику идентичности `strict`: DEV_ID кристалла должен совпасть с
описанием MCU. Прошивка записывается, только если образ во Flash отличается
(`flash = "if-different"` в стенде). В VS Code те же действия — задачи «HIL: …» (плата
выбирается из списка) и панель «Testing», где каждый сценарий виден как `hw.<ID>` и
`prepare.<ID>`.

| Сценарий | Что проверяет | Приёмы ([техники](https://github.com/ViacheslavMezentsev/stm32-gdbtest/blob/eb085b3e69b775d27085350cb9c6892177b317f4/docs/ru/TESTING_TECHNIQUES.md)) |
| --- | --- | --- |
| `HW_BOOT` | DEV_ID и F_SIZE по адресам из описания MCU, SYSCLK от HSI, `SystemCoreClock` | `t.profile`, `evaluate`, `read` |
| `HW_BOOT_CMSIS` | то же именами CMSIS при входе в `board::init()` | таблица `check(rows)`, контракт, TECH-001 |
| `HW_BOARD_PROFILE` | строка `g_board_name` = имя из файла данных, `BOARD_*` в сборке, таблица векторов, отказ чтения периферии | TECH-017, TECH-018, `memory`, `refused` |
| `HW_GPIO_CONFIG` | вывод светодиода из файла данных: тактирование, режим, `g_led` | ожидания из `profile.data`, TECH-001 |
| `HW_UART_CONFIG` | USART1: тактирование, PA9, делитель BRR для скорости из файла данных, TE/RE, TC | таблица, контракт |
| `HW_SETUP_DONE` | `setup()` завершилась, SysTick 1 мс | `read`, таблица |
| `HW_POST` | `PostOk`, VDDA и температура в пределах из `api.toml`, АЦП выключен | `within`, `profile.get`, `record` |
| `HW_BLINK` | уровень светодиода меняется, счётчик +1, интервал — полупериод | `read` структуры, `within` |
| `HW_TOGGLE_WRITERS` | `g_app.last_toggle_ms` пишут `setup()` и `loop()`, обе из `main()` | `watch`, `frames`, TECH-013 |
| `HW_LED_FORCED_STATE` | `ledToggle()` ставит уровень, обратный ответу `ledIsOn()` | `ret`, `finish`, TECH-004 |
| `HW_POST_VDDA_LOW` | подменённый отсчёт VREFINT даёт VDDA 1638 мВ и `PostVddaOutOfRange`, приложение запускается | `watch`, `write`, TECH-005 |

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

**Точка наблюдения останавливает чуть позже записи.** DWT Cortex-M3 сообщает о записи после
следующей команды. В `loop()` за записью `g_app.last_toggle_ms` сразу идёт вызов
`board::ledToggle()`, поэтому `HW_TOGGLE_WRITERS` может остановиться на входе в `ledToggle()`;
сценарий тогда считает писателем вызывающую функцию.

**Строка из массива без размера.** В единицах трансляции, которые видят только объявление
`extern const char g_board_name[]`, у массива нет размера, и GDB может взять именно этот тип.
`HW_BOARD_PROFILE` поэтому читает строку через указатель: `(const char *)g_board_name`.

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

**Результаты.** Каталог запуска `build/<mcu>-hil/hwtest/runs/<время>-<ID>-<pid>/`
содержит `result.json`, журналы GDB и сервера, снимок ELF и build manifest.

## Разработка через DDTT

[План](common/plans/ddtt-feedback.md) и [результат цикла](common/plans/ddtt-feedback-results.md):
сначала сценарий выявляет дефект на исходной прошивке, затем проверяет исправление и регрессию.
Навык — `.claude/skills/stm32-gdbtest-develop/SKILL.md`; его опытная копия сопровождает эту ветку,
Подмодуль закреплён на eb085b3 (main после v0.4.1). Старые локальные копии навыков относятся к 0.4.0; актуальные инструкции — в modules/stm32-gdbtest/skills.
В отличие от stand-loop, разработке нужен checkout исходников и компилятор, а не только ZIP.
Профили используют target schema 2 с `[openocd]`; сессии включают `[results] capture = true`.

Новый сценарий: `HW_POST_ADC_CLEANUP` (`tests/board/test_ddtt_feedback.py`).


[Окружение разработчика](../docs/DEVELOPER_ENVIRONMENT.md).

Новые сценарии: `HW_STARTUP_ORDER`, `HW_SYSTICK_PROGRESS`, `HW_ADC_INITIALIZATION`.
Карта WeAct PB2 и объяснения: [DDTT_STARTUP](../docs/DDTT_STARTUP.md).

[ADC/DMA, фильтрация и HTML DDTT / processing and evidence report](../docs/ADC_DMA.md).

Индикация: HW_INDICATOR_NORMAL, HW_INDICATOR_INVALID, HW_INDICATOR_RANGE. [Описание и темы отчёта](../docs/MEASUREMENT_LED.md).

[KEY, виртуальные нажатия и актуальный экспорт DDTT](../docs/BUTTON.md).

[Ошибка DMA и восстановление](../docs/DMA_ERROR.md).

[Таймауты POST](../docs/POST_TIMEOUT.md).

[Переносимая раскраска исходников для Pages (пока локально)](../docs/DDTT_PAGES.md).
