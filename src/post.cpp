#include "post.hpp"

#include "board.hpp"
#include "stm32f1xx.h"

PostResult g_post = {};

namespace
{
    // Типовые значения STM32F103 (datasheet DS5319): калибровок на кристалле нет.
    constexpr uint32_t kVrefIntMv = 1200;     // VREFINT, мВ
    constexpr int32_t kV25Mv10    = 14300;    // напряжение датчика при 25 °C, 0,1 мВ
    constexpr int32_t kSlopeUv    = 4300;     // наклон, мкВ/°C
    constexpr uint32_t kSamples   = 8;
    constexpr uint32_t kTimeoutMs = 10;

    constexpr uint32_t kChannelTemp    = 16;
    constexpr uint32_t kChannelVrefInt = 17;

    // Допустимые пределы POST.
    constexpr uint32_t kVddaMinMv = 2000;
    constexpr uint32_t kVddaMaxMv = 3700;
    constexpr int32_t kTempMinC10 = -400;
    constexpr int32_t kTempMaxC10 = 1250;

    bool convert( uint32_t channel, uint32_t& result )
    {
        uint32_t sum = 0;
        ADC1->SQR3   = channel;
        for ( uint32_t i = 0; i < kSamples; ++i )
        {
            ADC1->SR        = 0;
            ADC1->CR2      |= ADC_CR2_SWSTART;
            uint32_t start  = board::millis();
            while ( ( ADC1->SR & ADC_SR_EOC ) == 0 )
            {
                if ( board::millis() - start > kTimeoutMs )
                {
                    return false;
                }
            }
            sum += ADC1->DR & 0x0FFFU;
        }
        result = sum / kSamples;
        return true;
    }

    bool adcInit()
    {
        // ADCCLK = PCLK2 / 2 = 4 МГц (не более 14 МГц).
        RCC->CFGR     = ( RCC->CFGR & ~RCC_CFGR_ADCPRE ) | RCC_CFGR_ADCPRE_DIV2;
        RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
        ( void ) RCC->APB2ENR;

        // Датчик температуры и VREFINT, запуск программный (EXTSEL = SWSTART).
        ADC1->CR1 = 0;
        ADC1->CR2 = ADC_CR2_TSVREFE | ADC_CR2_EXTSEL | ADC_CR2_EXTTRIG | ADC_CR2_ADON;
        // Каналы 16 и 17: 239,5 такта (60 мкс при 4 МГц, требуется не менее 17,1 мкс).
        ADC1->SMPR1 = ADC_SMPR1_SMP16 | ADC_SMPR1_SMP17;
        ADC1->SQR1  = 0;
        // Стабилизация АЦП и запуск датчика температуры (не более 10 мкс).
        board::delayMs( 2 );

        ADC1->CR2      |= ADC_CR2_RSTCAL;
        uint32_t start  = board::millis();
        while ( ( ADC1->CR2 & ADC_CR2_RSTCAL ) != 0 )
        {
            if ( board::millis() - start > kTimeoutMs )
            {
                return false;
            }
        }
        ADC1->CR2 |= ADC_CR2_CAL;
        start      = board::millis();
        while ( ( ADC1->CR2 & ADC_CR2_CAL ) != 0 )
        {
            if ( board::millis() - start > kTimeoutMs )
            {
                return false;
            }
        }
        return true;
    }
}

namespace post
{
    bool run()
    {
        g_post = {};
        if ( !adcInit() || !convert( kChannelVrefInt, g_post.vrefint_raw ) || !convert( kChannelTemp, g_post.temp_raw ) ||
             g_post.vrefint_raw == 0 )
        {
            g_post.status = PostAdcTimeout;
            return false;
        }

        g_post.vdda_mv = kVrefIntMv * 4095U / g_post.vrefint_raw;
        // Vsense в 0,1 мВ; T = 25 + (V25 - Vsense) / наклон.
        int32_t vsense_mv10 = static_cast<int32_t>( g_post.temp_raw * g_post.vdda_mv * 10U / 4095U );
        g_post.temp_c10     = 250 + ( kV25Mv10 - vsense_mv10 ) * 1000 / kSlopeUv;

        if ( g_post.vdda_mv < kVddaMinMv || g_post.vdda_mv > kVddaMaxMv )
        {
            g_post.status = PostVddaOutOfRange;
        }
        else if ( g_post.temp_c10 < kTempMinC10 || g_post.temp_c10 > kTempMaxC10 )
        {
            g_post.status = PostTempOutOfRange;
        }
        else
        {
            g_post.status = PostOk;
        }

        // АЦП больше не нужен.
        ADC1->CR2 &= ~( ADC_CR2_ADON | ADC_CR2_TSVREFE );
        return g_post.status == PostOk;
    }
}
