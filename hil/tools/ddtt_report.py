"""HTML-пояснение к DDTT: выбранное свидетельство, сценарий и история данной кампании."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
from urllib.parse import quote


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


# VS Code открывает исходник на строке; в браузере потребуется разрешить внешний протокол.
def code_link(path, line=1):
    uri = "vscode://file/" + quote(Path(path).resolve().as_posix(), safe="/:") + ":" + str(line)
    return escape(uri, quote=True)


# Ищем определения case без импорта GDB-сценариев на host.
def scenarios(root):
    result = {}
    for path in (root / "hil/common/tests/board").glob("test_*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    if decorator.func.id == "case" and decorator.args:
                        result[ast.literal_eval(decorator.args[0])] = (path, node.lineno)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--runs", required=True)
    parser.add_argument("--view", default="build/ddtt-view")
    args = parser.parse_args()
    root, runs, view = Path(args.project).resolve(), Path(args.runs).resolve(), Path(args.view).resolve()
    output = view / "index.html"
    # Не оставляем прежний зелёный отчёт, если проверка входов не удалась.
    view.mkdir(parents=True, exist_ok=True)
    output.write_text("<!doctype html><meta charset=utf-8><p>DDTT report: generation incomplete / ERROR</p>", encoding="utf-8")
    report = load(view / "ddtt-evidence.json")
    if report.get("status") != "EXPORTED":
        raise ValueError("Сначала выполните успешный экспорт LCOV")
    cases = scenarios(root)
    attempts = {}
    for path in runs.glob("*/result.json"):
        data = load(path)
        if data.get("mode") == "hardware":
            attempts.setdefault(data["id"], []).append((path.resolve(), data))
    rows = []
    now = datetime.now(timezone.utc)
    for point in report["points"]:
        evidence = point.get("evidence")
        data = None
        link = "—"
        age = "—"
        values = "Нет выполненного утверждения"
        if evidence:
            path = Path(evidence["path"]).resolve()
            if not path.is_relative_to(runs):
                raise ValueError("Свидетельство находится вне выбранной кампании")
            if hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]:
                raise ValueError("Результат изменён после экспорта")
            data = load(path)
            link = '<a href="' + escape(path.as_uri(), quote=True) + '">result.json</a>'
            records = path.with_name("records.json")
            if records.exists():
                link += ' · <a href="' + escape(records.as_uri(), quote=True) + '">records.json</a>'
            started = datetime.fromisoformat(data["started_utc"].replace("Z", "+00:00"))
            hours = max(0, (now - started).total_seconds() / 3600)
            age = escape(started.astimezone().isoformat(timespec="seconds")) + f" ({hours:.1f} ч назад)"
            selected = [{"actual": c.get("actual"), "expected": c.get("expected"), "passed": c.get("passed")}
                        for c in data.get("checks", []) if c.get("name") == point["check"]]
            values = escape(json.dumps(selected, ensure_ascii=False, indent=2))
        scenario = point["scenario"]
        target = cases.get(scenario)
        case_link = escape(scenario)
        if target:
            case_link = '<a href="' + code_link(*target) + '">' + case_link + '</a>'
        history = attempts.get(scenario, [])
        compatible = sum(d.get("elf_sha256") == report["elf_sha256"] for _, d in history)
        hist = []
        for path, attempt in sorted(history, key=lambda item: item[1]["started_utc"]):
            label = attempt["started_utc"] + " · " + attempt["status"]
            hist.append('<li><a href="' + escape(path.as_uri(), quote=True) + '">' + escape(label) + '</a></li>')
        state = point["state"]
        source = root / point["source"]
        row = f'<tr data-state="{escape(state)}"><td><a href="{code_link(source, point["line"])}">'
        row += escape(point["source"]) + ':' + str(point["line"]) + '</a><pre>' + escape(point["anchor"]) + '</pre></td>'
        row += '<td>' + escape(point["check"]) + '<br><small>' + case_link + '</small></td>'
        row += '<td class="' + state + '">' + state + '<br><small>' + escape(point["reason"]) + '</small></td>'
        row += '<td>' + age + '<br>' + link + '<details><summary>Факт / ожидание</summary><pre>' + values + '</pre></details></td>'
        row += f'<td>{len(history)} всего / {compatible} с этим ELF<details><summary>Попытки</summary><ul>' + ''.join(hist) + '</ul></details></td></tr>'
        rows.append(row)
    html = """<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>DDTT — свидетельства проверок</title><style>
:root {color-scheme:light dark;--bg:#f6f8fb;--panel:#fff;--ink:#203047;--line:#d7dfeb}
@media(prefers-color-scheme:dark){:root{--bg:#131a23;--panel:#1c2633;--ink:#e4eaf3;--line:#38475c}}
body{font:16px/1.5 system-ui;margin:0;background:var(--bg);color:var(--ink)}
header{padding:24px 30px}h1{margin:0}p{max-width:1100px}a{color:#4d91e7}small{font-size:14px}
nav{position:sticky;top:0;padding:14px 30px;background:var(--panel);border-block:1px solid var(--line);display:flex;gap:14px}
input,select{font:inherit;padding:7px;border:1px solid var(--line);border-radius:5px;background:var(--bg);color:var(--ink)}
input{width:42%}main{padding:20px;overflow:auto}table{border-collapse:collapse;width:100%;background:var(--panel)}
th,td{text-align:left;padding:14px;border-bottom:1px solid var(--line);vertical-align:top}th{white-space:nowrap}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-width:550px;font:13px/1.5 monospace}summary{cursor:pointer}
.CONFIRMED{color:#29936b}.FAILED{color:#e66363}.UNKNOWN{color:#cf992d}</style>
<header><h1>DDTT · свидетельства проверок</h1><p>Зелёный — подтверждено ожидание; красный — выполненная проверка не прошла;
UNKNOWN — нет достоверного свидетельства. DA остаётся 0/1. Число попыток относится только к выбранной кампании,
а совпадение ELF само по себе не означает PASS. Время «назад» — на момент формирования отчёта.</p>
<p>Исходник и имя сценария открываются в VS Code. JSON — сохранённые артефакты; Preview Report может ограничивать
переходы к локальным файлам, тогда откройте HTML в браузере.</p>"""
    html += '<p>' + escape(json.dumps(report["summary"])) + ' · ELF ' + escape(report['elf_sha256'][:16]) + '</p></header>'
    html += '<nav><input id="query" placeholder="Файл, сценарий или проверка"><select id="state"><option value="">Все исходы</option><option>CONFIRMED</option><option>FAILED</option><option>UNKNOWN</option></select><span id="count"></span></nav>'
    html += '<main><table><thead><tr><th>Исходник</th><th>Проверка / сценарий</th><th>Исход</th><th>Выбранная попытка</th><th>История</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></main>'
    html += """<script>const q=document.querySelector('#query'),s=document.querySelector('#state');
function filter(){let n=0;document.querySelectorAll('tbody tr').forEach(r=>{r.hidden=!(r.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!s.value||r.dataset.state===s.value));if(!r.hidden)n++;});document.querySelector('#count').textContent=n+' связей';}q.oninput=filter;s.onchange=filter;filter();</script></html>"""
    output.write_text(html, encoding="utf-8")
    print(f"HTML: {output} ({len(rows)} links)")


if __name__ == "__main__":
    main()
