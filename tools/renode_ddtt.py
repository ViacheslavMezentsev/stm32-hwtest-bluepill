"""Свежая сборка, Renode/GDB и отдельный переносимый DDTT, без доступа к стендам."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'hil/tools'))
from ddtt_guard import validate_point
from ddtt_pages import FILES, formats, github, render
from ddtt_provenance import at_revision, digest, git, revision
from renode_smoke import find_renode, resc_path, RENODE_CONFIG


def capture_inputs(sha):
    paths = git(ROOT, 'ls-files', 'src', 'cmsis', 'ld', 'cmake', 'emu/renode', 'tools',
                'CMakeLists.txt', 'hil/ddtt-renode.template.json', 'hil/tools/ddtt_pages.py',
                'hil/tools/ddtt_pages.css', 'hil/tools/ddtt_theme.js', 'hil/tools/ddtt_guard.py',
                'hil/tools/ddtt_provenance.py').decode().splitlines()
    return {name: digest(at_revision(ROOT, sha, name)) for name in paths}


def annotation(point):
    # Экранирование protocol workflow commands, а не shell/HTML.
    def esc(text, prop=False):
        text = str(text).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        return text.replace(':', '%3A').replace(',', '%2C') if prop else text
    level = {'CONFIRMED': 'notice', 'FAILED': 'error', 'UNKNOWN': 'warning'}[point['state']]
    return (f'::{level} file={esc(point["source"], True)},line={point["line"]},title=DDTT emulator::'
            + esc(point['state'] + ': ' + point['check']))


def project(mapping, checks, status, sha, repository, stamp):
    if mapping['environment'] != 'emulator':
        raise ValueError('Expected separate emulator map')
    points, sources = [], {}
    script = at_revision(ROOT, sha, 'tools/renode_gdb_checks.py').decode('utf-8-sig').splitlines()
    for entry in mapping['points']:
        number = validate_point(ROOT, entry)
        name = entry['check']
        value = checks.get(name)
        if value is not None and type(value) is not bool:
            raise ValueError('Check verdict must be boolean')
        # Незавершённая попытка не выдаёт зелёную карту по промежуточным наблюдениям.
        state = 'UNKNOWN' if status == 'ERROR' or value is None else ('CONFIRMED' if value else 'FAILED')
        locations = [i + 1 for i, line in enumerate(script) if f"check('{name}'," in line]
        scenario_path = 'tools/renode_gdb_checks.py'
        if name == 'UART banner':
            scenario_path = 'tools/renode_ddtt.py'
            text = at_revision(ROOT, sha, scenario_path).decode('utf-8-sig').splitlines()
            locations = [i + 1 for i, line in enumerate(text) if line.lstrip().startswith("checks['UART banner'] =")]
        if len(locations) != 1:
            raise ValueError('Ambiguous check location: ' + name)
        sources[entry['source']] = at_revision(ROOT, sha, entry['source']).decode('utf-8-sig').splitlines()
        points.append(dict(source=entry['source'], line=number, scenario='EMU_STARTUP', check=name,
                           state=state, checks_passed=int(value is True), checks_total=int(value is not None),
                           started_utc=stamp, source_url=github(repository, sha, entry['source'], number),
                           scenario_url=github(repository, sha, scenario_path, locations[0])))
    return points, sources


def stop(process):
    if process is None or process.poll() is not None:
        return
    # Завершаем только собственную группу/дерево, не чужие отладчики.
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=15)
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=15)


def run(args):
    sha = revision(ROOT, args.revision)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        raise ValueError('Expected owner/repository')
    out = (ROOT / args.out).resolve()
    if not out.is_relative_to(ROOT / 'build') or out == ROOT / 'build':
        raise ValueError('Output must be a separate build directory')
    out.mkdir(parents=True, exist_ok=True)
    if any(p.name not in FILES or not p.is_file() or p.is_symlink() for p in out.iterdir()):
        raise ValueError('Unrelated output files')
    for name in FILES:
        (out / name).write_text('', encoding='utf-8')
    (out / 'index.html').write_text('<p>DDTT emulator ERROR / incomplete</p>', encoding='utf-8')
    inputs = capture_inputs(sha)
    mapping = json.loads(at_revision(ROOT, sha, 'hil/ddtt-renode.template.json'))
    work = Path(tempfile.mkdtemp(prefix='renode-ddtt-', dir=ROOT / 'build'))
    print('Raw logs:', work, flush=True)
    renode = find_renode(args.renode)
    stamp = datetime.now(timezone.utc).isoformat()
    checks, status, server = {}, 'ERROR', None
    elf = work / 'firmware/stm32_hwtest_bluepill.elf'
    env = os.environ.copy()
    try:
        with (work / 'build.log').open('w', encoding='utf-8') as log:
            subprocess.run(['cmake', '-S', str(ROOT), '-B', str(elf.parent), '-G', 'Ninja',
                            '-DBOARD=F103CB_PB2', '-DCMAKE_BUILD_TYPE=Debug',
                            '-DBLUEPILL_HIL=OFF', '-DBLUEPILL_RENODE_TEST=OFF'],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
            subprocess.run(['cmake', '--build', str(elf.parent)], stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=120)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        config, script = work / 'renode.config', work / 'run.resc'
        config.write_text(RENODE_CONFIG, encoding='utf-8')
        script.write_text('mach create "ddtt"\n'
            + 'machine LoadPlatformDescription ' + resc_path(ROOT / 'emu/renode/stm32f103.repl') + '\n'
            + 'sysbus.usart1 CreateFileBackend ' + resc_path(work / 'uart.log') + ' true\n'
            + 'sysbus LoadELF ' + resc_path(elf) + '\n'
            + 'sysbus.cpu VectorTableOffset 0x08000000\n'
            + f'machine StartGdbServer {port}\n', encoding='utf-8')
        with (work / 'renode.log').open('w', encoding='utf-8') as log:
            server = subprocess.Popen([renode, '--disable-gui', '--console', '--plain', '--config', str(config),
                                       '--execute', 'include ' + resc_path(script)],
                                      stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=os.name != 'nt')
            deadline = time.monotonic() + 30
            while True:
                if server.poll() is not None or time.monotonic() > deadline:
                    raise TimeoutError('Renode readiness failed')
                # Готовность определяем по журналу; пробный TCP-клиент не занимает GDB-сеанс.
                if 'GDB server' in (work / 'renode.log').read_text(encoding='utf-8', errors='replace'):
                    break
                time.sleep(0.1)
            env.update(DDTT_GDB_PORT=str(port), DDTT_GDB_RESULT=str(work / 'gdb-result.json'))
            with (work / 'gdb.log').open('w', encoding='utf-8') as glog:
                result = subprocess.run([args.gdb, '-nx', '-batch', str(elf), '-ex',
                    'source ' + (ROOT / 'tools/renode_gdb_checks.py').as_posix()],
                    env=env, stdout=glog, stderr=subprocess.STDOUT, timeout=60)
            evidence = json.loads((work / 'gdb-result.json').read_text(encoding='utf-8'))
            if evidence['environment'] != 'emulator':
                raise ValueError('Unexpected evidence environment')
            checks = evidence['checks']
            status = evidence['status']
            if result.returncode and status != 'FAIL':
                status = 'ERROR'
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        status = 'ERROR'
    finally:
        stop(server)
    uart = work / 'uart.log'
    checks['UART banner'] = uart.is_file() and 'stm32-hwtest-bluepill F103CB_PB2' in uart.read_text(encoding='utf-8', errors='replace')
    if status != 'ERROR':
        status = 'PASS' if all(checks.get(p['check']) is True for p in mapping['points']) else 'FAIL'
    (work / 'result.json').write_text(json.dumps(dict(environment='emulator', status=status, checks=checks,
        revision=sha, inputs=inputs, started_utc=stamp), indent=2), encoding='utf-8')
    if capture_inputs(sha) != inputs:
        raise ValueError('Inputs changed during run')
    points, sources = project(mapping, checks, status, sha, args.repository, stamp)
    public = dict(schema=1, interpretation='DDTT selected assertions; not execution coverage',
                  environment='emulator (Renode; ADC/DMA not modeled)', repository=args.repository,
                  revision=sha, elf_sha256=digest(elf.read_bytes()) if elf.exists() else None,
                  campaign_attempts=1, status=status, points=points, summary=dict(Counter(p['state'] for p in points)))
    lcov, xml = formats(public)
    for name, data in [('index.html', render(public, sources)), ('public-data.json', json.dumps(public, indent=2)),
                       ('lcov.info', lcov), ('coverage.xml', xml)]:
        (out / name).write_text(data, encoding='utf-8')
    if args.annotations:
        for point in points:
            print(annotation(point))
    print(status, public['summary'], out / 'index.html')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write(f'## DDTT emulator: {status}\n\nRevision: `{sha}`. {public["summary"]}\n\n'
                          'Download **ddtt-renode-pages**, extract and open `index.html`. ADC/DMA are not modeled.\n')
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gdb', required=True)
    parser.add_argument('--renode')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--repository', default='ViacheslavMezentsev/stm32-hwtest-bluepill')
    parser.add_argument('--out', default='build/ddtt-renode-pages')
    parser.add_argument('--annotations', action='store_true')
    sys.exit(run(parser.parse_args()))
