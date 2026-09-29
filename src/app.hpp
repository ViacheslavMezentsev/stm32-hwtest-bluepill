// Прикладная логика: setup() — один раз после сброса, loop() — в бесконечном цикле.
#pragma once

#include <cstdint>

struct AppState
{
    uint32_t setup_done;     // 1 после завершения setup()
    uint32_t blink_count;    // число переключений светодиода
    uint32_t last_toggle_ms;
};

extern AppState g_app;

// Период переключения светодиода: мигание 1 Гц.
constexpr uint32_t kBlinkHalfPeriodMs = 500;

void setup();
void loop();
