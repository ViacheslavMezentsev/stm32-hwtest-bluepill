import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import renode_ddtt as r

class EmulatorEvidence(unittest.TestCase):
    def points(self, checks, status='PASS'):
        mapping = {'environment':'emulator', 'points':[{'source':'src/main.cpp','anchor':'setup();','check':'main reached'}]}
        with patch.object(r, 'validate_point', return_value=6), patch.object(r, 'at_revision', return_value=b"check('main reached', True)\n"):
            return r.project(mapping, checks, status, 'a'*40, 'owner/repo', '2026-10-16T00:00:00+00:00')[0]

    def test_missing_is_unknown_and_omitted_from_lcov(self):
        points = self.points({})
        self.assertEqual(points[0]['state'], 'UNKNOWN')
        self.assertNotIn('DA:', r.formats({'points':points})[0])

    def test_error_discards_partial_green(self):
        self.assertEqual(self.points({'main reached':True}, 'ERROR')[0]['state'], 'UNKNOWN')

    def test_failed_assertion_is_zero(self):
        points = self.points({'main reached':False}, 'FAIL')
        self.assertIn('DA:6,0', r.formats({'points':points})[0])

    def test_boolean_required(self):
        with self.assertRaises(ValueError):
            self.points({'main reached':'false'})

    def test_annotation_escaping(self):
        command = r.annotation({'state':'FAILED','source':'src/a,b.cpp','line':3,'check':'x%\n::notice::bad'})
        self.assertIn('file=src/a%2Cb.cpp,line=3', command)
        self.assertIn('x%25%0A', command)
        self.assertNotIn('\n', command)

    def test_hardware_map_refused(self):
        with self.assertRaises(ValueError):
            r.project({'environment':'hardware'}, {}, 'PASS', 'a'*40, 'owner/repo', '')

if __name__ == '__main__':
    unittest.main()
