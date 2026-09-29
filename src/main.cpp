// Точка входа: startup_stm32f103xb.s -> SystemInit() (HSI 8 МГц) -> main().
#include "app.hpp"

int main()
{
    setup();
    for ( ;; )
    {
        loop();
    }
}
