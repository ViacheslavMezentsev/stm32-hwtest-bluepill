#include "monitor.hpp"
#include "board.hpp"
#include "stm32f1xx.h"

namespace
{
    constexpr uint32_t kPeriodMs  = 100;
    constexpr uint32_t kTimeoutMs = 10;

    // Остановить источник запросов и канал до передачи буфера процессору.
    void stopTransfer()
    {
        ADC1->CR2          &= ~( ADC_CR2_ADON | ADC_CR2_DMA | ADC_CR2_CONT | ADC_CR2_TSVREFE );
        DMA1_Channel1->CCR &= ~DMA_CCR_EN;
        __DSB();
        g_monitor.active = 0;
    }

    void init()
    {
        RCC->AHBENR  |= RCC_AHBENR_DMA1EN;
        RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
        ( void ) RCC->APB2ENR;
        // POST уже выполнил калибровку ADC. При его отказе монитор всё равно ограничен таймаутом.
        RCC->CFGR           = ( RCC->CFGR & ~RCC_CFGR_ADCPRE ) | RCC_CFGR_ADCPRE_DIV2;
        ADC1->CR1           = ADC_CR1_SCAN;
        ADC1->SMPR1         = ADC_SMPR1_SMP16 | ADC_SMPR1_SMP17;
        ADC1->SQR1          = ADC_SQR1_L_0;
        ADC1->SQR2          = 0;
        ADC1->SQR3          = 17U | ( 16U << 5 );
        DMA1_Channel1->CCR  = DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE;
        DMA1_Channel1->CPAR = reinterpret_cast<uint32_t>( &ADC1->DR );
        DMA1_Channel1->CMAR = reinterpret_cast<uint32_t>( &g_monitor.raw[0] );
        DMA1->IFCR          = DMA_IFCR_CGIF1;
        NVIC_ClearPendingIRQ( DMA1_Channel1_IRQn );
        NVIC_EnableIRQ( DMA1_Channel1_IRQn );
        g_monitor.initialized = 1;
    }
}

namespace monitor
{
    void arm()
    {
        // CNDTR меняем только у выключенного канала. Буфер принадлежит DMA до ready.
        DMA1_Channel1->CCR   &= ~DMA_CCR_EN;
        DMA1->IFCR            = DMA_IFCR_CGIF1;
        DMA1_Channel1->CNDTR  = kMonitorWords;
        g_monitor.ready       = 0;
        ADC1->CR2             = ADC_CR2_ADON | ADC_CR2_TSVREFE | ADC_CR2_DMA | ADC_CR2_CONT | ADC_CR2_EXTSEL | ADC_CR2_EXTTRIG;
        // Внутреннему датчику после включения нужно время стабилизации.
        board::delayMs( 2 );
        g_monitor.started_ms     = board::millis();
        g_monitor.last_start_ms  = g_monitor.started_ms;
        g_monitor.active         = 1;
        DMA1_Channel1->CCR      |= DMA_CCR_EN;
        ADC1->CR2               |= ADC_CR2_SWSTART;
    }

    void poll()
    {
        if ( !g_monitor.initialized )
        {
            init();
        }
        // На Cortex-M3 aligned word читается атомарно; IRQ публикует ready последним.
        if ( g_monitor.ready )
        {
            __DMB();
            process( g_monitor.raw, kMonitorWords );
            g_monitor.ready = 0;
        }
        uint32_t now = board::millis();
        if ( g_monitor.active && now - g_monitor.started_ms > kTimeoutMs )
        {
            // Исключаем завершение IRQ между проверкой таймаута и остановкой.
            uint32_t mask = __get_PRIMASK();
            __disable_irq();
            if ( g_monitor.active )
            {
                stopTransfer();
                DMA1->IFCR = DMA_IFCR_CGIF1;
                NVIC_ClearPendingIRQ( DMA1_Channel1_IRQn );
                ++g_monitor.timeouts;
            }
            __set_PRIMASK( mask );
        }
        if ( !g_monitor.active && !g_monitor.ready && now - g_monitor.last_start_ms >= kPeriodMs )
        {
            arm();
        }
    }
}

extern "C" void DMA1_Channel1_IRQHandler()
{
    uint32_t status = DMA1->ISR;
    stopTransfer();
    DMA1->IFCR = DMA_IFCR_CGIF1;
    if ( status & DMA_ISR_TEIF1 )
    {
        ++g_monitor.dma_errors;
        return;
    }
    if ( status & DMA_ISR_TCIF1 )
    {
        ++g_monitor.irq_count;
        __DMB();
        g_monitor.ready = 1;
    }
}
