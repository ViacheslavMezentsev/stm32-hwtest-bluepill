"""Локальный снимок входов кампании до/после: связывает результаты с Git-ревизией."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def revision(root, value):
    # Разрешаем только полный SHA: имя ветки не является неизменяемой ссылкой.
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Expected a full Git commit SHA")
    if git(root, "rev-parse", value + "^{commit}").decode().strip() != value:
        raise ValueError("Revision is not a commit")
    return value


def path_name(name):
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or not re.fullmatch(r"[A-Za-z0-9_./-]+", name):
        raise ValueError("Invalid project path")
    return name


def at_revision(root, sha, name):
    path_name(name)
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes project")
    data = path.read_bytes()
    blob = git(root, "show", sha + ":" + name)
    # Git checkout на Windows использует CRLF; содержимое сравнивается без этой разницы.
    if data.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
        raise ValueError("File differs from revision: " + name)
    return data


def snapshot(root, sha):
    names = git(root, "ls-tree", "-r", "--name-only", sha, "src", "hil/common/tests", "hil/api.toml",
                "hil/F103CB/board.toml", "hil/F103CB/target.toml", "hil/F103CB/session.toml",
                "hil/common/stm32f103-test.svd", "hil/ddtt-f103cb.template.json").decode().splitlines()
    return {name: digest(at_revision(root, sha, name)) for name in names}


def begin(root, sha, runs, out):
    revision(root, sha)
    if list(runs.glob("*/result.json")):
        raise ValueError("Begin requires a new campaign directory")
    if out.exists():
        raise ValueError("Provenance already exists")
    data = dict(schema=1, status="OPEN", revision=sha, started=datetime.now(timezone.utc).isoformat(),
                inputs=snapshot(root, sha))
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


def seal(root, runs, out):
    data = json.loads(out.read_text(encoding="utf-8"))
    if data["status"] != "OPEN" or snapshot(root, data["revision"]) != data["inputs"]:
        raise ValueError("Campaign inputs changed or already sealed")
    results = {}
    for path in sorted(runs.glob("*/result.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        request = json.loads(path.with_name("run.json").read_text(encoding="utf-8"))
        scenario = Path(request["test"]["path"]).resolve().relative_to(root.resolve()).as_posix()
        if scenario not in data["inputs"] or request["test"]["id"] != result["id"]:
            raise ValueError("Unknown campaign scenario")
        stamp = datetime.fromisoformat(result["started_utc"].replace("Z", "+00:00"))
        if not datetime.fromisoformat(data["started"]) <= stamp <= datetime.now(timezone.utc):
            raise ValueError("Result outside campaign time window")
        results[path.relative_to(runs).as_posix()] = dict(sha256=digest(path.read_bytes()),
                                                       scenario=scenario, case=result["id"])
    if not results:
        raise ValueError("Campaign has no results")
    data.update(status="SEALED", results=results, finished=datetime.now(timezone.utc).isoformat())
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["begin", "seal"])
    parser.add_argument("--project", default=".")
    parser.add_argument("--runs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--revision")
    args = parser.parse_args()
    root, runs, out = Path(args.project).resolve(), Path(args.runs).resolve(), Path(args.out).resolve()
    if args.operation == "begin":
        begin(root, args.revision, runs, out)
    else:
        seal(root, runs, out)


if __name__ == "__main__":
    main()
