"""Переносимый DDTT: только разрешённые поля, исходники Git SHA и локальная раскраска."""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET
from ddtt_guard import validate_point
from ddtt_provenance import at_revision, digest, path_name, revision, snapshot

FILES = {"index.html", "public-data.json", "lcov.info", "coverage.xml", ".nojekyll"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def github(repository, sha, path, line):
    return f"https://github.com/{repository}/blob/{sha}/{quote(path, safe='/')}#L{line}"


def scenario_line(data, case):
    found = []
    for node in ast.walk(ast.parse(data.decode("utf-8-sig"))):
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "case":
                    if ast.literal_eval(d.args[0]) == case:
                        found.append(node.lineno)
    if len(found) != 1:
        raise ValueError("Scenario definition is ambiguous")
    return found[0]


def prepare(root, view, runs, provenance, repository, sha):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected GitHub owner/repository")
    revision(root, sha)
    campaign = load(provenance)
    if campaign["status"] != "SEALED" or campaign["revision"] != sha:
        raise ValueError("Sealed campaign must match revision")
    if campaign["inputs"] != snapshot(root, sha):
        raise ValueError("Campaign inputs changed")
    results = []
    for name, metadata in campaign["results"].items():
        path = (runs / path_name(name)).resolve()
        if not path.is_relative_to(runs) or digest(path.read_bytes()) != metadata["sha256"]:
            raise ValueError("Campaign result changed")
        if load(path).get("mode") != "hardware":
            raise ValueError("This exporter currently requires hardware evidence")
        results.append(path)
    if set(results) != {p.resolve() for p in runs.glob("*/result.json")}:
        raise ValueError("Campaign result inventory changed")
    report = load(view / "ddtt-evidence.json")
    if report["status"] != "EXPORTED":
        raise ValueError("DDTT export is not valid")
    template = json.loads(at_revision(root, sha, "hil/ddtt-f103cb.template.json"))
    keys = ("source", "anchor", "scenario", "check")
    identity = lambda p: tuple(p[k] for k in keys)
    if Counter(map(identity, template["points"])) != Counter(map(identity, report["points"])):
        raise ValueError("Map differs from revision")
    # Пересчитываем исходы штатным экспортёром; готовому HTML или полю state не доверяем.
    spec = importlib.util.spec_from_file_location("ddtt_export_core", root / "modules/stm32-gdbtest/tools/ddtt_coverage.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    mapping = dict(schema=1, elf_sha256=report["elf_sha256"], points=[
        {k: p[k] for k in (*keys, "source_sha256")} for p in report["points"]])
    points = core.project(root, mapping, results)
    if points != report["points"]:
        raise ValueError("Evidence export is stale or altered")
    public, sources = [], {}
    for p in points:
        validate_point(root, p, bound=True)
        source = p["source"]
        if not source.startswith("src/"):
            raise ValueError("Only project src files may be embedded")
        sources[source] = at_revision(root, sha, source).decode("utf-8-sig").splitlines()
        row = {k: p[k] for k in ("source", "line", "scenario", "check", "state")}
        row.update(source_url=github(repository, sha, source, p["line"]),
                   checks_passed=sum(p.get("verdicts", [])), checks_total=len(p.get("verdicts", [])),
                   started_utc=None, scenario_url=None)
        if p["evidence"]:
            result_path = Path(p["evidence"]["path"]).resolve()
            metadata = campaign["results"][result_path.relative_to(runs).as_posix()]
            if metadata["case"] != p["scenario"]:
                raise ValueError("Scenario attribution mismatch")
            scenario = metadata["scenario"]
            code = at_revision(root, sha, scenario)
            if digest(code) != campaign["inputs"][scenario]:
                raise ValueError("Scenario changed")
            row["scenario_url"] = github(repository, sha, scenario, scenario_line(code, p["scenario"]))
            result = load(result_path)
            # Только дата и булевы исходы: actual/expected/records могут содержать личные данные.
            row["started_utc"] = datetime.fromisoformat(result["started_utc"].replace("Z", "+00:00")).isoformat()
        public.append(row)
    return dict(schema=1, interpretation="DDTT selected assertions; not execution coverage",
                repository=repository, revision=sha, elf_sha256=report["elf_sha256"], environment="hardware",
                campaign_attempts=len(results),
                summary=dict(Counter(p["state"] for p in public)), points=public), sources


def line_state(points):
    states = {p["state"] for p in points}
    if "FAILED" in states:
        return "FAILED"
    if "UNKNOWN" in states:
        return "UNKNOWN"
    return "CONFIRMED" if states else "UNMAPPED"


def formats(public):
    grouped, marks = defaultdict(list), defaultdict(dict)
    for p in public["points"]:
        grouped[(p["source"], p["line"])].append(p)
    for (source, line), points in grouped.items():
        state = line_state(points)
        if state in ("CONFIRMED", "FAILED"):
            marks[source][line] = int(state == "CONFIRMED")
    # UNKNOWN не превращается в 0; смешанная confirmed/unknown строка исключается целиком.
    total = sum(len(m) for m in marks.values())
    covered = sum(sum(m.values()) for m in marks.values())
    coverage = ET.Element("coverage", {"line-rate": str(covered / total if total else 0),
        "branch-rate": "0", "lines-covered": str(covered), "lines-valid": str(total),
        "branches-covered": "0", "branches-valid": "0", "complexity": "0",
        "version": "DDTT-boolean", "timestamp": str(max([int(datetime.fromisoformat(p["started_utc"]).timestamp())
            for p in public["points"] if p.get("started_utc")] or [0]))})
    ET.SubElement(ET.SubElement(coverage, "sources"), "source").text = "."
    package = ET.SubElement(ET.SubElement(coverage, "packages"), "package", {"name": "DDTT",
        "line-rate": coverage.get("line-rate"), "branch-rate": "0", "complexity": "0"})
    classes = ET.SubElement(package, "classes")
    lcov = ["TN:DDTT_selected_assertions"]
    for name, lines in sorted(marks.items()):
        lcov += ["SF:" + name] + [f"DA:{line},{hit}" for line, hit in sorted(lines.items())]
        lcov += [f"LF:{len(lines)}", f"LH:{sum(lines.values())}", "end_of_record"]
        cls = ET.SubElement(classes, "class", {"name": name, "filename": name,
            "line-rate": str(sum(lines.values()) / len(lines)), "branch-rate": "0", "complexity": "0"})
        ET.SubElement(cls, "methods")
        entries = ET.SubElement(cls, "lines")
        for line, hit in sorted(lines.items()):
            ET.SubElement(entries, "line", {"number": str(line), "hits": str(hit), "branch": "false"})
    return "\n".join(lcov) + "\n", ET.tostring(coverage, encoding="unicode")


def render(public, sources):
    groups = defaultdict(list)
    for point in public["points"]:
        groups[(point["source"], point["line"])].append(point)
    sections, panels, options = [], [], []
    for index, (source, lines) in enumerate(sorted(sources.items())):
        options.append(f'<option value="file{index}">{escape(source)}</option>')
        rows = []
        for number, text in enumerate(lines, 1):
            points = groups[(source, number)]
            state, key = line_state(points), f"f{index}l{number}"
            title = f"{source}:{number} — {state}"
            rows.append(f'<button class="code-line {state}" data-key="{key}" title="{escape(title, quote=True)}">'
                        f'<span class="number">{number}</span><code>{escape(text) or " "}</code></button>')
            evidence = []
            for p in points:
                link = (f'<a href="{escape(p["scenario_url"], quote=True)}">{escape(p["scenario"])}</a>'
                        if p["scenario_url"] else escape(p["scenario"]))
                evidence.append(f'<article><strong class="{p["state"]}">{p["state"]}</strong><p>{escape(p["check"])}</p>'
                                f'<p>{link}</p><small>{p["checks_passed"]}/{p["checks_total"]} assertions · '
                                f'{escape(p["started_utc"] or "no evidence")}</small></article>')
            url = github(public["repository"], public["revision"], source, number)
            panels.append(f'<section id="{key}" hidden><h2>{escape(source)}:{number}</h2>'
                          f'<p><a href="{escape(url, quote=True)}">Открыть в GitHub ↗</a></p>'
                          + (''.join(evidence) or '<p>Нет привязки DDTT / unmapped. Это не FAIL.</p>') + '</section>')
        sections.append(f'<section class="source" id="file{index}"'+(' hidden' if index else '')+'>'+''.join(rows)+'</section>')
    css = Path(__file__).with_name("ddtt_pages.css").read_text(encoding="utf-8")
    theme = Path(__file__).with_name("ddtt_theme.js").read_text(encoding="utf-8")
    return ('<!doctype html><html lang="ru" data-theme="dark"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width"><title>DDTT — исходники и свидетельства</title>'
            '<style>'+css+'</style><body><header><h1>DDTT · исходники и свидетельства</h1>'
            '<p>Зелёный — подтверждены выбранные ожидания; красный — есть FAIL; жёлтый — есть UNKNOWN; '
            'без цвета — нет привязки. Это не процент исполнения прошивки. Нажмите строку для подробностей.</p>'
            '<p>Ревизия <a href="https://github.com/'+escape(public["repository"], quote=True)+'/tree/'+public["revision"]+'">'
            +public["revision"]+'</a> · '+escape(json.dumps(public["summary"]))+'</p>'
            '<p>Источник: hardware · '+str(public['campaign_attempts'])+' попыток в зафиксированной кампании.</p>'
            '<p><a href="public-data.json">Публичная сводка</a> · <a href="lcov.info">LCOV</a> · '
            '<a href="coverage.xml">Cobertura</a>. Только выбранные утверждения; UNKNOWN исключён из числового покрытия.</p>'
            '<p>Сценарии и исходники сверены с ревизией до/после кампании. Полные журналы и значения остаются локально.</p></header>'
            '<nav><label>Файл <select id="file">'+''.join(options)+'</select></label>'
            '<label><input id="mapped" type="checkbox"> Только строки с привязками</label>'
            '<button id="theme" aria-label="Тема">☾</button></nav><main><div id="sources">'+''.join(sections)+'</div>'
            '<aside><p id="hint">Выберите строку / Select a line</p>'+''.join(panels)+'</aside></main>'
            '<script>'+theme+'''
const select=document.getElementById('file'),mapped=document.getElementById('mapped');
function filter(){document.querySelectorAll('.source').forEach(s=>s.hidden=s.id!==select.value);
document.querySelectorAll('.code-line.UNMAPPED').forEach(s=>s.hidden=mapped.checked);}
select.addEventListener('change',filter);mapped.addEventListener('change',filter);
document.querySelectorAll('.code-line').forEach(button=>button.addEventListener('click',()=>{
document.querySelectorAll('aside section').forEach(s=>s.hidden=s.id!==button.dataset.key);
document.querySelectorAll('.code-line').forEach(s=>s.classList.toggle('selected',s===button));
document.getElementById('hint').hidden=true;}));filter();</script></body></html>''')


def export(root, view, runs, provenance, repository, sha, out):
    # Отдельный build-каталог: никогда не публикуем сырую папку ddtt-view/runs.
    if (not out.is_relative_to(root / "build") or out == root / "build"
            or out.is_relative_to(view) or view.is_relative_to(out)
            or out.is_relative_to(runs) or runs.is_relative_to(out)):
        raise ValueError("Use a separate build output directory")
    out.mkdir(parents=True, exist_ok=True)
    if any(p.name not in FILES or not p.is_file() or p.is_symlink() for p in out.iterdir()):
        raise ValueError("Output contains unrelated files")
    for name in FILES:
        (out / name).write_text("", encoding="utf-8")
    (out / "index.html").write_text("<!doctype html><meta charset=utf-8><p>DDTT export ERROR / incomplete</p>", encoding="utf-8")
    public, sources = prepare(root, view, runs, provenance, repository, sha)
    lcov, cobertura = formats(public)
    (out / "public-data.json").write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "lcov.info").write_text(lcov, encoding="utf-8")
    (out / "coverage.xml").write_text(cobertura, encoding="utf-8")
    (out / "index.html").write_text(render(public, sources), encoding="utf-8")
    print("Portable DDTT:", out / "index.html", public["summary"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".")
    parser.add_argument("--view", default="build/ddtt-view")
    parser.add_argument("--runs", required=True)
    parser.add_argument("--provenance", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", default="build/ddtt-pages")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    export(root, (root / args.view).resolve(), (root / args.runs).resolve(),
           (root / args.provenance).resolve(), args.repository, args.revision, (root / args.out).resolve())


if __name__ == "__main__":
    main()
