// Подавление дребезга без привязки к GPIO и ожиданий внутри основного цикла.
#pragma once
#include <cstdint>

constexpr uint32_t kButtonDebounceMs = 30;

struct ButtonState
{
    bool candidate;
    bool stable;
    uint32_t changed_ms;
    uint32_t presses;

    // Одно событие на устойчивое нажатие; отпускание лишь разрешает следующее.
    void update( bool pressed, uint32_t now );
};

extern ButtonState g_button;
