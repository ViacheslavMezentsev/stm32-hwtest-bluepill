"""
RU: Загрузка: кристалл, размер Flash, тактирование и окружение прогона по описанию MCU и файлу данных платы.
EN: Boot: chip, flash size, clock and run environment against the MCU description and the board data file.
"""
from stm32_gdbtest import case, one_of, within


# HSI is the system clock after reset (RM0008: 8 MHz RC oscillator, PLL off).
HSI_HZ = 8_000_000
# DEV_ID of the STM32F10x medium-density line, F103x8 and F103xB (RM0008, DBGMCU_IDCODE).
DEV_ID_MEDIUM_DENSITY = 0x410
# RCC_CFGR address (RM0008: RCC base 0x40021000, offset 0x04); SWS is bits 3:2, 0 selects HSI.
RCC_CFGR = 0x40021004
# SRAM window of STM32F103 (20 KiB from 0x20000000).
SRAM = within(0x20000000, 0x20004FFF)
# USART1 data register: a peripheral address, never read as memory.
USART1_DR = 0x40013804


# Verify the chip and the clock at main() without CMSIS macros: addresses come from the MCU description.
@case("HW_BOOT", timeout_s=10, labels=("boot",))
def boot(t):
    profile = t.profile

    # The agent stopped in main() after reset; DEV_ID and F_SIZE are read where the description points.
    identity = profile["identity"]
    chip = t.evaluate(f"*(volatile unsigned int *)0x{identity['address']:08X}") & identity["mask"]
    t.check(f"DEV_ID 0x{chip:03X} matches {profile['mcu']}", chip, identity["value"])
    flash_kib = t.evaluate(f"*(volatile unsigned short *)0x{profile['flash_size_address']:08X}")
    t.check(f"F_SIZE {flash_kib} KiB covers the profile", flash_kib * 1024 >= profile["flash_size"])

    # SystemInit() leaves the HSI oscillator as the system clock.
    t.check("SYSCLK source is HSI", t.evaluate(f"(*(volatile unsigned int *)0x{RCC_CFGR:08X} >> 2) & 3"), 0)
    t.check("SystemCoreClock", t.read("SystemCoreClock"), HSI_HZ)


# The same boot state in terms of the device header, as the firmware code writes it.
@case("HW_BOOT_CMSIS", timeout_s=10, labels=("boot",), contracts=("cmsis_boot_macros",))
def boot_cmsis(t):
    # TECH-001: CMSIS macros are visible in board.cpp, the translation unit that includes stm32f1xx.h.
    t.reach("board::init")

    # Check the clock tree and the chip identity with the names of stm32f103xb.h.
    t.check([
        ("HSI ready", "RCC->CR & RCC_CR_HSIRDY"),
        ("PLL off", "RCC->CR & RCC_CR_PLLON", 0),
        ("SYSCLK source is HSI", "RCC->CFGR & RCC_CFGR_SWS", "RCC_CFGR_SWS_HSI"),
        ("DEV_ID medium density", "DBGMCU->IDCODE & DBGMCU_IDCODE_DEV_ID", DEV_ID_MEDIUM_DENSITY),
        ("factory flash size, KiB", "*(unsigned short *)FLASHSIZE_BASE", one_of(64, 128)),
        ("SystemCoreClock", "SystemCoreClock", HSI_HZ)
    ])


# Verify that the image, the board data and the build belong to the board the run configuration names.
@case("HW_BOARD_PROFILE", timeout_s=20, labels=("boot", "profile"))
def board_profile(t):
    profile = t.profile
    board = profile.data["board"]["board"]

    # TECH-018: the firmware names its board in a C string; TECH-017: the run names it in the board data.
    t.check(f"firmware is built for {board['name']}", t.evaluate("g_board_name", as_type=str), board["name"])
    t.check("the build defines the board", f"BOARD_{board['name']}" in profile.build["defines"])
    t.check("the board data comes from its file", profile.origin("data.board.board.name")["file"],
            profile.files["data.board"]["reference"])
    t.check("the frame limit comes from api.toml", profile.origin("api.frames.limit")["state"], "file")

    # The flashed image starts with a vector table: the initial stack lies in SRAM, reset in the flash.
    vectors = t.memory(profile["flash_start"], 8)
    stack, reset = int.from_bytes(vectors[:4], "little"), int.from_bytes(vectors[4:], "little")
    flash = within(profile["flash_start"], profile["flash_start"] + profile["flash_size"] - 1)
    t.check("initial stack pointer in SRAM", stack, SRAM)
    t.check("reset vector in the profile flash", reset & ~1, flash)
    t.check("reset vector is Thumb code", reset & 1)

    # TECH-012: a peripheral register is not read as memory, a read could change the device state.
    with t.refused("outside_window", name="USART1 data register is refused as memory"):
        t.memory(USART1_DR, 4)

    # The stand and GDB of this run are kept with the result.
    t.check("stand backend", profile.stand["backend"], one_of("jlink", "openocd", "stlink"))
    t.record("profile", profile)
