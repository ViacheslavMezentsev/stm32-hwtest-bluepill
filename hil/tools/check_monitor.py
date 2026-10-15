"""Host-проверка той же C++ обработки; MCU и GDB не нужны."""
from pathlib import Path
import os
import shutil
import subprocess

root = Path(__file__).resolve().parents[2]
out = root / "build" / "monitor-host"
out.mkdir(parents=True, exist_ok=True)
compiler = shutil.which("g++")
if not compiler:
    raise SystemExit("Нужен host g++ (не arm-none-eabi-g++)")
exe = out / ("check_monitor.exe" if os.name == "nt" else "check_monitor")
subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-static-libgcc", "-static-libstdc++",
                "-I" + str(root / "src"), str(root / "hil/tools/check_monitor.cpp"),
                str(root / "src/monitor_processing.cpp"), "-o", str(exe)], check=True)
subprocess.run([str(exe)], check=True)
print("PASS monitor processing: initialization, second sample, invalid inputs and unchanged filter")
