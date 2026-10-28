"""Пошаговый проход одного сценария stm32-gdbtest в отладчике VS Code (debugpy).

Сценарий запускается штатным runner модуля, как задача «один тест»: образ, проверка
идентичности, подготовка и восстановление платы те же. Python внутри GDB до подключения
к MCU открывает debugpy на 127.0.0.1:<port> и ждёт VS Code («Сценарий: подключиться
(debugpy)», F5). Затем работают точки останова в файле сценария, шаги, Variables, Watch
и Debug Console (`t.read("g_app")` и т. п.). Сам сценарий и его `timeout_s` не меняются:
режим выбирает только этот запуск, CTest и CI выполняют сценарий как обычно.

Модуль 0.6.0 и новее (`run --interactive`): без ограничения по времени, Ctrl+C отменяет
запуск, результаты в build/<пресет>/hwtest/interactive-runs. Модуль 0.5.x: тот же проход
через хук PYTHONUSERBASE, весь запуск ограничен --timeout (до 300 с), результаты в
hwtest/manual-runs. В обоих случаях ручной результат — диагностика: он не попадает в
hwtest/runs, сводку results.py, CTest и DDTT.

  python hil/tools/debug_scenario.py --build build/f103c8-hil --test HW_BLINK \\
      --stand hil/F103C8/stands/local.toml
"""
import argparse
import glob
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ANNOUNCE = "Interactive: attach the debugger to 127.0.0.1:%d"

# Только для модуля 0.5.x: usercustomize.py для Python внутри GDB-агента сценария.
HOOK = '''import os
import sys

_port = os.environ.get("STM32_GDBTEST_DEBUGPY_PORT")
if _port and os.environ.get("STM32_GDBTEST_RUN"):
    sys.path.insert(0, os.environ["STM32_GDBTEST_DEBUGPY"])
    import debugpy
    debugpy.listen(("127.0.0.1", int(_port)), in_process_debug_adapter=True)
    open(os.environ["STM32_GDBTEST_DEBUGPY_READY"], "w").close()
    debugpy.wait_for_client()
'''


def debugpy_libs(explicit):
    if explicit:
        return Path(explicit).resolve()
    found = []
    for root in (".vscode", ".vscode-server", ".vscode-insiders"):
        found += glob.glob(str(Path.home() / root / "extensions" / "ms-python.debugpy-*" / "bundled" / "libs"))
    if not found:
        sys.exit("debugpy не найден: установите расширение VS Code ms-python.debugpy или укажите --debugpy")
    version = lambda path: [int(part) for part in path.split("debugpy-")[1].split("-")[0].split(".") if part.isdigit()]
    return Path(sorted(found, key=version)[-1])


def legacy_command(args, base):
    """Модуль без `run --interactive`: отдельная копия сессии, хук через PYTHONUSERBASE, предел --timeout."""
    session = json.loads((args.build / "hwtest/session.json").read_text(encoding="utf-8"))
    manual = (args.build / "hwtest/manual").resolve()
    manual.mkdir(parents=True, exist_ok=True)
    session["out"] = str((args.build / "hwtest/manual-runs").resolve())
    (manual / "session.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
    ready = manual / "debugger-ready"
    ready.unlink(missing_ok=True)
    env = dict(os.environ, STM32_GDBTEST_DEBUGPY_PORT=str(args.port), STM32_GDBTEST_DEBUGPY_READY=str(ready),
               STM32_GDBTEST_DEBUGPY=str(debugpy_libs(args.debugpy)), PYTHONUSERBASE=str(manual / "userbase"))
    probe = subprocess.run([session["gdb"], "-nx", "-batch", "-q", "-ex",
                            "python import site; print(site.ENABLE_USER_SITE, site.getusersitepackages())"],
                           env=env, capture_output=True, text=True)
    enabled, _, site_dir = probe.stdout.strip().partition(" ")
    if enabled != "True":
        sys.exit("Python в GDB не читает пользовательский каталог site:\n" + probe.stdout + probe.stderr)
    Path(site_dir).mkdir(parents=True, exist_ok=True)
    (Path(site_dir) / "usercustomize.py").write_text(HOOK, encoding="utf-8")
    print("Модуль без run --interactive: весь запуск ограничен %g с; результат в %s" % (args.timeout, session["out"]),
          flush=True)
    command = base(manual / "session.json") + ["--timeout", str(args.timeout)]
    return command, env, ready


def announce_when_ready(ready, port, process):
    while process.poll() is None:
        if ready.exists():
            print(ANNOUNCE % port, flush=True)
            return
        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", type=Path, required=True, help="каталог сборки HIL-пресета, например build/f103c8-hil")
    parser.add_argument("--test", required=True, help="ID сценария, например HW_BLINK")
    parser.add_argument("--stand", type=Path, required=True, help="файл стенда")
    parser.add_argument("--port", type=int, default=5678, help="порт debugpy на 127.0.0.1 (по умолчанию 5678)")
    parser.add_argument("--debugpy", help="каталог с пакетом debugpy (по умолчанию из расширения VS Code)")
    parser.add_argument("--timeout", type=float, default=300, help="только для модуля 0.5.x: предел запуска, с")
    parser.add_argument("--gdbtest", type=Path, default=Path("modules/stm32-gdbtest"), help="путь к модулю")
    args = parser.parse_args()

    if not (args.build / "hwtest/session.json").exists():
        sys.exit("нет %s: сначала соберите HIL-пресет" % (args.build / "hwtest/session.json"))
    base = lambda session: [sys.executable, "-B", str(args.gdbtest / "stm32_gdbtest/cli.py"), "run", "--session",
                            str(session), "--test", args.test, "--stand", str(args.stand.resolve()),
                            "--identity-policy", "strict"]
    if (args.gdbtest / "stm32_gdbtest/interactive.py").exists():
        command = base(args.build / "hwtest/session.json") + ["--interactive", "--debug-port", str(args.port)]
        command += ["--debugpy", args.debugpy] if args.debugpy else []
        return subprocess.call(command)
    command, env, ready = legacy_command(args, base)
    process = subprocess.Popen(command, env=env)
    threading.Thread(target=announce_when_ready, args=(ready, args.port, process), daemon=True).start()
    return process.wait()


if __name__ == "__main__":
    sys.exit(main())
