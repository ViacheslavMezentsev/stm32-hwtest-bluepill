"""Проверка якорей DDTT: комментарий не является проверяемой строкой кода."""
import hashlib
import re

# Сначала распознаём литералы: // внутри строки не начинает комментарий.
TOKENS = re.compile(r'R"(?P<delimiter>[^ ()\\\t\r\n]{0,16})\(.*?\)(?P=delimiter)"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?(?:\*/|\Z)', re.S)


def code_lines(text):
    def strip(match):
        value = match.group()
        if value.startswith(('//', '/*')):
            return ''.join('\n' if c == '\n' else ' ' for c in value)
        return value
    return [bool(line.strip()) for line in TOKENS.sub(strip, text).splitlines()]


def validate_point(root, point, bound=False):
    source = (root / point['source']).resolve()
    if not source.is_relative_to(root.resolve()):
        raise ValueError('DDTT source outside project')
    data = source.read_bytes()
    text = data.decode('utf-8-sig')
    lines = text.splitlines()
    if bound:
        number = point['line']
        if not isinstance(number, int) or not 1 <= number <= len(lines):
            raise ValueError(f'DDTT invalid line: {source}:{number}')
    else:
        found = [i + 1 for i, line in enumerate(lines) if line.strip() == point['anchor'].strip()]
        if len(found) != 1:
            raise ValueError(f'DDTT changed/ambiguous anchor: {source}: {point["anchor"]}')
        number = found[0]
    if not code_lines(text)[number - 1]:
        raise ValueError(f'DDTT comment or blank line: {source}:{number}')
    if lines[number - 1].strip() != point['anchor'].strip():
        raise ValueError(f'DDTT stale line/anchor: {source}:{number}; rebind map')
    if bound and hashlib.sha256(data).hexdigest() != point['source_sha256']:
        raise ValueError(f'DDTT changed source: {source}; rebind map and rerun evidence')
    return number
