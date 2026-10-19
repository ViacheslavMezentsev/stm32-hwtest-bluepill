"""
RU: Конфигурация периферии платы: вывод светодиода из файла данных платы и USART1.
EN: Board peripheral configuration: the LED pin from the board data file and USART1.
"""
from stm32_gdbtest import case


# PCLK2 is HSI: USART1 runs from 8 MHz, the divider is rounded (RM0008, USART_BRR).
PCLK2_HZ = 8_000_000


# Verify the LED pin that the board data file names: clock, 2 MHz push-pull output and g_led.
@case("HW_GPIO_CONFIG", timeout_s=10, labels=("gpio",), contracts=("cmsis_gpio_macros",))
def gpio_config(t):
    board = t.profile.data["board"]["board"]
    port, pin = board["led_port"], board["led_pin"]

    # Pins 0..7 are configured in CRL, pins 8..15 in CRH (RM0008, GPIO configuration registers).
    cr = "CRL" if pin < 8 else "CRH"

    # TECH-001: the macros are visible in board.cpp; the LED is set up by the time it first toggles.
    t.reach("board::ledToggle")

    # The pin expectations are built from the board data, so one scenario serves both boards.
    t.check(f"{port} clock enabled", t.mmio.read("RCC.APB2ENR") & t.evaluate(f"RCC_APB2ENR_IOP{port[-1]}EN"))
    t.check(f"P{port[-1]}{pin} 2 MHz push-pull output",
            t.mmio.read(f"{port}.{cr}") & t.evaluate(f"GPIO_{cr}_MODE{pin} | GPIO_{cr}_CNF{pin}"),
            t.evaluate(f"GPIO_{cr}_MODE{pin}_1"))

    # Проверяем опубликованное состояние отдельно от MMIO-снимка.
    t.check([
        ("g_led ODR address", "g_led.odr_address", f"(unsigned int)&{port}->ODR"),
        ("g_led pin mask", "g_led.mask", f"GPIO_ODR_ODR{pin}"),
        ("g_led active level", "g_led.active_high", int(board["led_active_high"]))
    ])


# Verify the USART1 transmitter that prints the board name and the POST result.
@case("HW_UART_CONFIG", timeout_s=10, labels=("uart",), contracts=("cmsis_uart_macros",))
def uart_config(t):
    baud = t.profile.data["board"]["uart"]["baud"]
    divider = (PCLK2_HZ + baud // 2) // baud
    t.reach("board::ledToggle")

    # SR может начать последовательность сброса флагов SR→DR; DR сценарий не читает.
    # setup() has printed its banner: the transmitter is idle with the last frame complete.
    t.check("USART1 and GPIOA clocks",
            t.mmio.read('RCC.APB2ENR') & (t.evaluate("RCC_APB2ENR_USART1EN | RCC_APB2ENR_IOPAEN")),
            t.evaluate("RCC_APB2ENR_USART1EN | RCC_APB2ENR_IOPAEN"))
    t.check("PA9 alternate push-pull 50 MHz",
            t.mmio.read('GPIOA.CRH') & (t.evaluate("GPIO_CRH_MODE9 | GPIO_CRH_CNF9")),
            t.evaluate("GPIO_CRH_MODE9 | GPIO_CRH_CNF9_1"))
    t.check(f"baud divider for {baud}", t.mmio.read('USART1.BRR'), divider)
    t.check("USART and transmitter enabled",
            t.mmio.read('USART1.CR1') & (t.evaluate("USART_CR1_UE | USART_CR1_TE")),
            t.evaluate("USART_CR1_UE | USART_CR1_TE"))
    t.check("receiver disabled", t.mmio.read('USART1.CR1') & t.evaluate('USART_CR1_RE'), 0)
    t.check("last frame complete", t.mmio.read('USART1.SR', allow_effects=True) & t.evaluate('USART_SR_TC'))
