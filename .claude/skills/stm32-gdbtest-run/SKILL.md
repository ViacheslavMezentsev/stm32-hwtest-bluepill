---
name: stm32-gdbtest-run
description: Запуск сценариев stm32-gdbtest и разбор результатов — doctor, prepare-only, CTest host/hw, один сценарий через CLI, удалённый GDB-сервер по SSH, пакет подготовленного запуска (pack/run --package), аппаратный CI, чтение result.json и журналов при FAIL/ERROR, уборка после аварии. Используй, когда просят «прогнать тесты на плате», «запустить сценарий», «почему ERROR/FAIL», «GDB server startup timed out», «отладчик занят», «собрать пакет для стенда», «запустить на Orange Pi/Linux-стенде»; по-английски — run stm32-gdbtest scenarios, debug a failed hardware run, prepared run package, remote GDB server.
---

# Запуск сценариев и разбор результатов

Пути — от корня модуля (`modules/stm32-gdbtest/` у потребителя); CLI из любого каталога —
`python -B <модуль>/stm32_gdbtest/cli.py`, из корня модуля — `python -B -m stm32_gdbtest`.
Подробности: [проверки и CI](../../docs/ru/testing.md), [памятка](../../docs/ru/HOWTO.md),
[Linux-стенд](../../docs/ru/LINUX_STAND.md), [аппаратный CI](../../docs/ru/HARDWARE_CI.md),
[владение отладчиком](../../docs/ru/DEBUGGER_OWNERSHIP.md).

## Правила для агента

- Аппаратный запуск записывает Flash, если образ отличается: только на плате, согласованной с
  владельцем для опытов. Стенд, прошивку отладчика и настройки защиты Flash не менять.
- Один отладчик — один запуск: не запускать параллельно с CTest, другим терминалом или другим проектом.
- Серийные номера, адреса и пути стендов не переносить в коммиты, документы и ответы для публикации.
- Для SSH — только ключи; пароли в стенде отвергаются.
- Ожидания не подгонять под наблюдённый результат: FAIL — повод проверить требование и прошивку.

## Лестница запуска

От дешёвого к дорогому; следующая ступень — только после зелёной предыдущей.

| Ступень | Команда | Что доказывает |
| --- | --- | --- |
| 1. Окружение | `cli.py doctor --stand <стенд>` | GDB-Python, binutils, сервер, USB, каталог блокировок; без платы |
| 2. Host | `ctest --preset <…>-host` | трассировка требований, `prepare.<ID>`: ELF, manifest, контракты, образ |
| 3. Один сценарий | `cli.py run --session <build>/hwtest/session.json --test HW_X --stand <стенд>` | сценарий на плате |
| 4. Набор | `ctest --preset <…>-hw` | все `hw.*` последовательно (`RESOURCE_LOCK stm32_swd`) |

`--prepare-only` у `run` выполняет ступень 2 для одного сценария со стендом — без обращения к
отладчику. Политика идентичности: `--identity-policy strict` или `STM32_GDBTEST_IDENTITY_POLICY=strict`
(DEV_ID обязан совпасть), по умолчанию `warn`. Стенд: `--stand` или `STM32_GDBTEST_STAND`.

## Схемы стенда

Сценарии от схемы не зависят, её задаёт файл стенда:

| Схема | Стенд | Где GDB и runner |
| --- | --- | --- |
| Отладчик у рабочего компьютера | `[probe]` | там же |
| Linux-стенд, всё на нём | `[probe]`, окружение `tools/linux_stand.py` (`. ~/.local/stm32-gdbtest/env.sh`) | на стенде |
| Runner на Windows/WSL2, сервер на Linux-стенде | `[probe]` + `[remote]` (host, user, identity_file) | у разработчика; сервер по SSH |
| Пакет подготовленного запуска | `[probe]` на стенде | сборка и подготовка — в другом месте |
| Аппаратный CI | стенды раннера `~/.config/stm32-gdbtest/stands/` | self-hosted раннер |

Пакет: `cli.py pack --session <…>/session.json --output build/packages/<имя>.zip [--test ID] [--include helpers]`,
на стенде — `cli.py run --package <имя>.zip --test HW_X --stand <стенд>`. SHA-256 каждого файла
проверяется, пересборки на стенде нет.

## Результат

Итоговая строка `run`: `<СТАТУС> <ID>: <каталог>/result.json`. Коды: PASS 0, FAIL 1, ERROR 2.
Каталог запуска — `<build>/hwtest/runs/<время>-<ID>-<pid>/`:

| Файл | Зачем читать |
| --- | --- |
| `result.json` | `status`, `checks` (имя, фактическое, ожидаемое), `stops`, `mutations`, `evaluations`, `warnings`, `profile`, `error` |
| `junit.xml` | для CI и панели Testing |
| `gdb.log` | команды и ответы GDB, Python-трассировка сценария |
| `server.log` | запуск GDB-сервера: serial, USB, занятость отладчика |
| `recovery.log` | восстановление после таймаута или аварии |
| `tunnel.log` | только удалённый стенд: SSH |

**FAIL** — проверка не сошлась: сравнить `actual` и `expected` в `checks`, проверить место
остановки (`stops`), требование и прошивку. **ERROR** — сценарий не выполнился: причина в
`result.json` (`error`), затем `gdb.log`; ошибка подготовки (контракт, manifest, образ) видна уже на
ступени 2. Ожидаемый отказ остаётся ERROR и PASS не становится.

## Частые отказы

| Сообщение | Действие |
| --- | --- |
| `Debugger already owned by another runner` | дождаться другого запуска; параллельно не запускать |
| `Abandoned debugger ownership` | найти и остановить оставшиеся серверы (`pgrep -a openocd; pgrep -a JLink` / `Get-Process openocd, JLinkGDBServerCL, ST-LINK_gdbserver`), повторить |
| `GDB server exited before ready; see server.log` | неверный serial, отладчик занят другой программой, нет доступа к USB (udev) |
| `GDB server startup timed out` | `server.log`; медленному отладчику — `startup_timeout_s` в стенде |
| `Flash capacity differs … image fits both` | предупреждение: кристалл с большей Flash, чем в профиле; запуск продолжается |
| `Stand host refused the run: busy/abandoned/port/executable` | на хосте стенда: занят, остатки процессов, диапазон 61000–64999 занят, нет сервера в `PATH`/`env.sh` |
| `Permission denied (publickey)`, `Host key verification failed` | ключ не в `authorized_keys`; один раз `ssh <user>@<host> exit`, при смене ключа хоста — `ssh-keygen -R` |
| `Rename legacy environment variables to STM32_GDBTEST_` | `HWTEST_*` → `STM32_GDBTEST_*` |
| `No module named 'tomllib'` на Linux-стенде | не подключён `env.sh`: системный Python ниже 3.11 |
| `reach` ждёт до таймаута | функция встроена (LTO) или уже выполнена; сборка без LTO, другое место остановки |
| Макрос не найден | остановка вне единицы трансляции с заголовком устройства или сборка без `-g3` |

Полный список — [памятка](../../docs/ru/HOWTO.md).

## Отчёт владельцу

Коммит модуля и проекта, MCU и стенд (без серийного номера), схема, версия GDB, команда, итог
(PASS/FAIL/ERROR по сценариям), для не-PASS — проверка, фактическое и ожидаемое значение и вывод.
Что изменилось на плате (записанный образ, инъекции) и как восстановлено.
