// Точка входа: startup_stm32f103xb.s -> SystemInit() (HSI 8 МГц) -> main().
#include "app.hpp"

/**
 * @brief Точка входа.
 *
 * После запуска процессора и инициализации стека вызывается main().
 */
int main()
{
    setup();

    for ( ;; )
    {
        loop();
    }
}
