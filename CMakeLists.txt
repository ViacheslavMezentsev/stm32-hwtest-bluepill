cmake_minimum_required(VERSION 3.25)

# Toolchain GNU Arm (xPack 14.2.1) — до project().
if(NOT CMAKE_TOOLCHAIN_FILE)
    set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_SOURCE_DIR}/cmake/arm-gcc.cmake")
endif()

project(stm32_hwtest_bluepill VERSION 0.1.0 LANGUAGES C CXX ASM)

# Python ищется сначала по PATH, а не в реестре Windows: иначе FindPython может взять
# интерпретатор Visual Studio (например, 3.9) вместо установленного в PATH 3.11+.
set(Python3_FIND_REGISTRY LAST)

# =============================================================================
# Плата (профиль): F103C8_PC13 — обычная Blue Pill, F103CB_PB2 — WeAct BluePill-Plus.
# =============================================================================
set(BOARD "F103C8_PC13" CACHE STRING "Board profile")
set_property(CACHE BOARD PROPERTY STRINGS F103C8_PC13 F103CB_PB2)

if(BOARD STREQUAL "F103C8_PC13")
    set(BOARD_FLASH_SIZE 64K)
elseif(BOARD STREQUAL "F103CB_PB2")
    set(BOARD_FLASH_SIZE 128K)
else()
    message(FATAL_ERROR "Unknown BOARD=${BOARD}; use F103C8_PC13 or F103CB_PB2")
endif()
message(STATUS "Board: ${BOARD}, Flash ${BOARD_FLASH_SIZE}")

set(FLASH_SIZE ${BOARD_FLASH_SIZE})
set(LINKER_SCRIPT "${CMAKE_BINARY_DIR}/STM32F103_${BOARD_FLASH_SIZE}.ld")
configure_file("${CMAKE_SOURCE_DIR}/ld/stm32f103.ld.in" "${LINKER_SCRIPT}" @ONLY)

# =============================================================================
# Прошивка: CMSIS (только необходимые файлы из STM32CubeF1) и код приложения.
# =============================================================================
set(CMSIS_DIR "${CMAKE_SOURCE_DIR}/cmsis")

add_executable(${PROJECT_NAME}
    src/main.cpp
    src/app.cpp
    src/board.cpp
    src/button.cpp
    src/monitor.cpp
    src/monitor_processing.cpp
    src/post.cpp
    src/uart.cpp
    src/faults.cpp
    "${CMSIS_DIR}/Device/ST/STM32F1xx/Source/system_stm32f1xx.c"
    "${CMSIS_DIR}/Device/ST/STM32F1xx/Source/gcc/startup_stm32f103xb.s")

set_target_properties(${PROJECT_NAME} PROPERTIES
    SUFFIX ".elf"
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
    C_STANDARD 11
    LINK_DEPENDS "${LINKER_SCRIPT}")

target_include_directories(${PROJECT_NAME} PRIVATE
    src
    "${CMSIS_DIR}/Core/Include"
    "${CMSIS_DIR}/Device/ST/STM32F1xx/Include")

target_compile_definitions(${PROJECT_NAME} PRIVATE STM32F103xB BOARD_${BOARD})

set(MCU_FLAGS -mcpu=cortex-m3 -mthumb)

# LTO не используется: см. hil/README.md.
target_compile_options(${PROJECT_NAME} PRIVATE
    ${MCU_FLAGS}
    -ffunction-sections -fdata-sections
    -Wall -Wextra
    $<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit>
    $<$<CONFIG:Debug>:-Og -g3>
    $<$<CONFIG:Release>:-Os -g>)

target_link_options(${PROJECT_NAME} PRIVATE
    ${MCU_FLAGS}
    -T "${LINKER_SCRIPT}"
    --specs=nano.specs
    -Wl,--gc-sections
    -Wl,-Map=$<TARGET_FILE_DIR:${PROJECT_NAME}>/${PROJECT_NAME}.map
    -Wl,--print-memory-usage
    $<$<VERSION_GREATER_EQUAL:$<CXX_COMPILER_VERSION>,12.0>:-Wl,--no-warn-rwx-segments>)

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND "${CMAKE_OBJCOPY}" -O ihex "$<TARGET_FILE:${PROJECT_NAME}>" "$<TARGET_FILE_DIR:${PROJECT_NAME}>/${PROJECT_NAME}.hex"
    COMMAND "${CMAKE_OBJCOPY}" -O binary "$<TARGET_FILE:${PROJECT_NAME}>" "$<TARGET_FILE_DIR:${PROJECT_NAME}>/${PROJECT_NAME}.bin"
    COMMAND "${CMAKE_SIZE}" "$<TARGET_FILE:${PROJECT_NAME}>"
    VERBATIM)

# Эмуляция и ручной GDB-сервер используют ту же модель STM32F103.
include(cmake/emulation.cmake)

# =============================================================================
# HIL-тесты stm32-gdbtest (выключены по умолчанию): cmake/hil.cmake.
# =============================================================================
include(cmake/hil.cmake)
