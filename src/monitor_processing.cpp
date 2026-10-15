#include "monitor.hpp"

MonitorState g_monitor = {};

float ScalarFilter::update( float measurement )
{
    if ( !initialized )
    {
        value       = measurement;
        variance    = 1.0F;
        initialized = true;
        return value;
    }
    // Предсказание дисперсии, затем коррекция по новому измерению.
    float predicted  = variance + 1.0F;
    float gain       = predicted / ( predicted + 4.0F );
    value           += gain * ( measurement - value );
    variance         = ( 1.0F - gain ) * predicted;
    return value;
}

namespace monitor
{
    bool process( const volatile uint16_t* data, uint32_t count )
    {
        if ( data == nullptr || count != kMonitorWords )
        {
            ++g_monitor.rejected;
            return false;
        }
        uint32_t reference   = 0;
        uint32_t temperature = 0;
        // Сначала валидируем весь блок: отвергнутый хвост не должен менять фильтр.
        for ( uint32_t i = 0; i < count; i += 2 )
        {
            uint32_t r = data[i];
            uint32_t t = data[i + 1];
            if ( r == 0 || r > 4095 || t > 4095 )
            {
                ++g_monitor.rejected;
                return false;
            }
            reference   += r;
            temperature += t;
        }
        // Типовые значения, как у POST; индивидуальная калибровка F103 здесь отсутствует.
        float average_reference   = static_cast<float>( reference ) / 8.0F;
        float average_temperature = static_cast<float>( temperature ) / 8.0F;
        float vdda                = 1200.0F * 4095.0F / average_reference;
        float temp                = 25.0F + ( 1430.0F - average_temperature * vdda / 4095.0F ) / 4.3F;
        g_monitor.vdda_mv         = g_monitor.voltage.update( vdda );
        g_monitor.temp_c          = g_monitor.temperature.update( temp );
        g_monitor.normal =
            g_monitor.vdda_mv >= 2900.0F && g_monitor.vdda_mv <= 3600.0F && g_monitor.temp_c >= -10.0F && g_monitor.temp_c <= 85.0F;
        ++g_monitor.accepted;
        return true;
    }
}
