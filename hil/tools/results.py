"""Сводка результатов HIL-тестов stm32-gdbtest.

Читает каталоги запусков build/<пресет>/hwtest/runs/<время>-<ID>-<pid>/result.json.

  python hil/tools/results.py                  последний запуск каждого сценария
  python hil/tools/results.py --all            все запуски, новые сверху
  python hil/tools/results.py HW_BOOT          подробно о последнем запуске сценария
  python hil/tools/results.py --runs build/HIL_F103CB/hwtest/runs ...

Код возврата 1, если в выводе есть FAIL или ERROR.
"""
import argparse
import json
from pathlib import Path
import sys


def load(runs):
    results = []
    for path in runs.glob("*/result.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            data = {"id": path.parent.name, "status": "?", "error": f"unreadable result.json: {error}"}
        data["_dir"] = path.parent
        results.append(data)
    # The directory name starts with the UTC start time, so it sorts chronologically.
    return sorted(results, key=lambda r: r["_dir"].name, reverse=True)


def first_problem(result):
    failed = [c for c in result.get("checks", []) if not c.get("passed")]
    if failed:
        c = failed[0]
        return f"FAIL {c['name']}: {c.get('actual')!r} != {c.get('expected')!r}"
    error = (result.get("error") or "").strip().splitlines()
    return error[-1][:110] if error else ""


def summary(results):
    print(f"{'Сценарий':24} {'Итог':6} {'Режим':9} {'Время UTC':17} {'с':>6} {'Flash':6} Причина")
    for r in results:
        started = str(r.get("started_utc", ""))[:15]
        mode = r.get("mode", "")
        flashed = {True: "запись", False: "-", None: ""}.get(r.get("flashed"), "")
        duration = r.get("duration_s")
        duration = f"{duration:.1f}" if isinstance(duration, (int, float)) else ""
        print(f"{r.get('id', '?'):24} {r.get('status', '?'):6} {mode:9} {started:17} {duration:>6} {flashed:6} "
              f"{first_problem(r) if r.get('status') != 'PASS' else ''}")


def details(result):
    print(f"Сценарий: {result.get('id')}   итог: {result.get('status')}   режим: {result.get('mode')}")
    print(f"Каталог:  {result['_dir']}")
    print(f"Начало:   {result.get('started_utc')}   длительность: {result.get('duration_s')} с   "
          f"запись Flash: {result.get('flashed')}   образ совпал: {result.get('image_verified')}")
    identity = result.get("identity") or {}
    if identity:
        print(f"DEV_ID:   ожидался 0x{identity.get('expected', 0):03X}, прочитан "
              f"0x{identity.get('observed') or 0:03X}, совпадает: {identity.get('matches')}")
    print("\nПроверки:")
    for c in result.get("checks", []):
        mark = "PASS" if c.get("passed") else "FAIL"
        print(f"  {mark} {c['name']}: {c.get('actual')!r} (ожидалось {c.get('expected')!r})")
    for m in result.get("mutations", []):
        print(f"  изменение: {m}")
    for w in result.get("warnings", []):
        print(f"  предупреждение: {w}")
    if result.get("error"):
        print("\nОшибка (последние строки):")
        for line in result["error"].strip().splitlines()[-6:]:
            print("  " + line)
    logs = [name for name in ("gdb.log", "server.log", "tunnel.log", "prepare.log", "recovery.log")
            if (result["_dir"] / name).is_file()]
    print("\nЖурналы: " + ", ".join(logs))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("test", nargs="?", help="ID сценария для подробного вывода")
    parser.add_argument("--runs", type=Path, default=Path("build/HIL_F103C8/hwtest/runs"))
    parser.add_argument("--all", action="store_true", help="все запуски, а не последний каждого сценария")
    parser.add_argument("--prepare", action="store_true", help="включить запуски prepare (без платы)")
    args = parser.parse_args()
    if not args.runs.is_dir():
        sys.exit(f"Нет каталога запусков: {args.runs} (соберите пресет и запустите тесты)")
    results = [r for r in load(args.runs) if args.prepare or args.test or r.get("mode") != "prepare"]
    if args.test:
        chosen = [r for r in results if r.get("id") == args.test and r.get("mode") != "prepare"]
        if not chosen:
            sys.exit(f"Нет аппаратных запусков сценария {args.test} в {args.runs}")
        details(chosen[0])
        return 0 if chosen[0].get("status") == "PASS" else 1
    if not args.all:
        latest = {}
        for r in results:
            latest.setdefault((r.get("id"), r.get("mode")), r)
        results = sorted(latest.values(), key=lambda r: str(r.get("id")))
    summary(results)
    return 0 if all(r.get("status") == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
