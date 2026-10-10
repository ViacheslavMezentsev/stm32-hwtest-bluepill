# Цикл DDTT: план проверки

Требование: POST при недопустимом нулевом VREFINT сохраняет PostAdcTimeout, продолжает setup и сбрасывает ADON/TSVREFE до loop.

Исходный сценарий `HW_POST_ADC_CLEANUP` добавляется до исправления прошивки. Ожидаемый исход — FAIL
целевого утверждения (освобождение ADC для BluePill, код 6 для BlackPill), не ERROR окружения.
Далее минимальное исправление приложения, неизменённый сценарий, полный host/аппаратный набор.

Разрешены исходники приложения и HIL; тестовых hooks нет. BluePill: F103CB/PB2;
BlackPill: F411CE и F401CC. Windows, OpenOCD, только USB/SWD и встроенные периферийные узлы.
Identity strict; mass erase и option bytes не используются. Инъекции действуют до сброса.
Последняя прошивка — исправленная версия этого проекта; завершение — штатный BOOT и LED.

Бюджет: до трёх исправлений, одна диагностическая попытка при сбое окружения. USB ERROR,
неверный MCU или неудачное восстановление прекращают аппаратные повторы.

Сборки и evidence хранятся локально: `build/ddtt-baseline-*`, `build/ddtt-candidate-*`;
результаты команд и снимки входов — `build/ddtt-feedback/`. В сессиях включён capture.
Исходные FAIL не перезаписываются. Итог — `ddtt-feedback-results.md` рядом с планом.
Остановки GDB и инъекция не доказывают естественный физический отказ или real-time сроки.

## Повтор исправленной проверки

Локальный файл стенда должен соответствовать подключённой плате.

```powershell
cmake --preset HIL_F103CB -B build/ddtt-candidate-f103cb
cmake --build build/ddtt-candidate-f103cb
ctest --test-dir build/ddtt-candidate-f103cb -L host -j 1 --output-on-failure
python modules/stm32-gdbtest/stm32_gdbtest/cli.py run --session build/ddtt-candidate-f103cb/hwtest/session.json --test HW_POST_ADC_CLEANUP --stand hil/stands/F103CB-openocd.local.toml --identity-policy strict
```
