// POST: напряжение питания VDDA (по VREFINT) и температура кристалла через ADC1.
#pragma once

#include <cstdint>

enum PostStatus : uint32_t
{
    PostNotRun         = 0,
    PostOk             = 1,
    PostVddaOutOfRange = 2,
    PostTempOutOfRange = 3,
    PostAdcTimeout     = 4,
};

struct PostResult
{
    uint32_t vrefint_raw;
    uint32_t temp_raw;
    uint32_t vdda_mv;
    int32_t temp_c10;    // температура, десятые доли °C
    uint32_t status;     // PostStatus
};

extern PostResult g_post;

namespace post
{
    // Измеряет VREFINT и датчик температуры, заполняет g_post; true — значения в допустимых пределах.
    bool run();
}
