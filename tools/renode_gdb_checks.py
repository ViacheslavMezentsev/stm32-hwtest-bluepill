"""Проверки запуска внутри GDB; периферийные заглушки не считаются аппаратной проверкой."""
import json
import os
import traceback
import gdb

checks = {}

def check(name, value):
    checks[name] = bool(value)
    print(('PASS ' if value else 'FAIL ') + name)

def reach(symbol):
    # Временная точка: только основной поток GDB вызывает API отладчика.
    gdb.Breakpoint(symbol, temporary=True, internal=True)
    gdb.execute('continue')
    return gdb.newest_frame().name().removesuffix('()') == symbol.removesuffix('()')

try:
    gdb.execute('set pagination off')
    gdb.execute('set confirm off')
    gdb.execute('set remotetimeout 10')
    gdb.execute('target remote 127.0.0.1:' + os.environ['DDTT_GDB_PORT'])
    check('main reached', reach('main'))
    check('setup initially clear', int(gdb.parse_and_eval('g_app.setup_done')) == 0)
    check('setup reached', reach('setup()'))
    check('board init reached', reach('board::init()'))
    check('uart init reached', reach('uart::init()'))
    check('post reached', reach('post::run()'))
    check('loop reached', reach('loop()'))
    check('setup complete', int(gdb.parse_and_eval('g_app.setup_done')) == 1)
    check('model ADC timeout', bool(gdb.parse_and_eval('g_post.status == PostAdcTimeout')))
    status = 'PASS' if all(checks.values()) else 'FAIL'
except Exception:
    traceback.print_exc()
    status = 'ERROR'
finally:
    with open(os.environ['DDTT_GDB_RESULT'], 'w', encoding='utf-8') as stream:
        json.dump(dict(environment='emulator', status=status, checks=checks), stream)
    gdb.execute('quit ' + ('0' if status == 'PASS' else '1'))
