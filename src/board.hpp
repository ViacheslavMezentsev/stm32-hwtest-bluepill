// Плата: светодиод пользователя и системный тик 1 мс (HSI 8 МГц).
#pragma once

#include <cstdint>

// Описание светодиода для сценариев HIL: адрес GPIOx_ODR, маска вывода и активный уровень.
struct LedInfo
{
    uint32_t odr_address;
    uint32_t mask;
    uint32_t active_high;
};

extern const volatile LedInfo g_led;

// Имя платы (профиль сборки BOARD): его выводит UART, а сценарии HIL сверяют с файлом данных платы.
extern const char g_board_name[];

namespace board
{
    // Тактирование GPIO, вывод светодиода (выключен), SysTick 1 мс.
    void init();

    void ledSet( bool on );
    void ledToggle();
    bool ledIsOn();

    // Миллисекунды после board::init().
    uint32_t millis();
    void delayMs( uint32_t ms );

    const char* name();
}
