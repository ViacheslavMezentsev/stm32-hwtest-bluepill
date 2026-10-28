"""Пошаговый проход одного сценария stm32-gdbtest в отладчике VS Code (debugpy).

Сценарий запускается штатным runner модуля, как задача «один тест»: образ, проверка
идентичности, подготовка и восстановление платы те же. Python внутри GDB до подключения
к MCU открывает debugpy на 127.0.0.1:<port> и ждёт VS Code («Сценарий: подключиться
(debugpy)», F5). Затем работают точки останова в файле сценария, шаги, Variables, Watch
и Debug Console (`t.read("g_app")` и т. п.). Сам сценарий и его `timeout_s` не меняются:
режим выбирает только этот запуск, CTest и CI выполняют сценарий как обычно.

Используется `run --interactive` модуля (0.6.0 и новее): без ограничения по времени,
Ctrl+C отменяет запуск, результаты в build/<пресет>/hwtest/interactive-runs. Ручной
результат — диагностика: он не попадает в hwtest/runs, сводку results.py, CTest и DDTT.

  python hil/tools/debug_scenario.py --build build/f103c8-hil --test HW_BLINK \\
      --stand hil/F103C8/stands/local.toml
"""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--build", type=Path, required=True, help="каталог сборки HIL-пресета, например build/f103c8-hil")
    parser.add_argument("--test", required=True, help="ID сценария, например HW_BLINK")
    parser.add_argument("--stand", type=Path, required=True, help="файл стенда")
    parser.add_argument("--port", type=int, default=5678, help="порт debugpy на 127.0.0.1 (по умолчанию 5678)")
    parser.add_argument("--debugpy", help="каталог с пакетом debugpy (по умолчанию из расширения VS Code)")
    parser.add_argument("--gdbtest", type=Path, default=Path("modules/stm32-gdbtest"), help="путь к модулю")
    args = parser.parse_args()

    if not (args.build / "hwtest/session.json").exists():
        sys.exit("нет %s: сначала соберите HIL-пресет" % (args.build / "hwtest/session.json"))
    if not (args.gdbtest / "stm32_gdbtest/interactive.py").exists():
        sys.exit("модуль %s не поддерживает run --interactive (нужен 0.6.0 и новее): "
                 "выполните git submodule update --init" % args.gdbtest)
    command = [sys.executable, "-B", str(args.gdbtest / "stm32_gdbtest/cli.py"), "run",
               "--session", str(args.build / "hwtest/session.json"), "--test", args.test,
               "--stand", str(args.stand.resolve()), "--identity-policy", "strict",
               "--interactive", "--debug-port", str(args.port)]
    command += ["--debugpy", args.debugpy] if args.debugpy else []
    return subprocess.call(command)


if __name__ == "__main__":
    sys.exit(main())
