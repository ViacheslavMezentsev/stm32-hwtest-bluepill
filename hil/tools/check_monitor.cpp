// Проверяем реальную обработку на host без CMSIS и периферии.
#include "monitor.hpp"
#include <cassert>
#include <cmath>

int main()
{
    uint16_t block[kMonitorWords];
    for ( uint32_t i = 0; i < kMonitorWords; i += 2 )
    {
        block[i]     = 1500;
        block[i + 1] = 1800;
    }
    assert( monitor::process( block, kMonitorWords ) );
    assert( std::fabs( g_monitor.vdda_mv - 3276.0F ) < 0.01F );
    assert( std::fabs( g_monitor.temp_c - 22.6744186F ) < 0.001F );
    assert( g_monitor.normal == 1 );
    // Второй отсчёт: 3150 мВ, K=1/3, результат 3234 мВ.
    for ( uint32_t i = 0; i < kMonitorWords; i += 2 ) block[i] = 1560;
    assert( monitor::process( block, kMonitorWords ) );
    assert( std::fabs( g_monitor.vdda_mv - 3234.0F ) < 0.01F );
    float previous = g_monitor.voltage.value;
    assert( !monitor::process( nullptr, kMonitorWords ) );
    assert( !monitor::process( block, kMonitorWords - 1 ) );
    block[14] = 0;
    assert( !monitor::process( block, kMonitorWords ) );
    block[14] = 4096;
    assert( !monitor::process( block, kMonitorWords ) );
    assert( g_monitor.voltage.value == previous );
    assert( g_monitor.accepted == 2 && g_monitor.rejected == 4 );
    return 0;
}
