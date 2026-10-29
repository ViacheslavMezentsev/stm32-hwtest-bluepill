---
name: stm32-gdbtest-integrate
description: Подключение stm32-gdbtest к существующему проекту прошивки STM32 (CMake + Ninja) — Git-подмодуль, каталог hil/ с описанием MCU, session.toml и api.toml, вызов stm32_gdbtest_attach, пресеты CTest host/hw, файл стенда, первый сценарий и первый прогон. Используй, когда просят «подключить stm32-gdbtest», «добавить HIL/DDTT-тесты в проект», «настроить аппаратные тесты через GDB», «обновить версию модуля у потребителя», «перевести hwtest-проект на API 3»; по-английски — integrate stm32-gdbtest, add hardware-in-the-loop tests, attach the module to a firmware project, bump the submodule.
license: MIT
compatibility: stm32-gdbtest 0.6.x (API_VERSION 3); Python 3.11+, GDB с Python 3.11+ (arm-none-eabi-gdb-py3), CMake 3.25+ и Ninja; проект прошивки STM32 или совместимого Cortex-M на CMake
metadata:
  author: Viacheslav Mezentsev
  version: "0.6.1"
  module: stm32-gdbtest
  api_version: "3"
---

# Подключение stm32-gdbtest к проекту прошивки

stm32-gdbtest проверяет работающую прошивку на настоящей плате: Python-сценарии управляют GDB
через SWD-отладчик, тестового кода в прошивке нет (метод DDTT). Модуль подключается Git-подмодулем
с закреплённым коммитом; сценарии, описание MCU и стенды живут в проекте потребителя, модуль ради
проекта не меняется.

Пути ниже — от корня модуля (`modules/stm32-gdbtest/` в проекте потребителя). Подробности:
[начало работы](../../docs/ru/GETTING_STARTED.md), [API и конфигурация](../../docs/ru/API.md),
[identity и Flash](../../docs/ru/TARGET_IDENTITY.md), [GDB-серверы](../../docs/guides/ru/BACKENDS.md),
[памятка](../../docs/guides/ru/HOWTO.md). Сценарии — навык `stm32-gdbtest-scenarios`, запуски и разбор
отчётов — `stm32-gdbtest-run`.

## Что выяснить до начала

Не угадывай — спроси владельца, если этого нет в проекте:

- MCU с точным суффиксом (`STM32F411CEU6`), плата, вывод светодиода или другой наблюдаемый признак;
- отладчик и GDB-сервер: ST-Link + OpenOCD, ST-Link + ST-LINK GDB Server (CubeCLT) или J-Link, либо ST-Link + st-util;
- схема стенда: отладчик у рабочего компьютера, на Linux-стенде, или runner на Windows/WSL
  с сервером на Linux-стенде по SSH;
- toolchain: ARM GCC с `arm-none-eabi-gdb-py3` (GDB с Python ≥ 3.11), CMake ≥ 3.25, Ninja, Python ≥ 3.11;
- можно ли перезаписывать Flash платы и какой образ восстановить после опытов.

## Шаги

### 1. Подмодуль и версия

```powershell
git submodule add https://github.com/ViacheslavMezentsev/stm32-gdbtest.git modules/stm32-gdbtest
git -C modules/stm32-gdbtest checkout <agreed-tag-or-commit>
git add .gitmodules modules/stm32-gdbtest
```

Выбери согласованный тег/коммит и закрепи gitlink. Для линий 0.5.x и 0.6.x проверяй API_VERSION=3;
не выдавай рабочую ветку за опубликованный выпуск.
Gitlink фиксирует проверенный коммит; configure его не обновляет. Обновление версии — отдельный
коммит: новый gitlink, чтение раздела CHANGELOG модуля (миграция), прогон host и hw.

### 2. Каталог hil/

Так устроены проекты-потребители (hwtest-проекты, `examples/minimal-consumer`):

```text
hil/
  session.toml            [config] target/api, [data] — файлы данных проекта
  api.toml                лимиты API и параметры сценариев ([user.*])
  profiles/<board>.toml   описание MCU (target.toml); один файл на вариант MCU
  tests/requirements.md   требования HW_* — заголовок ## <ID> и наблюдаемый критерий
  tests/contracts.json    контракты: макросы и символы, которые сценарий берёт из ELF
  tests/board/test_*.py   сценарии
  stands/*.example.toml   шаблоны стендов без серийных номеров
```

В `.gitignore` проекта — `*.local.toml`, `*.remote.toml` и `build/`. Стенды с серийными номерами не коммитятся.

Компактный вариант равноправен: `hil/common/tests`, `hil/<MCU>/session.toml`,
`target.toml`, `board.toml`, `stands/` и общие `hil/api.toml`, `hil/templates/`.
В CMake укажи PROFILE_DIR=hil/common, SESSION_CONFIG=hil/<MCU>/session.toml.
Не выводи пути из имени каталога: проверь их через [inspect](../../docs/ru/HIL_INSPECT.md).

### 3. Описание MCU

Начни с ближайшего профиля модуля (`tests/firmware/profiles/<f030r8|f103c8|f401cc|f411ce|f429zi>/target.toml`)
или `examples/minimal-consumer/profile/target.toml` и сверь каждое поле с Reference Manual:

| Поле | Откуда |
| --- | --- |
| `flash_start`, `flash_size` | карта памяти, объём Flash заказанного кристалла |
| `flash_size_address` | регистр Flash size (F0 `0x1FFFF7CC`, F1 `0x1FFFF7E0`, F4 `0x1FFF7A22`) |
| `[identity]` | DBGMCU_IDCODE (`0xE0042000`; на F0 `0x40015800`), маска `0xFFF`, DEV_ID из RM; у совместимых МК — идентификатор производителя любой ширины (AT32F403A: PID, маска `0xFFFFFFFF`) |
| `breakpoint_limit` | число компараторов FPB: Cortex-M0 — 4, M3/M4 — 6 |
| `fault_handlers` | M0 — только `HardFault_Handler`; M3/M4 — ещё MemManage, BusFault, UsageFault |
| `[diagnostic_registers]` | M3/M4 — CFSR/HFSR; у M0 их нет (CPUID, ICSR, SCR) |
| `openocd_target` | `target/stm32f0x.cfg`, `stm32f1x.cfg`, `stm32f4x.cfg` и т. п. |
| `jlink_device` | имя устройства J-Link, если МК нет в таблице проверенных STM32 (например, `AT32F403ACGU7`) |

Точки fault handlers занимают слоты `breakpoint_limit` — сценарию остаётся меньше. Cortex-M-совместимый МК
другого производителя (Artery AT32, GD32, APM32) подключается своим профилем и CMSIS производителя; образец —
профиль `at32f403a` ([совместимые МК](../../docs/guides/ru/COMPATIBLE_MCU.md)).

### 4. Конфигурация сессии

```toml
# hil/session.toml — относительные пути от его каталога
[config]
target = "profiles/f411ce.toml"
api = "api.toml"

# Файлы данных проекта: t.profile.data["board"]
[data]
board = "board.toml"
```

`api.toml` (`schema = 1`) хранит лимиты (`[frames] limit`, `[execute] output_limit_chars`,
`[records] max_records`) и параметры сценариев (`[user.measurement] count = 5` →
`t.profile.get("user.measurement.count")`). Таблица значений и максимумов — [API](../../docs/ru/API.md).
Несколько вариантов MCU — по `session.toml` на вариант или параметр `PROFILE` (не вместе с `SESSION_CONFIG`).

Для аппаратной цели допустимы schema 1/2 и schema 3 с environment="hardware".
Для Renode/QEMU нужна schema 3 с environment="emulator" и architecture="cortex-m".
Бери профиль соответствующего backend из текущего примера, включая backend-specific
команды reset/setup; не переноси monitor-команды OpenOCD в st-util или ST-LINK GDB Server.
[Страницы backend](../../docs/guides/ru/BACKENDS.md) описывают различия и установку st-util на Ubuntu 20.04.
Если нужны записи после запуска, добавь в session.toml:

```toml
[results]
capture = true
```

Выдели отдельные выходные каталоги для попыток и обработки; результаты не храни поверх входов.
`record` сохраняет произвольные данные, не обязательно измерения. План анализа —
[stm32-gdbtest-results](../stm32-gdbtest-results/SKILL.md).

### 5. CMake

Подключение выключено по умолчанию и включается пресетом:

```cmake
option(MYPROJ_HIL "Hardware tests via stm32-gdbtest" OFF)
if(MYPROJ_HIL)
    set(STM32_GDBTEST_SOURCE_DIR "${CMAKE_SOURCE_DIR}/modules/stm32-gdbtest" CACHE PATH "stm32-gdbtest checkout")
    if(NOT EXISTS "${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
        message(FATAL_ERROR "stm32-gdbtest not found, run: git submodule update --init")
    endif()
    # CMSIS types the firmware does not use are kept for scenario expressions (DBGMCU->IDCODE).
    target_compile_options(${PROJECT_NAME} PRIVATE -fno-eliminate-unused-debug-types)
    include(CTest)
    include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
    stm32_gdbtest_attach(${PROJECT_NAME}
        PROFILE_DIR "${CMAKE_SOURCE_DIR}/hil"
        SESSION_CONFIG "${CMAKE_SOURCE_DIR}/hil/session.toml"
        MANIFEST_INPUTS "${CMAKE_SOURCE_DIR}/ld/firmware.ld" "${CMAKE_SOURCE_DIR}/CMakeLists.txt")
endif()
```

- Вызов — после создания firmware target; один target верхнего каталога, генератор Ninja,
  каталог сборки внутри проекта.
- Debug с `-g3`: GDB раскрывает макросы CMSIS/HAL только с ним.
- Сценариям с навигацией по вызовам и `ret` нужна сборка без LTO (`-fno-lto` после `-flto`).
- `TEST_DIRS` добавляет каталоги общих сценариев (`board/` и `requirements.md` в каждом).
- `MANIFEST_INPUTS` — файлы, от которых зависит образ (linker script, toolchain-файл): они попадают
  в build manifest.

### 6. Пресеты CTest

`stm32_gdbtest_attach` создаёт для каждого сценария `prepare.<ID>` (метка `host`, без платы) и
`hw.<ID>` (метка `hw`). Тестовые пресеты:

```json
{ "name": "HIL_F411CE-host", "configurePreset": "HIL_F411CE",
  "filter": { "include": { "label": "^host$" } }, "execution": { "noTestsAction": "error", "jobs": 1 } },
{ "name": "HIL_F411CE-hw", "configurePreset": "HIL_F411CE",
  "environment": { "STM32_GDBTEST_STAND": "${sourceDir}/hil/stands/f411ce.local.toml",
                   "STM32_GDBTEST_IDENTITY_POLICY": "strict" },
  "filter": { "include": { "label": "^hw$" } }, "execution": { "noTestsAction": "error", "jobs": 1 } }
```

`strict` требует совпадения DEV_ID кристалла с описанием MCU. Старые переменные `HWTEST_*`
отвергаются: только `STM32_GDBTEST_*`.

### 7. Стенд

Шаблоны — `tests/firmware/stands/{openocd,stlink,jlink,st-util,remote}.example.toml`. Владелец копирует
шаблон в `hil/stands/<board>-<backend>.local.toml` (удалённый стенд из `remote.example.toml` —
`hil/stands/<board>-<backend>.remote.toml`) и вписывает серийный номер; агент серийные номера в
коммиты и документы не переносит. Другой зонд для OpenOCD — ключи `interface` и `transport`, J-Link по JTAG —
`interface = "JTAG"` ([GDB-серверы](../../docs/guides/ru/BACKENDS.md)). `flash = "if-different"` пишет Flash только при отличии образа,
`verify-only` — только сверяет. Удалённый стенд — таблица `[remote]` с SSH-ключом; пароли не
поддерживаются ([Linux-стенд](../../docs/guides/ru/LINUX_STAND.md)).

### 8. Первый сценарий

Один сценарий-«дым»: остановка в функции приложения и проверка состояния, которое следует из кода.
Требование — в `tests/requirements.md` под тем же ID. Образец —
`examples/minimal-consumer/profile/tests/board/test_blink.py`; правила — навык `stm32-gdbtest-scenarios`.

### 9. Проверка без платы, затем на плате

```powershell
cmake --preset HIL_F411CE
cmake --build --preset HIL_F411CE
ctest --preset HIL_F411CE-host
python -B modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/stands/f411ce.local.toml
ctest --preset HIL_F411CE-hw -R HW_BOOT
```

`host` проверяет трассировку требований и подготовку (`run --prepare-only`: ELF, manifest,
контракты, образ) без отладчика. Аппаратный запуск — только с согласия владельца: он записывает Flash.

## Готово, когда

- gitlink указывает на тег или проверенный коммит, `git submodule update --init` восстанавливает модуль;
- `ctest --preset <…>-host` зелёный, у каждого `@case` есть требование;
- `doctor` со стендом без FAIL, один `hw.<ID>` дал PASS, `result.json` прочитан;
- в коммите нет `*.local.toml`, `*.remote.toml`, серийных номеров, ELF и каталогов `build/`;
- README проекта называет пресеты, файл стенда и версию модуля.

## Миграция прежних сценариев

На опубликованной 0.3.0 проекты с `t.value`, `t.fields`, `t.set_value`, `t.force_return`
получают предупреждения `deprecated`. В 0.4.0 эти четыре метода удалены;
`config`/`config_props`/`settings`/`sources` ранее заменены `t.profile`. Порядок:
поднять gitlink до выбранного опубликованного тега, добавить `session.toml`/`api.toml`, если нужны
лимиты и параметры, переписать сценарии по [руководству миграции](../../docs/ru/MIGRATION_050.md) и навыку
`stm32-gdbtest-scenarios`, прогнать host и hw.


## Перед первым запуском API 3

Из корня потребителя (подставь выбранный профиль):

```sh
python modules/stm32-gdbtest/stm32_gdbtest/cli.py inspect --config hil/F103CB/session.toml --profile-dir hil/common --project-root .
```

Затем проверь созданный CMake `session.json` через inspect --session и prepare.
inspect не запускает инструменты и не проверяет тело сценария. WARN без выбранного
стенда допустим для проверки структуры; перед run выбери стенд явно.
Для MMIO добавь `[mmio] svd="device.svd"` в session.toml: путь от этого файла,
описание захватывается в пакет. Получатель должен поддерживать капсулу schema 2.
Без MMIO SVD не обязателен. Читай [SVD](../../docs/ru/SVD.md).
Для эмулятора используй [Renode](../../docs/guides/ru/RENODE.md) или [QEMU](../../docs/guides/ru/QEMU.md):
новый собственный процесс на сценарий, без keep/attach/SSH и аппаратной identity.
Синхронные def сохраняются; async-помощники и скрытые вызовы функций мигрируются
по [контракту API 3](../../docs/ru/LIVE_EXECUTION.md). prepare не доказывает эту миграцию.

## Возможности 0.6.0

- Переход с 0.5.x: API_VERSION остаётся 3, новое включается явно ([переход к 0.6.0](../../docs/ru/VERSIONING.md#переход-к-060)).
- При смене версии модуля прогоняй все шаги CI потребителя, а не только `ctest --preset …-host`: отдельные unittest, проверки стиля сценариев, сборку на Linux. Копии `tools/` модуля (например, `ddtt_coverage.py`) в 0.6.0 требуют рядом пакет `stm32_gdbtest`.
- Копии навыков в `.claude/skills/` обновляй вместе с gitlink, включая каталоги `references/`.
- Для пошагового прохода сценария добавь задачу VS Code с `run --interactive` и расширение `ms-python.debugpy` ([ручная отладка](../../docs/ru/MANUAL_DEBUG.md)); образцы — BluePill и BlackPill, `hil/tools/debug_scenario.py`.
