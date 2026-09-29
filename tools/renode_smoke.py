"""Дымовой тест прошивки в эмуляторе Renode (без платы).

Модель emu/renode/stm32f103.repl: Cortex-M3, Flash, SRAM, SysTick и USART1; остальная
периферия — заглушки из RAM (АЦП не моделируется, POST печатает FAIL). Проверяется:
  - UART: строка «stm32-hwtest-bluepill <BOARD>» и строка POST;
  - g_app.setup_done = 1 (setup() завершилась);
  - g_app.blink_count >= 2 (loop() переключает светодиод раз в 500 мс).

  python tools/renode_smoke.py --elf build/Debug_F103C8/stm32_hwtest_bluepill.elf --board F103C8_PC13

Renode: --renode, иначе RENODE_BINARY, PATH, %ProgramFiles%/Renode/renode.exe.
nm: --nm, иначе ARM_TOOLCHAIN_ROOT/bin, PATH. Код возврата 0 — PASS, 1 — FAIL, 2 — ошибка запуска.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "emu/renode/stm32f103.repl"
# Как в stm32-cmake-yml: синхронный журнал Renode 1.16.1 не теряет записи.
RENODE_CONFIG = "[general]\nuse-synchronous-logging = True\ncollapse-repeated-log-entries = False\n"


def find_renode(explicit):
    candidates = [explicit, os.environ.get("RENODE_BINARY"), shutil.which("renode")]
    if os.name == "nt":
        candidates.append(str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Renode/renode.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
        if candidate == explicit and explicit:
            sys.exit(f"Renode not found: {explicit}")
    sys.exit("Renode not found: install Renode 1.16.1 or set RENODE_BINARY")


def find_nm(explicit):
    suffix = ".exe" if os.name == "nt" else ""
    root = os.environ.get("ARM_TOOLCHAIN_ROOT")
    for candidate in (explicit, root and str(Path(root) / "bin" / ("arm-none-eabi-nm" + suffix)),
                      shutil.which("arm-none-eabi-nm")):
        if candidate and Path(candidate).is_file():
            return candidate
    sys.exit("arm-none-eabi-nm not found: set ARM_TOOLCHAIN_ROOT or --nm")


def resc_path(path):
    value = Path(path).resolve().as_posix()
    if any(c in value for c in ('"', "\n", "\r")):
        sys.exit("Unsupported path for a Renode script: " + value)
    return "@" + value.replace(" ", "\\ ")


def symbol(nm, elf, name):
    output = subprocess.run([nm, str(elf)], check=True, capture_output=True, text=True).stdout
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == name:
            return int(parts[0], 16)
    sys.exit(f"Symbol {name} not found in {elf}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--board", required=True, choices=("F103C8_PC13", "F103CB_PB2"))
    parser.add_argument("--renode")
    parser.add_argument("--nm")
    parser.add_argument("--time", default="1.3", help="виртуальное время, с (по умолчанию 1.3)")
    parser.add_argument("--out", type=Path, help="каталог журналов (по умолчанию <каталог ELF>/renode)")
    args = parser.parse_args()

    renode = find_renode(args.renode)
    g_app = symbol(find_nm(args.nm), args.elf, "g_app")
    out = (args.out or args.elf.parent / "renode").resolve()
    out.mkdir(parents=True, exist_ok=True)
    uart = out / "uart.log"
    uart.unlink(missing_ok=True)
    (out / "renode.config").write_text(RENODE_CONFIG, encoding="utf-8")
    script = out / "smoke.resc"
    script.write_text("\n".join([
        'mach create "bluepill"',
        f"machine LoadPlatformDescription {resc_path(MODEL)}",
        f"sysbus.usart1 CreateFileBackend {resc_path(uart)} true",
        f"sysbus LoadELF {resc_path(args.elf)}",
        f'emulation RunFor "{args.time}"',
        'log "SMOKE_SETUP_DONE"',
        f"sysbus ReadDoubleWord 0x{g_app:08X}",
        'log "SMOKE_BLINK_COUNT"',
        f"sysbus ReadDoubleWord 0x{g_app + 4:08X}",
        'log "SMOKE_COMPLETED"',
        "quit",
    ]) + "\n", encoding="utf-8")
    command = [renode, "--disable-gui", "--console", "--plain", "--config", str(out / "renode.config"),
               "--execute", "include " + resc_path(script)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        print("ERROR: Renode did not finish in 120 s")
        return 2
    log = result.stdout + result.stderr
    (out / "renode.log").write_text(log, encoding="utf-8")
    if "SMOKE_COMPLETED" not in log or "There was an error" in log:
        print(f"ERROR: Renode run failed, see {out / 'renode.log'}")
        return 2

    values = {}
    for name in ("SMOKE_SETUP_DONE", "SMOKE_BLINK_COUNT"):
        match = re.search(re.escape(name) + r"\s*\n\s*(0x[0-9A-Fa-f]+)", log)
        values[name] = int(match.group(1), 16) if match else None
    text = uart.read_text(encoding="utf-8", errors="replace") if uart.exists() else ""
    checks = [
        ("UART banner", f"stm32-hwtest-bluepill {args.board}" in text),
        ("UART POST line", "POST: VDDA=" in text),
        ("g_app.setup_done == 1", values["SMOKE_SETUP_DONE"] == 1),
        (f"g_app.blink_count >= 2 (got {values['SMOKE_BLINK_COUNT']})", (values["SMOKE_BLINK_COUNT"] or 0) >= 2),
    ]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    print("--- UART\n" + text.strip())
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
