#include "uart.hpp"

#include "stm32f1xx.h"

namespace uart
{
    void init()
    {
        RCC->APB2ENR |= RCC_APB2ENR_IOPAEN | RCC_APB2ENR_USART1EN;
        ( void ) RCC->APB2ENR;
        // PA9: альтернативная функция, двухтактный выход, 50 МГц.
        GPIOA->CRH = ( GPIOA->CRH & ~( GPIO_CRH_MODE9 | GPIO_CRH_CNF9 ) ) | GPIO_CRH_MODE9 | GPIO_CRH_CNF9_1;
        // PCLK2 = HSI 8 МГц: 8 000 000 / 115 200 = 69,4 -> BRR = 69 (ошибка скорости 0,6 %).
        USART1->BRR = ( SystemCoreClock + 57600U ) / 115200U;
        USART1->CR1 = USART_CR1_UE | USART_CR1_TE;
    }

    void write( const char* text )
    {
        while ( *text != '\0' )
        {
            while ( ( USART1->SR & USART_SR_TXE ) == 0 )
            {
            }
            USART1->DR = static_cast<uint8_t>( *text++ );
        }
        while ( ( USART1->SR & USART_SR_TC ) == 0 )
        {
        }
    }

    void writeInt( int32_t value )
    {
        char buffer[12];
        char* end          = buffer + sizeof( buffer );
        char* p            = end;
        *--p               = '\0';
        uint32_t magnitude = value < 0 ? 0U - static_cast<uint32_t>( value ) : static_cast<uint32_t>( value );
        do
        {
            *--p       = static_cast<char>( '0' + magnitude % 10U );
            magnitude /= 10U;
        } while ( magnitude != 0U );
        if ( value < 0 )
        {
            *--p = '-';
        }
        write( p );
    }
}
