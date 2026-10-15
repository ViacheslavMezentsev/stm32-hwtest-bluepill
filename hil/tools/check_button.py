"""Host-проверка подавления дребезга; MCU и GDB не нужны."""
from pathlib import Path
import os
import shutil
import subprocess

root = Path(__file__).resolve().parents[2]
out = root / "build" / "button-host"
out.mkdir(parents=True, exist_ok=True)
compiler = shutil.which("g++")
if not compiler:
    raise SystemExit("Нужен host g++ (не arm-none-eabi-g++)")
exe = out / ("check_button.exe" if os.name == "nt" else "check_button")
subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-static-libgcc", "-static-libstdc++",
                "-I" + str(root / "src"), str(root / "hil/tools/check_button.cpp"),
                str(root / "src/button.cpp"), "-o", str(exe)], check=True)
subprocess.run([str(exe)], check=True)
print("PASS button: debounce boundary, bounce, hold, release, second press and clock wrap")
