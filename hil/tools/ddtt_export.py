"""Свежая карта → проверенный LCOV → подробный HTML; старую раскраску не сохраняем при ошибке."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from ddtt_guard import validate_point


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', required=True)
    parser.add_argument('--elf', default='build/f103cb-hil/stm32_hwtest_bluepill.elf')
    parser.add_argument('--template', default='hil/ddtt-f103cb.template.json')
    parser.add_argument('--out', default='build/ddtt-view')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    view = (root / args.out).resolve()
    view.mkdir(parents=True, exist_ok=True)
    # Не даём ошибке привязки оставить старые зелёные строки.
    (view / 'lcov.info').write_text('', encoding='utf-8')
    (view / 'index.html').write_text('<meta charset="utf-8"><p>DDTT: generation incomplete / ERROR</p>', encoding='utf-8')
    template = root / args.template
    data = json.loads(template.read_text(encoding='utf-8'))
    for point in data['points']:
        validate_point(root, point)
    module = root / 'modules/stm32-gdbtest'
    commands = [
        [module / 'examples/ddtt-coverage/bind_map.py', '--project', root, '--elf', root / args.elf,
         '--template', template, '--out', view / 'map.json'],
        [module / 'tools/ddtt_coverage.py', '--project', root, '--map', view / 'map.json',
         '--runs', root / args.runs, '--out', view],
        [root / 'hil/tools/ddtt_report.py', '--project', root, '--runs', root / args.runs, '--view', view]
    ]
    try:
        for command in commands:
            subprocess.run([sys.executable, *map(str, command)], cwd=root, check=True)
    except Exception:
        (view / 'lcov.info').write_text('', encoding='utf-8')
        (view / 'index.html').write_text('<meta charset="utf-8"><p>DDTT export ERROR; see terminal</p>', encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
