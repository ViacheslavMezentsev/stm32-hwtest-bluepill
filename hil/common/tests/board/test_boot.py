"""
RU: Загрузка: кристалл, размер Flash, тактирование и окружение прогона по описанию MCU и файлу данных платы.
EN: Boot: chip, flash size, clock and run environment against the MCU description and the board data file.
"""
from stm32_gdbtest import case, one_of, within


# HSI is the system clock after reset (RM0008: 8 MHz RC oscillator, PLL off).
HSI_HZ = 8_000_000
# DEV_ID of the STM32F10x medium-density line, F103x8 and F103xB (RM0008, DBGMCU_IDCODE).
DEV_ID_MEDIUM_DENSITY = 0x410
# SRAM of STM32F103: 20 KiB from 0x20000000. The stack is full descending, so the initial stack
# pointer may equal the end address: the first push stores below it (ld/stm32f103.ld.in, _estack).
SRAM_START, SRAM_END = 0x20000000, 0x20005000
# USART1 data register: a peripheral address, never read as memory.
USART1_DR = 0x40013804


# Идентификатор и размер Flash читаем через SVD; соответствие адресов профилю проверяется на host.
@case("HW_BOOT", timeout_s=10, labels=("boot",))
def boot(t):
    profile = t.profile

    # Агент остановился в main после сброса; ожидания берём из описания MCU.
    identity = profile["identity"]
    chip = t.mmio.read("DBGMCU.IDCODE") & identity["mask"]
    t.check(f"DEV_ID 0x{chip:03X} matches {profile['mcu']}", chip, identity["value"])
    flash_kib = t.mmio.read("FACTORY.FLASH_SIZE")
    t.check(f"F_SIZE {flash_kib} KiB covers the profile", flash_kib * 1024 >= profile["flash_size"])

    # SystemInit() leaves the HSI oscillator as the system clock.
    t.check("SYSCLK source is HSI", (t.mmio.read("RCC.CFGR") >> 2) & 3, 0)
    t.check("SystemCoreClock", t.read("SystemCoreClock"), HSI_HZ)


# The same boot state in terms of the device header, as the firmware code writes it.
@case("HW_BOOT_CMSIS", timeout_s=10, labels=("boot",), contracts=("cmsis_boot_macros",))
def boot_cmsis(t):
    # TECH-001: CMSIS macros are visible in board.cpp, the translation unit that includes stm32f1xx.h.
    t.reach("board::init")

    # Check the clock tree and the chip identity with the names of stm32f103xb.h.
    t.check("HSI ready", t.mmio.read('RCC.CR') & t.evaluate('RCC_CR_HSIRDY'))
    t.check("PLL off", t.mmio.read('RCC.CR') & t.evaluate('RCC_CR_PLLON'), 0)
    t.check("SYSCLK source is HSI",
            t.mmio.read('RCC.CFGR') & t.evaluate('RCC_CFGR_SWS'),
            t.evaluate("RCC_CFGR_SWS_HSI"))
    t.check("DEV_ID medium density",
            t.mmio.read('DBGMCU.IDCODE') & t.evaluate('DBGMCU_IDCODE_DEV_ID'),
            DEV_ID_MEDIUM_DENSITY)
    t.check("factory flash size, KiB", t.mmio.read("FACTORY.FLASH_SIZE"), one_of(64, 128))

    # Проверяем опубликованное состояние отдельно от MMIO-снимка.
    t.check([ ("SystemCoreClock", "SystemCoreClock", HSI_HZ) ])


# Verify that the image, the board data and the build belong to the board the run configuration names.
@case("HW_BOARD_PROFILE", timeout_s=20, labels=("boot", "profile"))
def board_profile(t):
    profile = t.profile
    board = profile.data["board"]["board"]

    # TECH-018: the firmware names its board in a C string; TECH-017: the run names it in the board data.
    # Units that see only the extern declaration give the array no bound, so it is read through a pointer.
    name = t.evaluate("(const char *)g_board_name", as_type=str)
    t.check(f"firmware is built for {board['name']}", name, board["name"])
    t.check("the build defines the board", f"BOARD_{board['name']}" in profile.build["defines"])
    t.check("the board data comes from its file", profile.origin("data.board.board.name")["file"],
            profile.files["data.board"]["reference"])
    t.check("the frame limit comes from api.toml", profile.origin("api.frames.limit")["state"], "file")

    # The flashed image starts with a vector table: the initial stack lies in SRAM, reset in the flash.
    vectors = t.memory(profile["flash_start"], 8)
    stack, reset = int.from_bytes(vectors[:4], "little"), int.from_bytes(vectors[4:], "little")
    flash = within(profile["flash_start"], profile["flash_start"] + profile["flash_size"] - 1)
    t.check("initial stack pointer in SRAM", stack, within(SRAM_START + 8, SRAM_END))
    t.check("initial stack pointer 8-byte aligned (AAPCS)", stack % 8, 0)
    t.check("reset vector in the profile flash", reset & ~1, flash)
    t.check("reset vector is Thumb code", reset & 1)

    # TECH-012: a peripheral register is not read as memory, a read could change the device state.
    with t.refused("outside_window", name="USART1 data register is refused as memory"):
        t.memory(USART1_DR, 4)

    # The stand and GDB of this run are kept with the result.
    t.check("stand backend", profile.stand["backend"], one_of("jlink", "openocd", "stlink"))
    t.record("profile", profile)
