"""Сверка проектного SVD с CMSIS/DWARF в ELF, без target remote и доступа к плате."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--gdb", required=True)
    args = parser.parse_args()
    source = '''
import gdb, sys
from pathlib import Path
root = Path(ROOT)
sys.path.insert(0, str(root / "modules/stm32-gdbtest"))
from stm32_gdbtest.svd import parse
catalog = parse((root / "hil/common/stm32f103-test.svd").read_bytes())
gdb.execute("list SysTick_Handler", to_string=True)
for name, reg in catalog.registers.items():
    if name == "FACTORY.FLASH_SIZE":
        expr = "FLASHSIZE_BASE"
    else:
        peripheral, field = name.split(".")
        expr = "(unsigned int)&" + peripheral + "->" + field
    expansion = gdb.execute("macro expand " + expr, to_string=True).strip()
    expanded = expansion.split("expands to:", 1)[1].strip()
    address = int(gdb.parse_and_eval(expanded))
    assert address == reg.address, (name, hex(address), hex(reg.address))
    if name != "FACTORY.FLASH_SIZE":
        size_expr = "sizeof(" + peripheral + "->" + field + ")"
        expanded = gdb.execute("macro expand " + size_expr, to_string=True).split("expands to:", 1)[1].strip()
        assert int(gdb.parse_and_eval(expanded)) * 8 == reg.width, name
print("SVD_ELF_MATCH", len(catalog.registers))
'''.replace("Path(ROOT)", "Path(" + repr(str(ROOT)) + ")")
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "verify.gdb"
        script.write_text("set pagination off\npython\n" + source + "\nend\nquit\n", encoding="utf-8")
        result = subprocess.run([args.gdb, "-nx", "-batch", str(args.elf.resolve()), "-x", str(script)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=30, env={**os.environ, "PYTHONUTF8": "1"})
    print(result.stdout)
    if result.returncode or "SVD_ELF_MATCH " not in result.stdout or "Traceback" in result.stderr:
        raise RuntimeError(result.stderr or "SVD/ELF verification failed")


if __name__ == "__main__":
    main()
