// Периодический монитор: DMA-блок из восьми пар и фильтрация в контексте main.
#pragma once
#include <cstdint>

constexpr uint32_t kMonitorWords = 16;

struct ScalarFilter
{
    float value;
    float variance;
    bool initialized;
    // Одномерный фильтр: Q=1, R=4; первый отсчёт становится начальным состоянием.
    float update( float measurement );
};

// Состояние последнего результата; счётчики ошибок не блокируют восстановление.
enum MeasurementState : uint32_t
{
    MeasurementPending,
    MeasurementNormal,
    MeasurementFault
};

struct MonitorState
{
    volatile uint16_t raw[kMonitorWords];
    volatile uint32_t ready;
    volatile uint32_t active;
    volatile uint32_t irq_count;
    volatile uint32_t dma_errors;
    uint32_t timeouts;
    uint32_t accepted;
    uint32_t rejected;
    uint32_t started_ms;
    uint32_t last_start_ms;
    uint32_t initialized;
    float vdda_mv;
    float temp_c;
    volatile uint32_t normal;
    volatile MeasurementState state;
    ScalarFilter voltage;
    ScalarFilter temperature;
};

extern MonitorState g_monitor;

namespace monitor
{
    // Не блокирует основной цикл ожиданием DMA; обрабатывает только законченный блок.
    void poll();
    // Чистая относительно периферии обработка; изменяет лишь g_monitor и фильтры.
    bool process( const volatile uint16_t* data, uint32_t count );
    // Запуск очередного конечного блока после завершения обработки предыдущего.
    void arm();
    // Отказ сбора/валидации отменяет прежнюю норму, не меняя фильтры.
    void invalidate();
}
