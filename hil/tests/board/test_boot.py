"""Загрузка: DEV_ID и тактирование от HSI 8 МГц (общий для F103C8_PC13 и F103CB_PB2)."""
from stm32_gdbtest import case

# RCC_CFGR STM32F1 (RM0008): база RCC 0x40021000, CFGR +0x04, SWS — биты 3:2 (0 — HSI).
RCC_CFGR = "*(unsigned int *)0x40021004"


@case("HW_BOOT", timeout_s=10, labels=("boot",))
def boot(t):
    # До вызова агент уже сбросил MCU, сверил DEV_ID с hil/profiles/<BOARD>.toml
    # (политика strict в пресетах: несовпадение даёт ERROR) и остановился в main().
    t.check("SYSCLK source is HSI", t.value(f"({RCC_CFGR} >> 2) & 3"), 0)
    t.check("SystemCoreClock", t.value("SystemCoreClock"), 8000000)
