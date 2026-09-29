// Обработчики отказов Cortex-M3. Отдельные функции (а не общий Default_Handler), чтобы
// отладчик и stm32-gdbtest различали причину остановки.
extern "C" {
void HardFault_Handler()
{
    for ( ;; )
    {
    }
}

void MemManage_Handler()
{
    for ( ;; )
    {
    }
}

void BusFault_Handler()
{
    for ( ;; )
    {
    }
}

void UsageFault_Handler()
{
    for ( ;; )
    {
    }
}
}
