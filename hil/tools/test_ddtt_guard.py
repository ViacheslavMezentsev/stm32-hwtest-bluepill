"""Отрицательные контроли: комментарии, сдвиг строки и устаревший хеш."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from ddtt_guard import code_lines, validate_point


class GuardTests(unittest.TestCase):
    def test_comments_and_literals(self):
        self.assertEqual(code_lines('// comment\n/* start\n * body\n */\ncall(); // comment\nconst char *s="//text";\n\n'),
                         [False, False, False, False, True, True, False])
        self.assertEqual(code_lines('/* comment */ call();\n'), [True])
        self.assertEqual(code_lines('const char *s=R"(//text /*text*/)";\n'), [True])

    def test_bound_map_and_comment_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'main.cpp'
            source.write_text('// comment\nrun();\n')
            point = dict(source='main.cpp', anchor='run();', line=2,
                         source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(validate_point(root, point, True), 2)
            with self.assertRaisesRegex(ValueError, 'comment'):
                validate_point(root, dict(point, line=1), True)
            with self.assertRaisesRegex(ValueError, 'comment'):
                validate_point(root, dict(point, anchor='// comment'))
            source.write_text('// added\n// comment\nrun();\n')
            with self.assertRaises(ValueError):
                validate_point(root, point, True)
            with self.assertRaisesRegex(ValueError, 'changed source'):
                validate_point(root, dict(point, line=3), True)
