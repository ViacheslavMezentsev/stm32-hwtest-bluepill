# Маршруты 0.6.0: журнал, вызовы C++, воздействия и внешняя запись

Карта пакетов A1–A6 выпуска 0.6.0: что проверяет комплектный пример, какой исход принять
и как правильно и неправильно использовать новый контракт. Команды выполняются **из корня
checkout модуля** той же ревизии; `<gcc-root>` и `<renode>` — установленные ARM GCC (с GDB-Python)
и Renode 1.17. Примеры проверены на Windows и Linux без плат; свежий прогон подтверждай своими
артефактами. Эталонные числа — для комплектных примеров, не требования к проекту потребителя.

## Сводная таблица

| Пакет | Пример | Что принять |
| --- | --- | --- |
| A1 ошибки и лимиты | `tests/renode-backend/run.py` | регрессии исчерпания журнала: ERROR с отдельной диагностикой аудита, cleanup VERIFIED |
| A2 уровни вывода | `tests/renode-backend/run_report.py [--summary]` | 13 исходов full/compact; с `--summary` — 36, включая потерю records и средний FAIL |
| A3 квоты journal | `tests/renode-backend/run_journal.py` | 20 исходов: full/compact × error/truncate; неполные прогоны — command 2 |
| A3 квоты report | `tests/renode-backend/run_report_quota.py` | 32 сочетания; FAIL за пределом префикса остаётся FAIL |
| A4 вызовы C++ | `tests/renode-backend/run_cpp.py` | PASS sync/async и один намеренный ERROR `HW_CPP_OBJECT_BREAK` (dummy frame) |
| A5.1 подмена | `tests/controlled-input/run.py` | 12 прогонов: 8 PASS, 2 FAIL (запись до refresh), 2 ERROR (исключение до потребления) |
| A5.2 вход GPIO | `tests/modeled-gpio/run.py` | анализ PASS вместе с отдельным `negative-control.status=FAIL` ложного «override поднял вход» |
| A5.3 буфер | `tests/buffer-consumption/run.py` | 14 прогонов: 10 PASS, 2 FAIL, 2 ERROR по ожиданию; восстановление подтверждено |
| A6 внешняя запись | `tests/rosbag-import/run.py` | 23 синтетических опыта: 3 PASS, 1 FAIL, 19 UNKNOWN анализа |

Summary кампании PASS означает совпадение **ожидаемой матрицы**, а не превращение намеренных
FAIL/ERROR в PASS. Отсутствие данных или иная причина отказа — остановка разбора.

## A1. Ошибка журнала не скрывает исходную

Правильно: читать исходную ошибку исполнения или транспорта и диагностику аудита раздельно
(имя записи, путь, used/maximum/attempted); при исчерпании журнала оставить исход ERROR и
сократить объём записей или задать явную квоту schema 3. `reason` у MMIO — пояснение без прав.

Неправильно: поднять `max_nodes`, чтобы прогон стал зелёным; ловить RecordError в сценарии;
считать cleanup ERROR причиной отказа сценария, когда остановка подтверждена событием.

```sh
python tests/renode-backend/run.py --toolchain <gcc-root> --renode <renode>
```

## A2. Уровень вывода не меняет данные

Правильно: сравнивать прогоны общим читателем (`stm32_gdbtest.report_data`), сводку проверять
повторным расчётом — `python -m stm32_gdbtest.report_summary <run>/result.json --verify`.
`console=summary` и `failures` меняют вывод терминала, но не коллекции проверок.

Неправильно: сравнивать только status и первую/последнюю строку; подавать сводку как вход DDTT;
считать компактное хранение ускорением (маленький неповторяющийся журнал может вырасти).

```sh
python tests/renode-backend/run_report.py --summary --toolchain <gcc-root> --renode <renode>
```

## A3. Квоты и полнота

Правильно: строгий режим по умолчанию; `truncate` — только когда объём заранее известен и
частичный журнал допустим для конкретного утверждения. Частичный анализ — `records(require_complete=False)`
с явной пометкой; неполный прогон завершается command 2, исход сценария проверяется отдельно.
CSV отклоняет неполный источник целиком, HTML и сводки показывают неполноту, DDTT — UNKNOWN.

Неправильно: переключить политику на `truncate`, чтобы получить PASS; экспортировать усечённый
журнал как обычный набор; выводить подтверждение из отсутствующих обязательных данных.

```sh
python tests/renode-backend/run_journal.py --toolchain <gcc-root> --renode <renode>
python tests/renode-backend/run_report_quota.py --toolchain <gcc-root> --renode <renode>
```

## A4. Вызовы C++ без скрытого исполнения

Правильно: один явный `call` с квалифицированным именем, `this=` (именованный объект или указатель
в SRAM) и `signature=` для перегрузки; аргументы-буферы — `Pointer`/`Reference`; проверить
`outcome`, `return_state`, затем `return_value`. Публичный метод вместо ручной записи private-полей.

```python
# tests/renode-startup/cpp_contracts.cpp: Probe::read() const через именованный указатель
result = await t.call("Probe::read", this="probe_ptr", signature="unsigned int() const", timeout=2)
t.check("returned", result["outcome"], "returned")
t.check("value available", result["return_state"], "available")
```

Неправильно: вызывать функцию внутри `read`/`evaluate`/`write` (отказ `expression_call_forbidden`);
полагаться на выбор перегрузки без `signature` (`ambiguous_function`); передавать поле, индекс или
выражение в `this`; вызывать виртуальный метод; объявлять обработчик, вызванный как метод, аппаратным IRQ.
Отказ до исполнения подтверждается счётчиком вызовов цели, а не только кодом ошибки.

```sh
python tests/renode-backend/run_cpp.py --toolchain <gcc-root> --renode <renode>
```

## A5. Воздействие подтверждается потреблением

Правильно: записать вход, продолжить до обработчика и проверить его реакцию, пропущенные эффекты
и следующий вход; для GPIO модели — вход через модель, а не запись регистра поверх override;
для буфера — пакет в буфере опыта, `call` обработчика через `Pointer` с точной длиной, порядок,
отказ, повторный вход и полное восстановление секции.

Неправильно: считать обратное чтение SRAM или регистра доказательством потребления; оставлять
запись без вызова и называть это проверкой обработчика; переносить вывод на DMA, прерывание или
физический вывод. Такие контроли в примерах — намеренный FAIL.

```sh
python tests/controlled-input/run.py --toolchain <gcc-root> --renode <renode>
python tests/modeled-gpio/run.py --toolchain <gcc-root> --renode <renode>
python tests/buffer-consumption/run.py --toolchain <gcc-root> --renode <renode>
```

## A6. Внешняя запись связывается со снимком только через опоры

Правильно: строгое чтение ROS1 bag v2 со сверкой индекса, каналы с объявленными единицами, время
записи как время приёма на узле; связь со снимком GDB — по переходам счётчика МК до и после чтения
в одном сегменте и измеренной задержке. Иначе анализ UNKNOWN, исход сценария не меняется.

Неправильно: считать последовательные выборки rostopic одновременными или совпадающими с bag;
сравнивать ROS и GDB как независимые датчики; принимать оборванный файл или NaN за измерение.

```sh
python tests/rosbag-import/run.py
python tests/rosbag-import/analysis.py build/rosbag-import/<campaign>/normal
```

Аппаратное подтверждение любого пакета — отдельный согласованный опыт; Renode подтверждает модель.
