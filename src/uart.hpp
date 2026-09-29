// USART1 (PA9 — TX), 115200 8N1, только передача.
#pragma once

#include <cstdint>

namespace uart
{
    void init();
    void write( const char* text );
    void writeInt( int32_t value );
}
