"""Регрессии HTML: ссылки/экранирование и отказ при изменённом свидетельстве."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
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


class ThemeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to execute browser theme logic")
    def test_theme_cycle_storage_and_auto(self):
        # Выполняем настоящий JS с минимальным DOM: без внешней библиотеки и браузера.
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
function fixture(saved,blocked=false){
 const state={saved,classes:new Set(),systemDark:false};
 const root={dataset:{}},button={dataset:{},setAttribute(){},addEventListener(n,f){state.click=f;}};
 const media={get matches(){return state.systemDark;},addEventListener(n,f){state.change=f;}};
 const context={document:{documentElement:root,body:{classList:{contains:n=>state.classes.has(n)}},getElementById:()=>button},
 window:{matchMedia:()=>media},localStorage:{getItem(){if(blocked)throw Error();return state.saved;},setItem(k,v){if(blocked)throw Error();state.saved=v;}},
 MutationObserver:class{constructor(f){state.mutate=f;}observe(){}}};
 vm.runInNewContext(source,context);return {state,root,button};
}
let f=fixture(null);assert.equal(f.root.dataset.theme,'dark');
f.state.click();assert.equal(f.root.dataset.theme,'light');assert.equal(f.state.saved,'light');
f.state.click();assert.equal(f.button.dataset.mode,'auto');
f.state.systemDark=true;f.state.change();assert.equal(f.root.dataset.theme,'dark');
f.state.classes.add('vscode-light');f.state.mutate();assert.equal(f.root.dataset.theme,'light');
f.state.click();assert.equal(f.root.dataset.theme,'dark');
f.state.mutate();assert.equal(f.root.dataset.theme,'dark');
assert.equal(fixture('light').root.dataset.theme,'light');
assert.equal(fixture('garbage').root.dataset.theme,'dark');
f=fixture(null,true);f.state.click();assert.equal(f.root.dataset.theme,'light');
console.log('PASS theme: persistence, cycle, VS Code priority, explicit override, blocked storage');
"""
        result = subprocess.run([shutil.which("node"), "-e", script,
                                 str(Path(__file__).with_name("ddtt_theme.js"))], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
