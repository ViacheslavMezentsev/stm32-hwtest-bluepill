"""Загрузка, записанная через имена CMSIS (stm32f103xb.h) вместо адресов регистров.

Тот же смысл, что HW_BOOT, но выражения читаются как код прошивки: `RCC->CFGR & RCC_CFGR_SWS`.
GDB раскрывает макросы только в единице трансляции, которая включает stm32f1xx.h, и только в
сборке с -g3 (Debug, пресеты HIL_*). Поэтому сценарий сначала доходит до board::init()
(board.cpp), а наличие макросов в ELF заранее проверяет контракт cmsis_boot_macros
(hil/tests/contracts.json) — в prepare.HW_BOOT_CMSIS, без платы.
"""
from stm32_gdbtest import case


@case("HW_BOOT_CMSIS", timeout_s=10, labels=("boot",), contracts=("cmsis_boot_macros",))
def boot_cmsis(t):
    t.reach("board::init")
    t.check("HSI ready", t.value("(RCC->CR & RCC_CR_HSIRDY) != 0"), 1)
    t.check("PLL off", t.value("(RCC->CR & RCC_CR_PLLON) == 0"), 1)
    t.check("SYSCLK source is HSI", t.value("(RCC->CFGR & RCC_CFGR_SWS) == RCC_CFGR_SWS_HSI"), 1)
    t.check("DEV_ID medium density", t.value("DBGMCU->IDCODE & DBGMCU_IDCODE_DEV_ID"), 0x410)
    flash_kib = t.value("*(unsigned short *)FLASHSIZE_BASE")
    t.check(f"F_SIZE {flash_kib} KiB is 64 or 128", flash_kib in (64, 128), True)
    t.check("SystemCoreClock", t.value("SystemCoreClock"), 8000000)
