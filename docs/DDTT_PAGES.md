# Переносимый отчёт DDTT для GitHub Pages

[English](DDTT_PAGES.en.md)

Генератор `hil/tools/ddtt_pages.py` создаёт локальный статический комплект в
`build/ddtt-pages`. Он ничего не публикует, не подключает GitHub App и не меняет настройки репозитория.
Откройте `index.html`: весь исходник показан с номерами строк, выбором файла и фильтром
привязок. По нажатию строки справа видны проверки и ссылки на исходник/сценарий GitHub
по полному SHA, а не по движущемуся main. Тёмная, светлая и автоматическая темы.

Зелёная строка — все связанные утверждения подтверждены; красная — хотя бы один FAIL;
жёлтая — есть UNKNOWN при отсутствии FAIL. Без привязки строка не окрашена.
Условие из нескольких частей может быть зелёным по отдельному проверенному ожиданию:
смотрите список утверждений, это не заявление полного покрытия ветвей.

## Публичный комплект

- `index.html`: встроенные исходники проверенной ревизии, CSS/JS без CDN и внешних зависимостей;
- `public-data.json`: разрешённые поля карты, булевы исходы, UTC, SHA и ссылки;
- `lcov.info`: относительные `SF:src/...`, DA=0/1;
- `coverage.xml`: тот же набор строк в Cobertura;
- `.nojekyll`: статические файлы готовы для будущего размещения.

Не копируются сырые result/records/run/config, стенды, UID/серийники, адреса серверов,
персональные пути и произвольные actual/expected. Исходники и имена проверок берутся из
отслеживаемой ревизии: содержимое этих публичных файлов всё равно должно быть пригодно
для публикации. Полные свидетельства остаются локальными. Экспорт не является подписанной
аттестацией и не защищает от намеренной подделки всех локальных входов одновременно.

UNKNOWN не записывается как DA=0. Если на строке есть CONFIRMED и UNKNOWN без FAIL,
она исключается из обоих числовых форматов. Поэтому числовая сводка — только выбранные
достоверные утверждения, не процент всей прошивки. Сводка JSON сохраняет неизвестные связи.

## Привязка к проверенной ревизии

Прежние result.json не сохраняли хеш Python-сценария. Не приписывайте старым результатам
такое подтверждение задним числом. `ddtt_provenance.py begin` снимает хеши входов до
кампании, `seal` сравнивает их после и закрепляет хеши результатов. Экспорт сверяет:

1. неизменность исходников, сценариев, карты и конфигурации с выбранным Git SHA;
2. инвентарь результатов и их SHA-256;
3. исходы, заново рассчитанные штатным DDTT-экспортёром, и привязки строк;
4. сценарий выбранного результата и определение его case в ревизии.

CRLF/LF допускается только при сравнении с Git blob; локальные хеши свидетельств точные.
В процессе кампании входы не редактируют. Снимок до/после не обнаруживает временную
правку, которую успели вернуть; такой параллельный рабочий процесс не поддерживается.
Изменение несвязанных документов не мешает использовать прежнюю проверенную ревизию.
Вывод разрешён в отдельный каталог build с пятью известными файлами; посторонние файлы
вызывают отказ. При ошибке входов прежняя раскраска и публичная сводка очищаются.

## Повторить локально

Сначала сохраните/согласуйте ревизию тестируемых входов, соберите `f103cb-hil` и выполните
`ctest --preset f103cb-hil-host`. Не используйте существующую папку runs для новой кампании.

```powershell
$revision = git rev-parse HEAD
$campaign = "build/ddtt-public-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force "$campaign/runs" | Out-Null
python hil/tools/ddtt_provenance.py begin --revision $revision --runs "$campaign/runs" --out "$campaign/campaign.json"
if ($LASTEXITCODE -ne 0) { throw "Provenance begin failed" }
$session = Get-Content build/f103cb-hil/hwtest/session.json -Raw | ConvertFrom-Json
$session.out = (Resolve-Path "$campaign/runs").Path
$session | ConvertTo-Json -Depth 20 | Set-Content "$campaign/session.json" -Encoding utf8
$cases = Get-ChildItem hil/common/tests/board/test_*.py | ForEach-Object {
    [regex]::Matches((Get-Content $_ -Raw), '@case\("([A-Z0-9_]+)"') | ForEach-Object { $_.Groups[1].Value }
} | Sort-Object -Unique
foreach ($case in $cases) {
    python -B modules/stm32-gdbtest/stm32_gdbtest/cli.py run --session "$campaign/session.json" --stand hil/F103CB/stands/local.toml --identity-policy strict --test $case
    if ($LASTEXITCODE -ne 0) { break } # Сохранить отказ, сначала разобраться с причиной.
}
python hil/tools/ddtt_provenance.py seal --runs "$campaign/runs" --out "$campaign/campaign.json"
if ($LASTEXITCODE -ne 0) { throw "Campaign inputs changed" }
python hil/tools/ddtt_export.py --runs "$campaign/runs"
if ($LASTEXITCODE -ne 0) { throw "DDTT export failed" }
python hil/tools/ddtt_pages.py --runs "$campaign/runs" --provenance "$campaign/campaign.json" --revision $revision --repository ViacheslavMezentsev/stm32-hwtest-bluepill
```

После обычного экспорта также доступна задача VS Code **HIL: DDTT portable report (no publish)**.
Укажите ту же папку runs, campaign.json и полный SHA из campaign.json. Публиковать в будущем
нужно только `build/ddtt-pages`, не `build/ddtt-view` и не весь build. Сам HTML можно переносить
как файл; для скачивания JSON/LCOV/XML рядом нужны остальные четыре файла.

## GitHub и Renode/GDB

GitHub не сканирует репозиторий в поиске LCOV. Для встроенного Code Quality нужно загрузить
Cobertura отдельным action; документация описывает проценты и изменения по файлам в PR,
а не зелёные полосы в обычном blob-просмотре. Указаны Team/Enterprise Cloud:
[настройка](https://docs.github.com/en/code-security/how-tos/maintain-quality-code/set-up-code-coverage),
[формат представления](https://docs.github.com/en/enterprise-cloud@latest/code-security/reference/code-quality/code-coverage).
[Checks annotations](https://docs.github.com/en/rest/checks/runs) позволяют привязать сообщения
к строкам, но не являются картой всех зелёных строк. Для своей полной раскраски подходит
[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

Renode/GDB в CI может выполнять проверки и формировать LCOV/Cobertura с той же трактовкой DDTT.
Нужно отдельно выбрать ожидания, которые модель реально поддерживает, записывать свидетельства,
помечать их как emulator и не объединять с hardware без явного правила. Текущий генератор
принимает аппаратную кампанию; поддержка emulator и загрузка отчётов в GitHub пока не внедрены.
Обычный Renode smoke PASS сам по себе не превращается в карту. Простой первый CI-пример —
вход main, порядок setup/loop и UART-баннер; ADC/DMA остаются отдельными аппаратными свидетельствами.

Проверено локально 15.10.2026: свежая кампания WeAct 28/28 PASS; 94 подтверждённые связи на 72 строках, ревизия 9650ec50120c1e61b778a5f1ef113c45cbaf6d12. Прошли 13 host-тестов: приватность, устаревшие входы, экранирование HTML, навигация по исходникам и тема. Сканирование публичного комплекта и соответствие строк LCOV/Cobertura прошли. Загрузка в GitHub, развёртывание Pages и встроенное отображение GitHub не выполнялись.
