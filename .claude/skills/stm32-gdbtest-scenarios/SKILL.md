---
name: stm32-gdbtest-scenarios
description: Техника написания тестовых сценариев stm32-gdbtest на API_VERSION=3 (линии 0.5.x и 0.6.x) — требование и контракт, выбор места остановки, таблицы check(rows) и write(rows), подмена возврата ret, инъекции, refused, watch/frames, профиль прогона, стиль сценариев и каталог техник TECH-001…027. Используй, когда просят «написать сценарий/тест для платы», «проверить регистр/периферию/callback через GDB», «добавить HW_-кейс», «перевести сценарии с value/set_value/force_return на новый API», «сделать ревью сценария»; по-английски — write a stm32-gdbtest scenario, hardware test case, migrate scenarios to API 3.
license: MIT
compatibility: stm32-gdbtest 0.6.x (API_VERSION 3); Python 3.11+, GDB с Python 3.11+ (arm-none-eabi-gdb-py3); плата нужна только для прогона, prepare выполняется без неё
metadata:
  author: Viacheslav Mezentsev
  version: "0.6.1"
  module: stm32-gdbtest
  api_version: "3"
---

# Сценарии stm32-gdbtest

Сценарий — функция Python с декоратором `@case`, которую агент модуля выполняет внутри GDB на
остановленной в `main()` плате. Он проверяет наблюдаемое поведение прошивки: значения объектов и
регистров в выбранной точке, реакцию на подменённый возврат или аргумент, кто и когда пишет объект.
Результат — `result.json`/JUnit со статусом PASS, FAIL (проверка не сошлась), ERROR
(сценарий не смог выполниться) или SKIP (явный `t.skip(reason)` для неприменимого случая).

Пути — от корня модуля (`modules/stm32-gdbtest/` у потребителя). Источники истины:
[справочник API](../../docs/ru/api/index.md), [каталог техник](../../docs/ru/TESTING_TECHNIQUES.md),
[автору тестов](../../docs/ru/TEST_AUTHORING.md), [HAL-макросы](../../docs/guides/ru/HAL_MACRO_GUIDE.md).
Образцы — `tests/firmware/common/tests/board/*.py` и `tests/firmware/profiles/*/tests/board/*.py`.

## Порядок работы

1. **Требование.** В `tests/requirements.md` — `## HW_<ID>` и наблюдаемый критерий: что, в какой
   точке, с каким ожиданием, какое влияние halt/reset допустимо. Ожидание берётся из RM, схемы
   платы и кода, а не из наблюдённого значения ради PASS.
2. **Место остановки.** Функция, в которой состояние уже установлено и видимо (TECH-016). Макросы
   CMSIS/HAL раскрываются только в единице трансляции, которая включает заголовок устройства (TECH-001).
3. **Контракт.** Если сценарий берёт макросы или символы из ELF, перечисли их в `tests/contracts.json`
   (`context` — функция той единицы трансляции) и укажи `contracts=("…",)` в `@case`.
   Тогда отсутствие макроса — ERROR подготовки до платы, а не ноль на плате.
4. **Сценарий** по шаблону ниже.
5. **Проверка без платы** — `prepare.<ID>` (метка `host`), затем один `hw.<ID>` на стенде
   (навык `stm32-gdbtest-run`). Прочитать `result.json`: какие проверки, какие значения.

## Шаблон

```python
"""
RU: Конфигурация TIM2 и публикация результата обработчика прерывания.
EN: TIM2 configuration and the interrupt handler result publication.
"""
from stm32_gdbtest import case, within


# TIM2 counts at 1 kHz and overflows every 100 ms (RM: PSC + 1, ARR + 1).
TIMER_TICK_HZ = 1_000
TIMER_PERIOD_TICKS = 100


# Verify the timer configuration after board initialization.
@case("HW_TIM2_INIT", labels=("timer",), contracts=("tim2_macros",))
def tim2_init(t):
    # CMSIS macros are visible in board.c, the translation unit that includes the device header.
    t.reach("board_led_toggle")

    # SVD must define TIM2 registers; check ready Python values individually.
    prescaler = t.read("SystemCoreClock") // TIMER_TICK_HZ - 1
    t.check("prescaler", t.mmio.read("TIM2.PSC"), prescaler)
    t.check("period", t.mmio.read("TIM2.ARR"), TIMER_PERIOD_TICKS - 1)
    t.check("update interrupt", bool(t.mmio.read("TIM2.DIER") & t.evaluate("TIM_DIER_UIE")), True)
    t.check("counter enabled", bool(t.mmio.read("TIM2.CR1") & t.evaluate("TIM_CR1_CEN")), True)


# Verify that the handler publishes one period to the application.
@case("HW_TIM2_PUBLICATION", labels=("timer", "irq"))
def tim2_publication(t):
    t.reach("TIM2_IRQHandler")
    before = t.read("app_state.periods")

    # TECH-003: the result is checked after the handler returns, where the application sees it.
    t.finish()
    t.check("one period published", t.read("app_state.periods") - before, 1)
    t.check("counter wrapped", t.mmio.read("TIM2.CNT"), within(0, TIMER_PERIOD_TICKS - 1))
```

## Что чем проверять

| Задача | Средство | Техника |
| --- | --- | --- |
| Три и более значения цели в одной точке | `t.check([(имя, "выражение GDB", ожидание), …])` | TECH-010 |
| Одно значение объекта / выражения | `t.check(имя, t.read(path), ожидание)`, `t.evaluate(expr)` | — |
| Диапазон, допуск, набор, шаблон | `within`, `near`, `one_of`, `matches` | TECH-007 |
| Остановиться на этапе | `reach(функция)`, `finish()`, `until(функция)`, `step()` | TECH-016 |
| Нужный вызов из многих | `reach(loc, condition="…")`, `breakpoint(…, ignore_count=N)` | TECH-015 |
| Отказ вызванной функции | на входе `t.ret("HAL_ERROR")`, затем состояние вызывающего | TECH-004 |
| Неверный аргумент | `t.write("arg", значение)` на входе функции | TECH-005 |
| Управляемое состояние периферии | `t.mmio.write("GPIOA.BSRR", mask)` по SVD, без скрытого чтения | TECH-006, [MMIO](../../docs/ru/api/mmio.md) |
| Результат callback/IRQ | остановка в публикации или `finish()` из обработчика | TECH-003 |
| Кто пишет объект | `with t.watch(path): t.resume()`, затем `t.frames()` | TECH-013 |
| Функция прошивки как проверка | `t.call(...)` с сохранением и восстановлением `t.memory` | TECH-014 |
| Ожидаемый отказ API | `with t.refused(code, name=…)` | TECH-012 |
| Заявленные кристалл, образ, сборка | `t.profile` (`target`, `build`, `data`, `get()`) | TECH-017 |
| C-строки | `$_streq(...)` в ячейке таблицы или `t.evaluate(path, as_type=str)` | TECH-018 |
| Серия измерений | `t.record(name, data)`, расчёт по `t.records(name)` | TECH-011 |
| Адрес до смены контекста DWARF | сохранить `t.symbol(...)["address"]` заранее | TECH-002 |
| Сон и WFI | контекст прерванного WFI | TECH-008 |
| Контекст исключения (ISR) | `t.mmio.read("SCB.ICSR") & t.evaluate("SCB_ICSR_VECTACTIVE_Msk")`; не `$xPSR` — имя регистра зависит от GDB-сервера | TECH-027 |
| Метод или функция C++ | `t.call("ns::Class::method", …, this="&obj", signature="…")`, `Pointer`/`Reference` | [call](../../docs/ru/api/call.md) |
| Длинная серия воздействий | квоты журнала api schema 3, `t.records()` с `require_complete=True` | [журналирование](../../docs/ru/JOURNALING.md) |
| Имитируемый вход | подмена в SRAM до чтения или `ret` драйвера, затем проверка использования значения прошивкой | [маршруты 0.6.0](references/release-060-routes.md), A5 |

Ссылка на технику — комментарий у нетривиального действия:
`# TECH-004: <URL закреплённой версии модуля>/docs/ru/TESTING_TECHNIQUES.md#tech-004`.

## Правила

**Ожидания.** Биты, маски, номера IRQ и адреса — идентификаторами прошивки (`"GPIO_MODER_MODER13_0"`),
физические величины — именованными константами с комментарием-источником. В таблице строковая
ячейка — выражение GDB, число и сопоставитель — значения Python. Значения Python (результаты
методов API, строки, коллекции, `t.profile`) проверяются отдельными `t.check`, не строками таблицы.

**Навигация.** Место остановки — функция. Адрес `файл:строка` ломается от любой правки исходника;
его не использовать. `reach` проверяет фактическую причину остановки: установленная точка сама по
себе не проверка.

**Безопасность чтения.** Не читать регистры с побочным эффектом (read-to-clear, FIFO, SR→DR) без
нужды и не сравнивать зарезервированные биты MMIO — маскировать. Не выдавать setter-макрос HAL за
чтение. Регистры «только запись» (RM: `wo`) не читать; ноль не гарантирован — проверять через читаемые (у AT32F403A
`RTC_DIV`/`RTC_TA` — через `RTC_DIVCNT`/`RTC_CNT`). Для МК не от ST выражения могут читать битовые поля SDK
производителя (`GPIOC->odt_bit.odt13`), значение регистра целиком — сравнивать с константой из позиций битов RM. Восстановление после инъекции планируется отдельно: сброс следующего сценария
не гарантирует возврат памяти, периферии и внешних нагрузок. Для положительной
проверки — отдельный кейс с подтверждённым начальным состоянием.

**Чего не доказывает.** Значение регистра GPIO — не напряжение на выводе; `uwTick` — не точное
внешнее время; остановки отладчика меняют время исполнения; Sleep под SWD — не ток потребления.
Пиши это в требовании, а не обещай в имени проверки.

**Ошибки не прячь.** Без `try/except ApiError` вокруг операций; ожидаемый отказ — `refused`.
Отрицательный сценарий сохраняет причину FAIL/ERROR.

## Стиль

Правила проверяет `tests/host/test_scenario_style.py`; свои файлы:
`python modules/stm32-gdbtest/tests/host/test_scenario_style.py hil/tests/board/*.py`.

- Заголовок модуля — строки `RU:` и `EN:`; остальные комментарии на английском.
- Комментарий о назначении над каждой функцией (над декоратором), две пустые строки между
  функциями верхнего уровня и после импортов.
- Блоки внутри функции разделены пустой строкой; комментарий открывает блок; таблицы и циклы
  поясняются комментарием над ними.
- Строка до 120 символов; что помещается — одной строкой; продолжение по открывающей скобке или
  +4, если скобка закрывает строку. Без завершающих запятых, кроме одноэлементного кортежа `("adc",)`.
- Объект цели называется `t`; константа модуля поясняется комментарием.

## Миграция со старого API

| Было | Стало |
| --- | --- |
| `t.check(n, t.value("expr"), v)` подряд три и больше | `t.check([(n, "expr", v), …])` |
| `t.value("obj")` | `t.read("obj")`; выражение — `t.evaluate("expr")` |
| `t.fields("expr", {...})` | `t.read("obj", fields=…)` или `t.check(rows)` |
| `t.set_value("x", v)` | `t.write("x", v)` (проверяет применённое значение) |
| `t.force_return("HAL_ERROR")` | `t.ret("HAL_ERROR")` |
| `t.config`, `t.config_props`, `settings`, `sources` | `t.profile` (`get("a.b")`, `origin()`) |
| `try: … except ApiError` | `with t.refused(code):` |
| `def f(target)`, `target.…` | `def f(t)` |
| `t.reach("main.c:120")` | `t.reach("функция")` / `t.finish()` |

Старые `value`, `fields`, `set_value`, `force_return` удалены из API 0.4.0/0.4.1 (`API_VERSION=2`).
Таблица выше служит только для переноса прежних сценариев; новые сценарии используют правую колонку.

## Перед сдачей

- у каждого `@case` есть требование с тем же ID, `ctest … -host` зелёный;
- макросы и символы из ELF перечислены в контракте;
- ожидания независимы от наблюдённого результата и названы идентификаторами или константами;
- тест стиля по своим файлам без замечаний;
- один прогон на плате прочитан по `result.json`, побочные эффекты описаны в требовании.

## Свидетельства сценария

Записывай record там, где понятны точка наблюдения, единицы и происхождение данных. name — метка,
а не тип; sequence — порядок, не время. Для серии проверяй публикации/повторы и явно задавай N−1/N
при расчёте СКО. Внешний экспорт не выполняет GDB-выражения из records.
Сохранение на диск включает session.toml `[results] capture = true`; лимиты остаются в api.toml.

skip завершает весь сценарий, finally выполняется; для необязательного блока нужен if.
Неприменимость отделяй от обнаруженной неисправности: последняя не становится SKIP ради зелёного отчёта.
Для bit-полей и коллекций используй принятые bits/each/predicate по [справочнику](../../docs/ru/api/index.md),
не заменяя проверку маски равенством всего регистра. Примеры пакета: test_records.py, test_skip.py, test_skip_validation.py, test_string_views.py в общих сценариях.
После прогона сопоставь выполненные ветви и checks с журналом по
[навыку результатов](../stm32-gdbtest-results/SKILL.md); наличие record само по себе не является check.

## Осмотр перед длительным опытом

Перед аппаратной серией прочитай [шпаргалку сценариста](../../docs/ru/SCENARIO_CHECKLIST.md)
([English](../../docs/en/SCENARIO_CHECKLIST.md)). Проверь предпосылки обвязки отдельно от
поведения приложения; prepare не исполняет тело аппаратного сценария. Для анализа по records
заранее определи обязательные записи и проверь захват. После неожиданного исхода различи
ошибку приложения, сценария, обвязки, API и исходного предположения; не ослабляй ожидание
до установления причины. Эвристическое замечание не объявляй нарушением контракта.

Для периферии используй SVD и [mmio.read/write](../../docs/ru/api/mmio.md).
Обычный write даже с verify=False может читать before и не является MMIO-контрактом.
mmio.write принимает целое Python, не выражение; ACK не означает проверку состояния.
Эффекты требуют allow_effects=True. Override требует причину и не снимает транспортные
проверки. Ошибка после отправки означает неизвестный эффект: не повторяй автоматически.
Включи capture для журнала, проверь модель в Renode и затем согласованный стенд.


## Исполнение API 3

В обычном def навигация и call блокируют до результата. В async def используй await
для reach/step/until/finish/reset/resume(sync=True)/call с первого вызова, включая
помощники. resume(sync=False), данные, точки, record/check и ret остаются немедленными.
wait и halt требуют await и конечного timeout; timeout wait не останавливает цель.
Доступ к цели возможен только после подтверждённой остановки. finally с await halt
не заменяет восстановление памяти/регистров и не завершает прерванный call.
Не используй execute в async и скрытые inferior calls в выражениях данных; вынеси
их в явный call. Обычный def не нужно превращать в async без живого окна.
[Контракт и миграция](../../docs/ru/LIVE_EXECUTION.md) описывают отказные пути.

## Практика состояния и порядка событий

Примени [приёмы и нейтральный пример](../stm32-gdbtest-scenarios/references/stateful-evidence.md):
следующая операция без reset, wrap и busy/complete, исходный FAIL, исправление,
повтор и полное восстановление объекта. Ресурс также задаёт границы переноса
на DMA, логическое время и внешние свидетели. Renode подтверждает модель, не плату.

## Нейтральные примеры (0.5.0 и новее)

Для порогов и retry используй logical-time; для wrap счётчика и baseline — counter-cost;
для записи другого источника — external-capture. [Нейтральные маршруты](references/neutral-workflows.md)
дают команды и точные отрицательные контроли. Сохраняй факт до check; call возвращает
словарь, а отказ приложения не является refused API. Ожидания проекта задай независимо.

## Возможности 0.6.0

- Длинные серии воздействий — квоты журнала api schema 3 в `api.toml` ([журналирование](../../docs/ru/JOURNALING.md)); `t.records()` по умолчанию отказывает при неполном журнале (`incomplete_evidence`), частичное чтение — только явно `require_complete=False`.
- Методы и функции C++ — `t.call("ns::Class::method", …, this="&obj", signature="…")`, указатели и ссылки — `Pointer`/`Reference` из `stm32_gdbtest` ([call](../../docs/ru/api/call.md)).
- Имитируемый вход (подмена данных в SRAM или результата функции через `ret`) доказывает реакцию логики после точки чтения, а не путь сигнала от вывода; проверяй, что прошивка использовала подставленное значение. Физический вход требует внешнего источника сигнала.
- Контекст исключения проверяй по `SCB.ICSR` (VECTACTIVE) через `t.mmio`, а не через `$xPSR`: имя регистра (`xPSR`/`xpsr`) зависит от GDB-сервера.
- Пошаговый проход сценария в VS Code при его написании — `run --interactive` ([ручная отладка](../../docs/ru/MANUAL_DEBUG.md)); результат такого прогона не является свидетельством приёмки.

[маршруты 0.6.0](references/release-060-routes.md) — пакеты A1–A6: команды, принимаемый исход, пары «правильно/неправильно».
