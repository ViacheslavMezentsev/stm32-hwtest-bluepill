---
name: stm32-gdbtest-scenarios
description: Техника написания тестовых сценариев stm32-gdbtest на API 0.3.0 — требование и контракт, выбор места остановки, таблицы check(rows) и write(rows), подмена возврата ret, инъекции, refused, watch/frames, профиль прогона, стиль сценариев и каталог техник TECH-001…018. Используй, когда просят «написать сценарий/тест для платы», «проверить регистр/периферию/callback через GDB», «добавить HW_-кейс», «перевести сценарии с value/set_value/force_return на новый API», «сделать ревью сценария»; по-английски — write a stm32-gdbtest scenario, hardware test case, migrate scenarios to API 0.3.0.
---

# Сценарии stm32-gdbtest

Сценарий — функция Python с декоратором `@case`, которую агент модуля выполняет внутри GDB на
остановленной в `main()` плате. Он проверяет наблюдаемое поведение прошивки: значения объектов и
регистров в выбранной точке, реакцию на подменённый возврат или аргумент, кто и когда пишет объект.
Результат — `result.json`/JUnit со статусом PASS, FAIL (проверка не сошлась) или ERROR (сценарий не
смог выполниться).

Пути — от корня модуля (`modules/stm32-gdbtest/` у потребителя). Источники истины:
[справочник API](../../docs/ru/api/index.md), [каталог техник](../../docs/ru/TESTING_TECHNIQUES.md),
[автору тестов](../../docs/ru/TEST_AUTHORING.md), [HAL-макросы](../../docs/ru/HAL_MACRO_GUIDE.md).
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

    # Check the prescaler, the period and the enabled update interrupt.
    t.check([
        ("prescaler", "TIM2->PSC", f"SystemCoreClock / {TIMER_TICK_HZ} - 1"),
        ("period", "TIM2->ARR", TIMER_PERIOD_TICKS - 1),
        ("update interrupt", "TIM2->DIER & TIM_DIER_UIE"),
        ("counter enabled", "TIM2->CR1 & TIM_CR1_CEN")
    ])


# Verify that the handler publishes one period to the application.
@case("HW_TIM2_PUBLICATION", labels=("timer", "irq"))
def tim2_publication(t):
    t.reach("TIM2_IRQHandler")
    before = t.read("app_state.periods")

    # TECH-003: the result is checked after the handler returns, where the application sees it.
    t.finish()
    t.check("one period published", t.read("app_state.periods") - before, 1)
    t.check("counter wrapped", t.evaluate("TIM2->CNT"), within(0, TIMER_PERIOD_TICKS - 1))
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
| Управляемое состояние периферии | `t.write(path, "REG | BIT")`, серия — `t.write(rows)` | TECH-006 |
| Результат callback/IRQ | остановка в публикации или `finish()` из обработчика | TECH-003 |
| Кто пишет объект | `with t.watch(path): t.resume()`, затем `t.frames()` | TECH-013 |
| Функция прошивки как проверка | `t.call(...)` с сохранением и восстановлением `t.memory` | TECH-014 |
| Ожидаемый отказ API | `with t.refused(code, name=…)` | TECH-012 |
| Заявленные кристалл, образ, сборка | `t.profile` (`target`, `build`, `data`, `get()`) | TECH-017 |
| C-строки | `$_streq(...)` в ячейке таблицы или `t.evaluate(path, as_type=str)` | TECH-018 |
| Серия измерений | `t.record(name, data)`, расчёт по `t.records(name)` | TECH-011 |
| Адрес до смены контекста DWARF | сохранить `t.symbol(...)["address"]` заранее | TECH-002 |
| Сон и WFI | контекст прерванного WFI | TECH-008 |

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
чтение. После инъекции (`ret`, `write` в периферию) состояние платы восстанавливается сбросом
следующего сценария; для положительной проверки — отдельный кейс.

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

Старые `value`, `fields`, `set_value`, `force_return` работают с предупреждением до 0.4.0.

## Перед сдачей

- у каждого `@case` есть требование с тем же ID, `ctest … -host` зелёный;
- макросы и символы из ELF перечислены в контракте;
- ожидания независимы от наблюдённого результата и названы идентификаторами или константами;
- тест стиля по своим файлам без замечаний;
- один прогон на плате прочитан по `result.json`, побочные эффекты описаны в требовании.
