#include <cstddef>
#include "stm32f1xx.h"
#include "board.hpp"

namespace
{
    volatile uint32_t g_ticks = 0;
}

// g_led читают и код, и сценарии HIL через GDB. volatile не даёт компилятору подставить
// константы вместо чтения: иначе --gc-sections удалит переменную из ELF (HW_BLINK: Missing ELF symbol).
#if defined( BOARD_F103C8_PC13 )
// Обычная Blue Pill: светодиод на PC13, горит при низком уровне.
const volatile LedInfo g_led = { GPIOC_BASE + offsetof( GPIO_TypeDef, ODR ), GPIO_ODR_ODR13, 0 };

/**
 * @brief Инициализировать пин светодиода.
 *
 */
static void ledPinInit()
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPCEN;
    ( void ) RCC->APB2ENR;
    GPIOC->BSRR = GPIO_BSRR_BS13;
    // Двухтактный выход, 2 МГц.
    GPIOC->CRH = ( GPIOC->CRH & ~( GPIO_CRH_MODE13 | GPIO_CRH_CNF13 ) ) | GPIO_CRH_MODE13_1;
}

const char g_board_name[] = "F103C8_PC13";
#elif defined( BOARD_F103CB_PB2 )
// WeAct BluePill-Plus v1.1: светодиод на PB2, горит при высоком уровне.
const volatile LedInfo g_led = { GPIOB_BASE + offsetof( GPIO_TypeDef, ODR ), GPIO_ODR_ODR2, 1 };

/**
 * @brief Инициализировать пин светодиода.
 *
 */
static void ledPinInit()
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPBEN;
    ( void ) RCC->APB2ENR;
    GPIOB->BRR = GPIO_BRR_BR2;
    // Двухтактный выход, 2 МГц.
    GPIOB->CRL = ( GPIOB->CRL & ~( GPIO_CRL_MODE2 | GPIO_CRL_CNF2 ) ) | GPIO_CRL_MODE2_1;
}

const char g_board_name[] = "F103CB_PB2";
#else
#error "Define BOARD_F103C8_PC13 or BOARD_F103CB_PB2"
#endif

namespace board
{
    /**
     * @brief Настроить периферию.
     *
     * Настроить тактирование, SysTick, светодиод и кнопку.
     */
    void init()
    {
        ledPinInit();

#if defined( BOARD_F103CB_PB2 )
        // SW2 через 330 Ом соединяет PA0 с 3,3 В. Без pull-down отпущенный вход плавает.
        RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
        ( void ) RCC->APB2ENR;
        GPIOA->BRR = GPIO_BRR_BR0;
        GPIOA->CRL = ( GPIOA->CRL & ~( GPIO_CRL_MODE0 | GPIO_CRL_CNF0 ) ) | GPIO_CRL_CNF0_1;
#endif

        SystemCoreClockUpdate();
        SysTick_Config( SystemCoreClock / 1000U );
    }

    /**
     * @brief Проверить, нажата ли кнопка.
     *
     * @return true, если кнопка нажата, false в противном случае.
     */
    bool buttonPressed()
    {
#if defined( BOARD_F103CB_PB2 )
        return ( GPIOA->IDR & GPIO_IDR_IDR0 ) != 0;
#else
        return false;
#endif
    }

    /**
     * @brief Включить или выключить светодиод.
     *
     * @param on true, если светодиод включён, false в противном случае.
     */
    void ledSet( bool on )
    {
        auto* gpio = reinterpret_cast<GPIO_TypeDef*>( g_led.odr_address - offsetof( GPIO_TypeDef, ODR ) );
        bool high  = ( on == ( g_led.active_high != 0 ) );
        gpio->BSRR = high ? g_led.mask : ( g_led.mask << 16 );
    }

    /**
     * @brief Проверить, включён ли светодиод.
     *
     * @return true, если светодиод включён, false в противном случае.
     */
    bool ledIsOn()
    {
        bool high = ( *reinterpret_cast<volatile uint32_t*>( g_led.odr_address ) & g_led.mask ) != 0;

        return high == ( g_led.active_high != 0 );
    }

    /**
     * @brief Переключить светодиод.
     *
     */
    void ledToggle()
    {
        ledSet( !ledIsOn() );
    }

    /**
     * @brief Получить количество миллисекунд, прошедших с момента запуска.
     *
     * @return Количество миллисекунд.
     */
    uint32_t millis()
    {
        return g_ticks;
    }

    /**
     * @brief Задержка на указанное количество миллисекунд.
     *
     * @param ms Количество миллисекунд.
     */
    void delayMs( uint32_t ms )
    {
        uint32_t start = g_ticks;

        while ( ( g_ticks - start ) < ms )
        {
        }
    }

    /**
     * @brief Получить имя платы.
     *
     * @return Имя платы.
     */
    const char* name()
    {
        return g_board_name;
    }
}

/**
 * @brief Обработчик прерывания SysTick.
 *
 * Увеличивает счётчик миллисекунд.
 */
extern "C" void SysTick_Handler()
{
    g_ticks = g_ticks + 1;
}
