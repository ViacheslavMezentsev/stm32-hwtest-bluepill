#include "button.hpp"

ButtonState g_button = {};

void ButtonState::update( bool pressed, uint32_t now )
{
    if ( pressed != candidate )
    {
        candidate  = pressed;
        changed_ms = now;
    }
    // Беззнаковая разность сохраняет интервал при переполнении миллисекунд.
    if ( candidate == stable || now - changed_ms < kButtonDebounceMs )
    {
        return;
    }
    stable = candidate;
    if ( stable )
    {
        ++presses;
    }
}
