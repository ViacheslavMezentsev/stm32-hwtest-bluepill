# Результат цикла DDTT

Дата: 2026-10-10. Модуль v0.4.0 (`9c3ff2d`), Windows/ST-Link/OpenOCD 0.12.0.

Требование: при раннем отказе POST освободить ADC и внутренние датчики до входа в loop.
Исходный код оставлял `ADC_CR2 & (ADON | TSVREFE) = 0x800001`; исправленный — `0`.
Сценарий подменяет VREFINT нулём после реального преобразования и проверяет ошибку POST,
продолжение setup и освобождение ресурса. Это проверка ветви отказа, не физического таймаута ADC.

Первоначальные ERROR сохранены: watchpoint срабатывал на записи нуля при инициализации;
затем макрос ADC1 был недоступен в loop. Сценарий ставит watchpoint после инициализации,
сохраняет CMSIS-адрес и маску в board.cpp. Целевые ожидания не ослаблялись.
После подтверждённого FAIL тот же алгоритм и ожидания прошли на исправленном коде;
позже добавлен только поясняющий комментарий для проверки стиля.

F103CB/PB2: host 13/13; аппаратный набор первоначально 11 PASS + 1 ERROR старой инъекции VDDA.
Её watchpoint также перенесён после инициализации; повтор prepare и HW — PASS.
Итого все 12 сценариев имеют PASS, исходный ERROR сохранён; BOOT/BLINK восстановления — 2/2 PASS.
F103C8/PC13 физически не проверялся. Компилятор 14.2.1, GDB 15.2.90.20241130-git/Python 3.12.8.
Предупреждение `inferred_stop` сохранено: причина watchpoint восстановлена модулем по изменению данных.

| Build | Run ID | Verdict | Checks | ELF SHA-256 |
| --- | --- | --- | --- | --- |
| ddtt-baseline-f103cb | 20261010T113619.613385Z-HW_POST_ADC_CLEANUP-44872 | ERROR | 2 | `420be5e872fc9d3814999bf10e65cc39aeebbea70f97b60bb7f495f1b5dda889` |
| ddtt-baseline-f103cb | 20261010T113708.073555Z-HW_POST_ADC_CLEANUP-41328 | ERROR | 9 | `420be5e872fc9d3814999bf10e65cc39aeebbea70f97b60bb7f495f1b5dda889` |
| ddtt-baseline-f103cb | 20261010T113736.851468Z-HW_POST_ADC_CLEANUP-22732 | FAIL | 12 | `420be5e872fc9d3814999bf10e65cc39aeebbea70f97b60bb7f495f1b5dda889` |
| ddtt-candidate-f103cb | 20261010T113815.774749Z-HW_POST_ADC_CLEANUP-11424 | PASS | 12 | `45cd65c763701b0d236fde707cdde5973176731b90caaa7e29fd4016b8f691f0` |
| ddtt-candidate-f103cb | 20261010T113900.333368Z-HW_POST_ADC_CLEANUP-33188 | PASS | 12 | `45cd65c763701b0d236fde707cdde5973176731b90caaa7e29fd4016b8f691f0` |

Локальные свидетельства (не поставляются в Git): `build/ddtt-feedback/` содержит selection,
export/index, integrity.json, HTML report, hardware-summary.json и baseline-inputs с хешами.
Каталоги `build/ddtt-baseline-*` сохраняют исходные ELF и попытки; `build/ddtt-candidate-*` — исправленные.
Экспорт, проверка целостности и формирование отчёта выполняются отдельно от verdict сценариев.
Платы оставлены с исправленной прошивкой, reset_run подтверждён. Измерение электрических
характеристик внешними приборами и автономная работа qwen/pi этим прогоном не подтверждаются.

## Проверки без платы

Docker: Debug/Release/HIL для C8 и CB — 6 сборок PASS, host по 13/13; форматирование PASS.
Renode/Windows: дымовые проверки C8 и CB — 2/2 PASS (ADC в модели не реализован).
Первый вызов Docker обошёл entrypoint и не нашёл cmake; повтор через штатный entrypoint прошёл.
Стиль всех сценариев — PASS. Export/verify/report — code 0, включая сохранённые FAIL/ERROR.
Это проверки рабочего снимка с SHA-256, не результат GitHub CI; push и land выполняет владелец.
