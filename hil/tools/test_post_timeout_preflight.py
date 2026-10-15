"""Host: изменённые инструкции и неоднозначный DWARF запрещают инъекцию."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class PreflightTests(unittest.TestCase):
    def load_scenario(self, asm, pcs=(100,)):
        fake = SimpleNamespace(
            decode_line=lambda location: (None, [SimpleNamespace(pc=pc) for pc in pcs]),
            selected_frame=lambda: SimpleNamespace(architecture=lambda: SimpleNamespace(
                disassemble=lambda address, count: [dict(addr=100 + i * 2, asm=item)
                                                    for i, item in enumerate(asm)])))
        path = Path(__file__).resolve().parents[1] / "common/tests/board/test_post_timeout.py"
        spec = importlib.util.spec_from_file_location("post_timeout_vectors", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"gdb": fake, "stm32_gdbtest": SimpleNamespace(
                case=lambda *args, **kwargs: lambda function: function)}):
            spec.loader.exec_module(module)
        return module

    def test_accepts_expected_contracts(self):
        for mask, offset, branch in [(8, 8, "beq"), (4, 8, "beq"), (2, 0, "bne")]:
            asm = ["ldr r3, [pc, #44]", f"ldr r3, [r3, #{offset}]",
                   f"tst.w r3, #{mask}", f"{branch}.n 0x1234"]
            module = self.load_scenario(asm)
            address, register, _ = module.wait_point(
                "while ( ( ADC1->SR & ADC_SR_EOC ) == 0 )", mask, offset, branch)
            self.assertEqual((address, register), (104, "r3"))

    def test_rejects_instruction_changes(self):
        original = ["ldr r3, [pc, #44]", "ldr r3, [r3, #8]", "tst.w r3, #8", "beq.n 0x1234"]
        for index, replacement in enumerate(["mov r3, r0", "str r3, [r3, #8]", "tst.w r3, #4", "bne.n 0x1234"]):
            asm = original.copy()
            asm[index] = replacement
            module = self.load_scenario(asm)
            with self.assertRaises(RuntimeError):
                module.wait_point("while ( ( ADC1->CR2 & ADC_CR2_RSTCAL ) != 0 )", 8, 8, "beq")

    def test_rejects_ambiguous_dwarf(self):
        module = self.load_scenario([], (100, 102))
        with self.assertRaises(RuntimeError):
            module.wait_point("while ( ( ADC1->CR2 & ADC_CR2_RSTCAL ) != 0 )", 8, 8, "beq")
