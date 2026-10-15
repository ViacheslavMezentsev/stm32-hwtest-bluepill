"""Регрессии HTML: ссылки/экранирование и отказ при изменённом свидетельстве."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ReportTests(unittest.TestCase):
    def test_evidence_and_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "hil/common/tests/board"
            scripts.mkdir(parents=True)
            (scripts / "test_example.py").write_text('@case("HW_DEMO")\ndef example(t): pass\n')
            view = root / "view"
            view.mkdir()
            run = root / "runs/one"
            run.mkdir(parents=True)
            result = run / "result.json"
            check = '<img src=x onerror="alert(1)">'
            result.write_text(json.dumps({"id": "HW_DEMO", "mode": "hardware", "status": "PASS",
                "started_utc": "2026-10-15T00:00:00Z", "elf_sha256": "a" * 64,
                "checks": [{"name": check, "actual": 1, "expected": 1, "passed": True}]}))
            point = {"scenario": "HW_DEMO", "source": "src/main.cpp", "line": 1,
                "anchor": "start();", "check": check, "state": "CONFIRMED", "reason": "executed check",
                "evidence": {"path": str(result), "sha256": hashlib.sha256(result.read_bytes()).hexdigest()}}
            (view / "ddtt-evidence.json").write_text(json.dumps({"status": "EXPORTED", "elf_sha256": "a" * 64,
                "summary": {"CONFIRMED": 1}, "points": [point]}))
            command = [sys.executable, str(Path(__file__).with_name("ddtt_report.py")),
                       "--project", str(root), "--runs", str(root / "runs"), "--view", str(view)]
            good = subprocess.run(command, capture_output=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            html = (view / "index.html").read_text(encoding="utf-8")
            self.assertIn("&lt;img", html)
            self.assertNotIn("<img", html)
            self.assertIn("vscode://file/", html)
            self.assertIn("1 всего / 1 с этим ELF", html)
            result.write_text(result.read_text() + " ")
            bad = subprocess.run(command, capture_output=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("ERROR", (view / "index.html").read_text())
            self.assertNotIn("CONFIRMED", (view / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
