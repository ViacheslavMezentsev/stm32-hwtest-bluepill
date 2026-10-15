"""Публичный отчёт: утечки, привязка SHA, неизвестные исходы и очистка после ошибки."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from ddtt_pages import export, formats, line_state
from ddtt_provenance import begin, seal

ROOT = Path(__file__).resolve().parents[2]


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.view = self.root / "build/view"
        self.runs = self.root / "build/runs"
        self.out = self.root / "build/pages"
        self.provenance = self.root / "build/campaign.json"
        for path in (self.view, self.runs, self.root / "src", self.root / "hil/common/tests/board",
                     self.root / "modules/stm32-gdbtest/tools"):
            path.mkdir(parents=True, exist_ok=True)
        (self.root / "src/main.cpp").write_text('start(); // <script>alert(1)</script>\n', encoding="utf-8")
        self.scenario = self.root / "hil/common/tests/board/test_demo.py"
        self.scenario.write_text('@case("HW_DEMO")\ndef demo(t): pass\n', encoding="utf-8")
        template = dict(schema=1, points=[dict(source="src/main.cpp",
            anchor='start(); // <script>alert(1)</script>', scenario="HW_DEMO", check="expected check")])
        (self.root / "hil/ddtt-f103cb.template.json").write_text(json.dumps(template), encoding="utf-8")
        for args in [["init", "-q"], ["add", "src", "hil"], ["-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"]]:
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        self.sha = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        module_path = self.root / "modules/stm32-gdbtest/tools/ddtt_coverage.py"
        shutil.copyfile(ROOT / "modules/stm32-gdbtest/tools/ddtt_coverage.py", module_path)
        spec = importlib.util.spec_from_file_location("portable_fixture_core", module_path)
        self.core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.core)
        begin(self.root, self.sha, self.runs, self.provenance)
        self.result = self.runs / "one/result.json"
        self.result.parent.mkdir()
        self.data = dict(id="HW_DEMO", mode="hardware", status="PASS", started_utc="2099-01-01T00:00:00Z",
            elf_sha256="a" * 64, checks=[dict(name="expected check", passed=True,
                actual="C:/Users/Private/secret", expected="PROBE-SERIAL-PRIVATE")],
            backend={"serial": "PROBE-SERIAL-PRIVATE", "host": "10.9.8.7"},
            build_manifest={"inputs": [dict(file="src/main.cpp", sha256=hashlib.sha256(
                (self.root / "src/main.cpp").read_bytes()).hexdigest())]})
        # seal проверяет свежесть, поэтому дата берётся после begin.
        from datetime import datetime, timezone
        self.data["started_utc"] = datetime.now(timezone.utc).isoformat()
        self.result.write_text(json.dumps(self.data), encoding="utf-8")
        self.result.with_name("run.json").write_text(json.dumps(dict(test=dict(path=str(self.scenario), id="HW_DEMO"))), encoding="utf-8")
        seal(self.root, self.runs, self.provenance)
        self.mapping = dict(schema=1, elf_sha256="a" * 64, points=[dict(template["points"][0],
            source_sha256=self.data["build_manifest"]["inputs"][0]["sha256"])])
        self.core.export(self.root, self.mapping, [self.result], self.view)

    def generate(self, sha=None):
        export(self.root, self.view, self.runs, self.provenance, "owner/project", sha or self.sha, self.out)

    def test_portable_allowlist_and_revision(self):
        self.generate()
        self.assertEqual({p.name for p in self.out.iterdir()},
                         {"index.html", "public-data.json", "lcov.info", "coverage.xml", ".nojekyll"})
        combined = ''.join(p.read_text(encoding="utf-8") for p in self.out.iterdir())
        for private in [str(self.root), "C:/Users/Private", "PROBE-SERIAL-PRIVATE", "10.9.8.7", "file://", "vscode://", "result.json", "records.json"]:
            self.assertNotIn(private, combined)
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn("code-line CONFIRMED", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn(f"/blob/{self.sha}/src/main.cpp#L1", html)
        self.assertIn(f"/blob/{self.sha}/hil/common/tests/board/test_demo.py#L2", html)
        self.assertIn("SF:src/main.cpp", (self.out / "lcov.info").read_text())
        xml = ET.parse(self.out / "coverage.xml")
        self.assertEqual(xml.getroot().get("lines-valid"), "1")
        self.assertEqual(xml.find(".//class").get("filename"), "src/main.cpp")

    def test_tamper_invalidates_previous_output(self):
        self.generate()
        self.result.write_text(self.result.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "result changed"):
            self.generate()
        self.assertIn("ERROR", (self.out / "index.html").read_text())
        self.assertEqual((self.out / "lcov.info").read_text(), "")
        self.assertEqual((self.out / "public-data.json").read_text(), "")

    def test_changed_scenario_rejected(self):
        self.scenario.write_text(self.scenario.read_text() + "# changed\n")
        with self.assertRaisesRegex(ValueError, "differs from revision"):
            self.generate()

    def test_changed_source_rejected(self):
        (self.root / "src/main.cpp").write_text("changed();\n")
        with self.assertRaisesRegex(ValueError, "differs from revision"):
            self.generate()

    def test_changed_report_rejected(self):
        path = self.view / "ddtt-evidence.json"
        report = json.loads(path.read_text())
        report["points"][0]["state"] = "FAILED"
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "stale or altered"):
            self.generate()

    def test_unsealed_campaign_rejected(self):
        data = json.loads(self.provenance.read_text())
        data["status"] = "OPEN"
        self.provenance.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Sealed campaign"):
            self.generate()

    def test_formats_keep_unknown_separate(self):
        points = [dict(source="src/main.cpp", line=1, state="CONFIRMED"),
                  dict(source="src/main.cpp", line=1, state="UNKNOWN"),
                  dict(source="src/main.cpp", line=2, state="FAILED"),
                  dict(source="src/main.cpp", line=3, state="CONFIRMED")]
        self.assertEqual(line_state(points[:2]), "UNKNOWN")
        lcov, xml = formats(dict(points=points))
        self.assertNotIn("DA:1,", lcov)
        self.assertIn("DA:2,0", lcov)
        self.assertIn("DA:3,1", lcov)
        self.assertEqual(ET.fromstring(xml).get("lines-valid"), "2")

    def test_output_refuses_unrelated_files(self):
        self.out.mkdir()
        (self.out / "records.json").write_text("private")
        with self.assertRaisesRegex(ValueError, "unrelated"):
            self.generate()
        self.assertEqual((self.out / "records.json").read_text(), "private")

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for report interaction checks")
    def test_source_navigation(self):
        self.generate()
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8'),source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
function element(id,classes=[]){const set=new Set(classes);return {id,hidden:false,dataset:{},handlers:{},
classList:{contains:n=>set.has(n),toggle(n,v){v?set.add(n):set.delete(n);}},
addEventListener(n,f){this.handlers[n]=f;},setAttribute(){}};}
const file=element('file'),mapped=element('mapped'),theme=element('theme'),hint=element('hint');
file.value='file0';mapped.checked=false;
const sources=[element('file0'),element('file1')],panels=[element('f0l1'),element('f1l1')];
const buttons=[element('b0'),element('b1',['UNMAPPED'])];buttons[0].dataset.key='f0l1';buttons[1].dataset.key='f1l1';
const root={dataset:{}},ids={file,mapped,theme,hint};
const context={document:{documentElement:root,body:element('body'),getElementById:id=>ids[id],
querySelectorAll:s=>({'.source':sources,'.code-line.UNMAPPED':[buttons[1]],'.code-line':buttons,'aside section':panels}[s])},
window:{matchMedia:()=>({matches:true,addEventListener(){}})},localStorage:{getItem(){return null;},setItem(){}},
MutationObserver:class{observe(){}}};
vm.runInNewContext(source,context);
assert.equal(root.dataset.theme,'dark');assert.equal(sources[1].hidden,true);
file.value='file1';file.handlers.change();assert.equal(sources[0].hidden,true);assert.equal(sources[1].hidden,false);
mapped.checked=true;mapped.handlers.change();assert.equal(buttons[1].hidden,true);
buttons[0].handlers.click();assert.equal(panels[0].hidden,false);assert.equal(panels[1].hidden,true);
assert.equal(hint.hidden,true);assert.equal(buttons[0].classList.contains('selected'),true);
console.log('PASS source navigation');
"""
        result = subprocess.run([shutil.which("node"), "-e", script, str(self.out / "index.html")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
