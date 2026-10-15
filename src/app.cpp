#include "app.hpp"

#include "board.hpp"
#include "button.hpp"
#include "post.hpp"
#include "monitor.hpp"
#include "uart.hpp"

AppState g_app = {};

namespace
{
    void printPost()
    {
        uart::write( "POST: VDDA=" );
        uart::writeInt( static_cast<int32_t>( g_post.vdda_mv ) );
        uart::write( " mV, T=" );
        int32_t whole = g_post.temp_c10 / 10;
        int32_t tenth = g_post.temp_c10 % 10;
        if ( g_post.temp_c10 < 0 && whole == 0 )
        {
            uart::write( "-" );
        }
        uart::writeInt( whole );
        uart::write( "." );
        uart::writeInt( tenth < 0 ? -tenth : tenth );
        uart::write( g_post.status == PostOk ? " C, OK\r\n" : " C, FAIL\r\n" );
    }
}

void setup()
{
    board::init();
    uart::init();
    uart::write( "\r\nstm32-hwtest-bluepill " );
    uart::write( board::name() );
    uart::write( "\r\n" );

    post::run();
    printPost();

    g_app.last_toggle_ms = board::millis();
    g_app.setup_done     = 1;
}

void loop()
{
    uint32_t now = board::millis();
    g_button.update( board::buttonPressed(), now );
    // Удержание KEY и отказ включают LED постоянно; отпускание возвращает индикацию измерений.
    g_app.indication = g_monitor.state;
    if ( g_button.stable || g_app.indication == MeasurementFault )
    {
        board::ledSet( true );
    }
    else if ( g_app.indication == MeasurementPending )
    {
        board::ledSet( false );
    }
    else if ( now - g_app.last_toggle_ms >= kBlinkHalfPeriodMs )
    {
        g_app.last_toggle_ms = now;
        board::ledToggle();
        ++g_app.blink_count;
    }
    // Новый результат будет показан в следующем проходе loop, без ожидания DMA.
    monitor::poll();
}
