---
name: stm32-gdbtest-integrate
description: Подключение stm32-gdbtest к существующему проекту прошивки STM32 (CMake + Ninja) — Git-подмодуль, каталог hil/ с описанием MCU, session.toml и api.toml, вызов stm32_gdbtest_attach, пресеты CTest host/hw, файл стенда, первый сценарий и первый прогон. Используй, когда просят «подключить stm32-gdbtest», «добавить HIL/DDTT-тесты в проект», «настроить аппаратные тесты через GDB», «обновить версию модуля у потребителя», «перевести hwtest-проект на 0.4.0»; по-английски — integrate stm32-gdbtest, add hardware-in-the-loop tests, attach the module to a firmware project, bump the submodule.
---

# Подключение stm32-gdbtest к проекту прошивки

stm32-gdbtest проверяет работающую прошивку на настоящей плате: Python-сценарии управляют GDB
через SWD-отладчик, тестового кода в прошивке нет (метод DDTT). Модуль подключается Git-подмодулем
с закреплённым коммитом; сценарии, описание MCU и стенды живут в проекте потребителя, модуль ради
проекта не меняется.

Пути ниже — от корня модуля (`modules/stm32-gdbtest/` в проекте потребителя). Подробности:
[начало работы](../../docs/ru/GETTING_STARTED.md), [API и конфигурация](../../docs/ru/API.md),
[identity и Flash](../../docs/ru/TARGET_IDENTITY.md), [GDB-серверы](../../docs/ru/BACKENDS.md),
[памятка](../../docs/ru/HOWTO.md). Сценарии — навык `stm32-gdbtest-scenarios`, запуски и разбор
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

Выбери согласованный тег/коммит: опубликован v0.4.0. Проверь тег в репозитории и закрепи gitlink.
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
профиль `at32f403a` ([совместимые МК](../../docs/ru/COMPATIBLE_MCU.md)).

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

Для 0.4.0 используй target schema 2 из актуального профиля, включая backend-specific
команды reset/setup; не переноси monitor-команды OpenOCD в st-util или ST-LINK GDB Server.
[Страницы backend](../../docs/ru/BACKENDS.md) описывают различия и установку st-util на Ubuntu 20.04.
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
`interface = "JTAG"` ([GDB-серверы](../../docs/ru/BACKENDS.md)). `flash = "if-different"` пишет Flash только при отличии образа,
`verify-only` — только сверяет. Удалённый стенд — таблица `[remote]` с SSH-ключом; пароли не
поддерживаются ([Linux-стенд](../../docs/ru/LINUX_STAND.md)).

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

## Перевод старого потребителя на 0.4.0

На опубликованной 0.3.0 проекты с `t.value`, `t.fields`, `t.set_value`, `t.force_return`
получают предупреждения `deprecated`. В 0.4.0 эти четыре метода удалены;
`config`/`config_props`/`settings`/`sources` ранее заменены `t.profile`. Порядок:
поднять gitlink до выбранного опубликованного тега, добавить `session.toml`/`api.toml`, если нужны
лимиты и параметры, переписать сценарии по таблице миграции из [API](../../docs/ru/API.md) и навыку
`stm32-gdbtest-scenarios`, прогнать host и hw.
