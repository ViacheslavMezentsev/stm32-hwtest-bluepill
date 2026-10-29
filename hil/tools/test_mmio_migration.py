"""RU: Офлайн-контракт MMIO потребителя. EN: Consumer MMIO offline contract."""
import ast
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "modules/stm32-gdbtest"))
from stm32_gdbtest.mmio import MMIO, MMIOError
from stm32_gdbtest.records import Journal
from stm32_gdbtest.svd import parse

SCENARIOS = ROOT / "hil/common/tests/board"


def load(name):
    spec = importlib.util.spec_from_file_location("mmio_test_" + name, SCENARIOS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"gdb": SimpleNamespace()}):
        spec.loader.exec_module(module)
    return module


class MMIOTests(unittest.TestCase):
    def setUp(self):
        self.catalog = parse((ROOT / "hil/common/stm32f103-test.svd").read_bytes())
        self.transport = Mock()
        self.transport.write.return_value = None
        self.transport.read.return_value = b"\x01\x00\x00\x00"
        self.journal = Journal()
        self.mmio = MMIO(self.catalog, self.transport, self.journal.record)

    def test_addresses_widths_and_access(self):
        # Независимые числовые ожидания: RM0008, PM0056; CMSIS сверяется также по ELF.
        expected = {
            "RCC.CR": (0x40021000, 32), "RCC.CFGR": (0x40021004, 32),
            "RCC.AHBENR": (0x40021014, 32), "RCC.APB2ENR": (0x40021018, 32),
            "ADC1.CR2": (0x40012408, 32), "ADC1.DR": (0x4001244C, 32),
            "DMA1.ISR": (0x40020000, 32), "DMA1.IFCR": (0x40020004, 32),
            "DMA1_Channel1.CCR": (0x40020008, 32), "DMA1_Channel1.CNDTR": (0x4002000C, 32),
            "DMA1_Channel1.CPAR": (0x40020010, 32), "DMA1_Channel1.CMAR": (0x40020014, 32),
            "DBGMCU.IDCODE": (0xE0042000, 32), "FACTORY.FLASH_SIZE": (0x1FFFF7E0, 16), "SCB.ICSR": (0xE000ED04, 32),
            "SysTick.CTRL": (0xE000E010, 32), "SysTick.LOAD": (0xE000E014, 32)
        }
        for name, expected_value in expected.items():
            reg = self.catalog.registers[name]
            self.assertEqual((reg.address, reg.width), expected_value, name)
        for name in ("DMA1.ISR", "GPIOA.IDR", "FACTORY.FLASH_SIZE", "DBGMCU.IDCODE"):
            with self.subTest(name=name), self.assertRaises(MMIOError):
                self.mmio.write(name, 0)
        self.transport.write.assert_not_called()

    def test_svd_matches_both_target_identities(self):
        import tomllib
        for profile in ("F103C8", "F103CB"):
            target = tomllib.loads((ROOT / "hil" / profile / "target.toml").read_text(encoding="utf-8"))
            self.assertEqual(self.catalog.registers["DBGMCU.IDCODE"].address, target["identity"]["address"])
            self.assertEqual(self.catalog.registers["FACTORY.FLASH_SIZE"].address, target["flash_size_address"])

    def test_effects_require_consent_before_transport(self):
        for name in ("SysTick.CTRL", "USART1.SR", "ADC1.DR", "DMA1.IFCR"):
            with self.subTest(name=name), self.assertRaises(MMIOError):
                self.mmio.read(name)
        for name in ("ADC1.CR2", "DMA1.IFCR"):
            with self.subTest(name=name), self.assertRaises(MMIOError):
                self.mmio.write(name, 0)
        self.transport.read.assert_not_called()
        self.transport.write.assert_not_called()
        self.transport.prepare.assert_not_called()

    def test_effect_read_once_and_write_without_readback(self):
        self.assertEqual(self.mmio.read("SysTick.CTRL", allow_effects=True), 1)
        self.transport.read.assert_called_once()
        self.transport.reset_mock()
        ack = self.mmio.write("ADC1.CR2", 0x800000, allow_effects=True)
        self.assertFalse(ack["verified"])
        self.transport.read.assert_not_called()
        self.transport.write.assert_called_once()
        self.assertEqual(self.transport.write.call_args.args[-1], b"\x00\x00\x80\x00")

    def test_factory_halfword(self):
        self.transport.read.return_value = b"\x80\x00"
        self.assertEqual(self.mmio.read("FACTORY.FLASH_SIZE"), 128)
        self.assertEqual(self.transport.read.call_args.args[-2:], (0x1FFFF7E0, 2))

    def test_setup_reads_ctrl_once(self):
        t = Mock()
        t.mmio.read.side_effect = lambda name, **kw: 7 if name == "SysTick.CTRL" else 7999
        t.evaluate.side_effect = {"SysTick_CTRL_ENABLE_Msk": 1,
                                 "SysTick_CTRL_TICKINT_Msk": 2, "SysTick_CTRL_CLKSOURCE_Msk": 4}.__getitem__
        load("test_app").setup_done(t)
        reads = [c for c in t.mmio.read.call_args_list if c.args == ("SysTick.CTRL",)]
        self.assertEqual(len(reads), 1)
        self.assertEqual(reads[0].kwargs, {"allow_effects": True})

    def test_led_both_profiles_one_read(self):
        for name in ("test_app", "test_button", "test_dma", "test_indicator", "test_injection"):
            for port, pin, active in (("GPIOB", 2, True), ("GPIOC", 13, False)):
                for physical in (0, 1):
                    t = Mock()
                    t.profile.data = {"board": {"board": {"led_port": port}}}
                    t.read.side_effect = {"g_led.mask": 1 << pin, "g_led.active_high": active}.__getitem__
                    t.mmio.read.return_value = physical << pin
                    self.assertEqual(load(name).led_on(t), bool(physical) == active)
                    t.mmio.read.assert_called_once_with(port + ".ODR")

    def test_dma_exception_restores_only_bit_no_redundant_write(self):
        for current in (0x800001, 0x800101):
            t = Mock()
            t.evaluate.return_value = 0x100
            t.mmio.read.side_effect = [0x800101, current]
            t.reach.side_effect = [None, None, RuntimeError("lost next arm")]
            with self.assertRaisesRegex(RuntimeError, "lost next arm"):
                load("test_dma").dma_timeout(t)
            calls = t.mmio.write.call_args_list
            self.assertEqual(calls[0].args, ("ADC1.CR2", 0x800001))
            self.assertEqual(calls[0].kwargs, {"allow_effects": True})
            self.assertEqual(len(calls), 2 if current == 0x800001 else 1)
            if len(calls) == 2:
                self.assertEqual(calls[1].args, ("ADC1.CR2", 0x800101))
            t.write.assert_not_called()

    def test_dma_lost_ack_not_blindly_retried(self):
        t = Mock()
        t.evaluate.return_value = 0x100
        t.mmio.read.side_effect = [0x800101, 0x800101]
        t.mmio.write.side_effect = RuntimeError("unknown write outcome")
        with self.assertRaisesRegex(RuntimeError, "unknown write outcome"):
            load("test_dma").dma_timeout(t)
        self.assertEqual(t.mmio.write.call_count, 1)
        self.assertEqual(t.mmio.read.call_count, 2)

    def test_no_legacy_peripheral_data_expressions(self):
        # Проверяем аргументы API/таблиц, не строки-якоря C++ в тестах таймаутов.
        import re
        for path in SCENARIOS.glob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if not isinstance(node.func.value, ast.Name) or node.func.value.id != "t":
                    continue
                args = node.args if node.func.attr in ("read", "evaluate", "write") else []
                if node.func.attr == "check" and node.args and isinstance(node.args[0], ast.List):
                    args = [v for row in node.args[0].elts for v in row.elts[1:]]
                for arg in args:
                    if isinstance(arg, ast.JoinedStr):
                        text = ast.unparse(arg)
                        if "->" in text:
                            self.assertIn("&", text, path.name)
                        self.assertNotIn("unsigned int *)", text, path.name)
                        continue
                    for part in ast.walk(arg):
                        if isinstance(part, ast.Constant) and isinstance(part.value, str):
                            value = part.value
                            if "->" in value:
                                self.assertRegex(value, r"&\s*[\w{]", f"{path.name}: {value}")
                            self.assertNotRegex(value, r"\*\s*\(\s*(volatile )?unsigned", path.name)

    def test_literal_registers_exist(self):
        for path in SCENARIOS.glob("test_*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if ast.unparse(node.func) in ("t.mmio.read", "t.mmio.write"):
                        if isinstance(node.args[0], ast.Constant):
                            self.assertIn(node.args[0].value, self.catalog.registers)


if __name__ == "__main__":
    unittest.main()
