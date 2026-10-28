# Окружение разработчика

[English](DEVELOPER_ENVIRONMENT.en.md) · [HIL](../hil/README.md)

Проект собирается собственным CMake и CMSIS, без stm32-cmake-yml. Код прошивки и сценарии
при реорганизации не изменены. BOARD выбирает F103C8_PC13 или F103CB_PB2.

## Профили и инструменты

| Пресеты | Назначение |
| --- | --- |
| f103c8-debug / f103cb-debug | Debug, Renode и ручная отладка |
| f103c8-release / f103cb-release | Release, без HIL и эмуляции |
| f103c8-hil / f103cb-hil | Debug с CMSIS debug types, host/prepare и отдельным HW |

Старые имена Debug_*, Release_* и HIL_* удалены. Старые build-каталоги и результаты сохранены,
но новые задачи их не используют. Без пресета BOARD по-прежнему F103C8_PC13.

CMake >= 3.25, Ninja, Python >= 3.11. ARM_TOOLCHAIN_ROOT задаётся параметром CMake или
переменной окружения. Затем ищется xPack 14.2.1-1.1 в USERPROFILE (Windows) или HOME (Linux),
иначе инструменты берутся из PATH. После изменения toolchain используйте новую папку сборки
или CMake: Delete Cache and Reconfigure. Не указывайте компилятор MSVC.
Renode 1.17.0: RENODE_BINARY, CMake RENODE_EXECUTABLE или PATH/ProgramFiles.

## Визуальная работа в VS Code

1. Откройте папку проекта. Установите рекомендации из .vscode/extensions.json: CMake Tools,
   Microsoft C/C++, Cortex-Debug, Python (Pylance и debugpy). clangd не требуется.
   Pylance находит `stm32_gdbtest` в подмодуле по `python.analysis.extraPaths`; модуль `gdb`
   существует только внутри GDB, поэтому предупреждение об отсутствии его исходника отключено.
2. Через CMake: Select Configure Preset выберите, например, f103cb-debug, выполните Configure.
   Затем выберите одноимённый Build Preset и Build. Окружение Visual Studio отключено настройкой
   cmake.useVsDeveloperEnvironment=never.
3. Откройте исходник выбранного профиля. IntelliSense получает параметры от CMake Tools;
   compile_commands.json активной сборки копируется в build/compile_commands.json.
   Условия другого BOARD могут оставаться неактивными — это ожидаемо.
4. Tasks: Run Task: фильтры «Сборка:», «Проверка:», «Эмуляция:», «Прошивка:», «HIL:».
   HIL-задачи явно именуют плату; сборка и тест не могут случайно выбрать разные платы в двух диалогах.
5. В Testing обновите список после смены пресета. Старые зелёные значки не доказывают новый прогон.
   Запускайте выбранный набор заново. Обычный HIL test preset включает только host;
   аппаратные тесты выбираются отдельным *-hw. Запуск отдельного hw.* из дерева Testing — это
   явный аппаратный запуск, фильтр пресета не следует считать блокировкой доступа к плате.
6. Ручная отладка: выберите конфигурацию «Плата: OpenOCD / ST-Link». Настройки device,
   svdFile, toolchain независимы от пресета: сверьте MCU и ELF. Для C8 задайте STM32F103C8,
   для CB — STM32F103CB. SVD необязателен. Если расширение не разворачивает вложенный config-путь,
   задайте gdbPath явно. На Linux замените USERPROFILE на HOME в пользовательском toolchain.
   Несколько отладчиков требуют явного выбора serial в собственной конфигурации OpenOCD;
   ручная отладка не использует автоматически HIL stand и его блокировку.
7. Пошаговый проход сценария: поставьте точку останова в `hil/common/tests/board/*.py`, запустите
   задачу «HIL: F103C8 — пошаговый проход сценария (VS Code)…» и выберите сценарий, затем F5 —
   «Сценарий: подключиться (debugpy)». Работают шаги, Variables и Debug Console (`t.read(...)`),
   ограничения по времени нет, Ctrl+C отменяет запуск. Итог пишется в
   `build/<пресет>/hwtest/interactive-runs`, отдельно от автоматических прогонов; сценарий и его
   `timeout_s` не меняются. Нужно расширение `ms-python.debugpy`. С модулем 0.5.x запуск ограничен
   300 с, итог — в `manual-runs`. Подробно — [пошаговый проход сценария](https://github.com/ViacheslavMezentsev/stm32-gdbtest/blob/main/docs/ru/MANUAL_DEBUG.md).

## Терминал, без платы

```powershell
cmake --preset f103cb-debug
cmake --build --preset f103cb-debug
ctest --preset f103cb-debug-emulator
cmake --build --preset f103cb-debug --target emulate
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host
```

Для C8 замените f103cb на f103c8. Цель emulate выводит UART и итог дымовой проверки.
Логи находятся в build/<preset>/renode. Модель не моделирует ADC: POST FAIL в UART ожидаем,
критерии smoke — загрузка, завершение setup и мигание. QEMU для этой платы не добавлялся.

## Отладка в Renode

Выберите debug-пресет и конфигурацию «Эмуляция: Renode (GDB)», затем F5.
Предварительная задача собирает ELF и запускает Renode на порту 3334; Cortex-Debug подключается
к уже загруженному ELF, остановка — main. Лог UART: build/<preset>/renode-debug/uart.log.
После Disconnect сервер может остаться в терминале: введите quit в Renode или завершите именно
задачу Renode перед повторным F5. Не запускайте второй сервер на том же порту.
Проверка интерфейса F5/брейкпоинтов выполняется разработчиком отдельно от терминального smoke.

## HIL

```text
hil/
  common/tests/          сценарии, requirements.md, contracts.json
  common/plans/          сохранённые планы и отчёты DDTT
  F103C8/                session.toml, target.toml, board.toml
  F103CB/                session.toml, target.toml, board.toml
    stands/              local.toml, remote.toml (Git ignore)
  templates/             примеры серверов отладки
  tools/                 просмотр результатов
  api.toml               общие параметры сценариев
```

Оба профиля используют common/tests без копирования Python-кода. Стенд берите из templates;
для ST-Link HIL используйте OpenOCD. Старые локальные конфигурации сохранены в stands нужной платы.
Для F103CB выбран ранее использовавшийся OpenOCD; конфигурацию F103C8 обязательно сверьте с
фактическим подключением перед запуском — её сохранение не является проверкой оборудования.

```powershell
python modules/stm32-gdbtest/stm32_gdbtest/cli.py doctor --stand hil/F103CB/stands/local.toml
ctest --preset f103cb-hil-hw
# После подготовки remote.toml с SSH:
ctest --preset f103cb-hil-hw-remote
python hil/tools/results.py --runs build/f103cb-hil/hwtest/runs
```

Doctor не заменяет тест платы. HW выполняется последовательно, identity policy strict.
Результаты каждой попытки — отдельные каталоги runs; захват records включён.
Подмодуль сохранён на v0.4.1. Сценарии новых функций и карта DDTT — следующий этап.

## CI и приёмка

GitHub CI использует те же шесть пресетов, GCC 14.2.1, host/prepare для HIL и Renode 1.17.0
для Debug. Linux-архив Renode закреплён SHA-256, имя файла без старого суффикса -dotnet.
Аппаратные проверки в CI не запускаются. Установка зависимостей GitHub требует сети.
Форматирование src остаётся отдельным существующим заданием; пользовательский .clang-format
в этом изменении не редактируется. При публикации нового набора правил потребуется согласовать
версию clang-format в CI с ним; локальная версия 23.1.3 отличается от Ubuntu clang-format.

До аппаратного этапа: обе Debug/Release/HIL сборки, два host-набора, два Renode smoke.
Вручную в VS Code: смена профиля/IntelliSense, обновление Testing, F5 на Renode и повторный запуск.
Проверки физической платы и удалённого стенда выполняются после сверки подключения.

## Результаты переноса (15.10.2026)

Windows: 6/6 configure/build; два host-набора по 13/13; два Renode smoke PASS.
Linux в stm32-universal-builder (Docker volume): та же матрица, все 16 команд успешны.
Renode 1.17 + GDB: первоначальный main и повторный main после Reset подтверждены.
Reset-макрос повторно загружает ELF и задаёт VectorTableOffset; исходный неудачный опыт сохранён.
GDB выдал предупреждения кодировки CP1252 и выбора SP alias; обе остановки достигнуты, exit 0.
Цель emulate выводит UART и проходит smoke. Исходники, CMSIS, linker script, подмодуль и код
Python-сценариев сверены на неизменность. Сетевую установку GitHub CI и UI VS Code эти проверки
не заменяют. Аппаратных запусков на этом этапе нет.

Раскраска DDTT и новая серия инициализации: [DDTT_STARTUP](DDTT_STARTUP.md).

Удержание KEY имеет приоритет над индикацией измерений. Поведение кнопки и единая задача экспорта DDTT: [BUTTON](BUTTON.md).
