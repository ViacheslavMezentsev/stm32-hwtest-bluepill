# Раскраска запуска WeAct BluePill-Plus

[English](DDTT_STARTUP.en.md) · [Окружение](DEVELOPER_ENVIRONMENT.md)

Профиль F103CB_PB2, светодиод PB2 active high. Карта —
[hil/ddtt-f103cb.template.json](../hil/ddtt-f103cb.template.json), сценарии —
[test_startup.py](../hil/common/tests/board/test_startup.py). Карта не предназначена для PC13:
универсальные сценарии поддерживают C8, но привязки GPIOB относятся к WeAct.

## Что добавили

| Сценарий | Ожидание и смысл |
| --- | --- |
| HW_STARTUP_ORDER | Вход main с нулевым состоянием; setup вызван из main, board init и POST из setup. GPIO и SysTick готовы до UART, UART — до POST; loop начинается после публикации setup_done. |
| HW_SYSTICK_PROGRESS | Два соседних входа ISR, исключение 15, приращение счётчика ровно один. Это проверка обработчика и настроек, не измерение периода по внешним часам. |
| HW_ADC_INITIALIZATION | ADC включён, /2, программный триггер, калибровка завершена, длинная выборка внутренних каналов; VREFINT перед температурой. Проверки на границе C++ convert без повторного вызова init. |

Новые комментарии на русском. Как в mcu_power_board: условия → наблюдение → records →
таблица утверждений. Строки таблицы — выражения GDB, строки одиночного check — данные Python;
маски сравниваются с масками, логические значения явно нормализованы. Макросы используются
в кадрах с CMSIS. Records содержат обычные Python-числа и строковые ключи.
Для ELF-контракта используется SysTick_Handler: закреплённый валидатор не принимает C++
имя post::run в поле macros.context. Реальные проверки идут в convert из post.cpp.

## Проверено 15.10.2026

Windows, OpenOCD 0.12.0/ST-Link, WeAct F103CB, xPack 14.2.1-1.1 (GDB 15.2.90),
модуль eb085b3 (main после v0.4.1; номер Python-пакета ещё 0.4.1, не выпущенная 0.4.2).
Все 15 аппаратных сценариев PASS, захват SAVED, команды 0; host обоих профилей 16/16.
Карта: 33 CONFIRMED, 28 уникальных строк, 0 FAILED/UNKNOWN. Это весь выбранный набор
связей, а не 100% прошивки. Исходники C/C++ не менялись. C8 на железе в этой серии не проверялся.
Предварительный ERROR контракта сохранён локально; это ошибка сценария до доступа к плате.
Предупреждения inferred_stop из существующих watchpoint-сценариев сохранены: причина
остановки восстановлена модулем, а не явно сообщена GDB.

## Почему именно эти строки

Входы функций привязаны к подтверждённому вызывающему кадру; строки настройки регистров —
к состоянию до следующей стадии; публикации — к проверенному значению; ветви отказа —
к уже существующим инъекциям. Не раскрашиваем весь блок по факту достижения его входа.
Не привязываем проверку сброшенного CAL к строке, устанавливающей CAL: это не доказательство
самого запуска калибровки. Выбор канала и калибровка остаются утверждениями в отчёте.

| Строка | Сценарий | Точное имя проверки |
| --- | --- | --- |
| [src/app.cpp](../src/app.cpp) | `HW_BLINK` | toggles a half period apart, ms |
| [src/app.cpp](../src/app.cpp) | `HW_BLINK` | LED state changed |
| [src/app.cpp](../src/app.cpp) | `HW_BLINK` | blink counter advanced by one |
| [src/app.cpp](../src/app.cpp) | `HW_POST_VDDA_LOW` | setup still finished |
| [src/app.cpp](../src/app.cpp) | `HW_SETUP_DONE` | setup finished |
| [src/app.cpp](../src/app.cpp) | `HW_TOGGLE_WRITERS` | setup() stores the start time, called from main() |
| [src/app.cpp](../src/app.cpp) | `HW_TOGGLE_WRITERS` | loop() stores the toggle time, called from main() |
| [src/main.cpp](../src/main.cpp) | `HW_STARTUP_ORDER` | setup called from main |
| [src/main.cpp](../src/main.cpp) | `HW_STARTUP_ORDER` | loop called from main |
| [src/app.cpp](../src/app.cpp) | `HW_STARTUP_ORDER` | board init called from setup |
| [src/app.cpp](../src/app.cpp) | `HW_STARTUP_ORDER` | UART transmitter before POST |
| [src/app.cpp](../src/app.cpp) | `HW_STARTUP_ORDER` | POST called from setup |
| [src/app.cpp](../src/app.cpp) | `HW_STARTUP_ORDER` | setup published before loop |
| [src/board.cpp](../src/board.cpp) | `HW_STARTUP_ORDER` | LED clock before UART |
| [src/board.cpp](../src/board.cpp) | `HW_STARTUP_ORDER` | LED initially off |
| [src/board.cpp](../src/board.cpp) | `HW_STARTUP_ORDER` | LED output before UART |
| [src/board.cpp](../src/board.cpp) | `HW_STARTUP_ORDER` | SysTick reload before UART |
| [src/board.cpp](../src/board.cpp) | `HW_STARTUP_ORDER` | SysTick enabled before UART |
| [src/board.cpp](../src/board.cpp) | `HW_SYSTICK_PROGRESS` | SysTick handler increments once |
| [src/uart.cpp](../src/uart.cpp) | `HW_STARTUP_ORDER` | UART clocks before POST |
| [src/uart.cpp](../src/uart.cpp) | `HW_STARTUP_ORDER` | UART pin before POST |
| [src/uart.cpp](../src/uart.cpp) | `HW_STARTUP_ORDER` | UART divider before POST |
| [src/uart.cpp](../src/uart.cpp) | `HW_STARTUP_ORDER` | UART transmitter before POST |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | ADC clock divider |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | ADC clock enabled before sample |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | ADC independent single conversion |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | ADC enabled with internal sensors |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | ADC software trigger |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | internal channels long sampling |
| [src/post.cpp](../src/post.cpp) | `HW_ADC_INITIALIZATION` | one regular conversion |
| [src/post.cpp](../src/post.cpp) | `HW_POST_VDDA_LOW` | VDDA computed from the substituted sample |
| [src/post.cpp](../src/post.cpp) | `HW_POST_VDDA_LOW` | POST reports VDDA out of range |
| [src/post.cpp](../src/post.cpp) | `HW_POST_ADC_CLEANUP` | ADC and internal sensors released |
| [src/app.cpp](../src/app.cpp) | `HW_DMA_CAPTURE` | block accepted exactly once |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | DMA clock enabled |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | ADC scan enabled |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | ADC scans two channels |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | ADC channel order |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | DMA halfword normal mode |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | DMA peripheral address |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | DMA owned buffer address |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | DMA block length |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | DMA transfer completed |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | one IRQ per block |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_CAPTURE` | block accepted exactly once |
| [src/monitor.cpp](../src/monitor.cpp) | `HW_DMA_TIMEOUT` | missing requests timed out |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_PROCESS` | first voltage seeds filter |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_PROCESS` | Kalman second voltage |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_PROCESS` | temperature conversion |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_PROCESS` | two valid blocks accepted |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_PROCESS` | two invalid blocks rejected |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_PROCESS` | bad block preserves filter |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_CAPTURE` | DMA voltage plausible |
| [src/monitor_processing.cpp](../src/monitor_processing.cpp) | `HW_DMA_CAPTURE` | DMA temperature plausible |

## Повторить и увидеть в VS Code

Откройте папку проекта. Используйте Coverage Gutters → Watch; затем откройте src/main.cpp,
board.cpp, uart.cpp или post.cpp. Workspace настроен искать только build/ddtt-view/lcov.info;
персональный абсолютный путь не нужен. Если видны старые отметки, выполните Coverage Gutters:
Remove Coverage, затем Watch (или Display Coverage для текущего файла).

Зелёный — утверждение подтвердилось; красный — выполненное утверждение не подтвердилось;
без отметки — нет достоверного свидетельства. Причины — build/ddtt-view/ddtt-evidence.json.
Имена/хеши проверяются экспортёром. После изменения исходников нужны сборка и новый прогон;
одной перепривязки карты недостаточно. Не объединяйте старые архивы с выбранной кампанией.

```powershell
# Из корня проекта; новая папка кампании при каждом повторении.
cmake --preset f103cb-hil
cmake --build --preset f103cb-hil
ctest --preset f103cb-hil-host
$campaign = "build/ddtt-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force "$campaign/runs", build/ddtt-view | Out-Null
# Удаляем старые цветные отметки до новой серии, включая случай её аварийного завершения.
Set-Content build/ddtt-view/lcov.info -Value ''
$session = Get-Content build/f103cb-hil/hwtest/session.json -Raw | ConvertFrom-Json
$session.out = (Resolve-Path "$campaign/runs").Path
$session | ConvertTo-Json -Depth 20 | Set-Content "$campaign/session.json" -Encoding utf8
python modules/stm32-gdbtest/examples/ddtt-coverage/bind_map.py --project . --elf build/f103cb-hil/stm32_hwtest_bluepill.elf --template hil/ddtt-f103cb.template.json --out "$campaign/map.json"
# Все сценарии, указанные картой; остальные аппаратные проверки — ctest --preset f103cb-hil-hw.
$cases = (Get-Content hil/ddtt-f103cb.template.json -Raw | ConvertFrom-Json).points.scenario | Sort-Object -Unique
foreach ($case in $cases) {
    python modules/stm32-gdbtest/stm32_gdbtest/cli.py run --session "$campaign/session.json" --stand hil/F103CB/stands/local.toml --identity-policy strict --test $case
    if ($LASTEXITCODE -ne 0) { break } # Сохраняем отказ; сначала разбираем его причину.
}
# Выполнить и при FAIL/ERROR: неизвестное не станет зелёным или фиктивным нулём.
python hil/tools/ddtt_export.py --runs "$campaign/runs"
```

## Границы

GPIO ODR не доказывает физическое свечение. Настройки USART/TC не доказывают форму сигнала
на выводе. ADC sampling/clock не доказывают точность температуры; прерывания под GDB не
измеряют реальные сроки. DMA, фильтр и пользовательская кнопка — следующий этап. Ни записи
произвольной SRAM, ни вмешательства в периферию новые сценарии не выполняют.

Текущий этап: [ADC/DMA и HTML-отчёт](ADC_DMA.md), 64 связи на 55 строках; выше результаты первоначальной серии запуска.

Актуальные результаты и экспорт с защитой: [BUTTON](BUTTON.md), 74 связи / 65 строк. Таблицы выше описывают прежние этапы; текущие номера строк смотрите в свежем HTML.
