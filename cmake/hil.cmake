# =============================================================================
# HIL-тесты stm32-gdbtest (метод DDTT), выключены по умолчанию.
# Включение: пресеты HIL_F103C8 и HIL_F103CB (-DBLUEPILL_HIL=ON, генератор Ninja).
# Сценарии и требования общие (hil/tests), описание MCU — hil/profiles/<BOARD>.toml.
# =============================================================================
option(BLUEPILL_HIL "Hardware tests via stm32-gdbtest" OFF)

if(BLUEPILL_HIL)
    set(HIL_PROFILE "${CMAKE_SOURCE_DIR}/hil/profiles/${BOARD}.toml")
    if(NOT EXISTS "${HIL_PROFILE}")
        message(FATAL_ERROR "No HIL MCU description for BOARD=${BOARD}: ${HIL_PROFILE}")
    endif()

    set(STM32_GDBTEST_SOURCE_DIR "${CMAKE_SOURCE_DIR}/modules/stm32-gdbtest" CACHE PATH "stm32-gdbtest checkout")
    if(NOT EXISTS "${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
        message(FATAL_ERROR "stm32-gdbtest not found: ${STM32_GDBTEST_SOURCE_DIR}\n"
                            "Run: git submodule update --init")
    endif()

    # GDB с Python из того же toolchain, если не задан явно.
    if(NOT STM32_GDBTEST_GDB AND ARM_TOOLCHAIN_ROOT)
        foreach(name arm-none-eabi-gdb-py3 arm-none-eabi-gdb)
            if(EXISTS "${ARM_TOOLCHAIN_ROOT}/bin/${name}${ARM_TOOLCHAIN_EXT}")
                set(STM32_GDBTEST_GDB "${ARM_TOOLCHAIN_ROOT}/bin/${name}${ARM_TOOLCHAIN_EXT}" CACHE FILEPATH "GDB with Python")
                break()
            endif()
        endforeach()
    endif()

    # Типы CMSIS (DBGMCU_TypeDef и др.), которые прошивка не использует, GCC не пишет в
    # отладочную информацию. Сценарии обращаются к регистрам по именам CMSIS
    # (DBGMCU->IDCODE), поэтому в HIL-сборке типы сохраняются; код не меняется.
    target_compile_options(${PROJECT_NAME} PRIVATE -fno-eliminate-unused-debug-types)

    message(STATUS "HIL: MCU description ${HIL_PROFILE}")
    include(CTest)
    include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
    stm32_gdbtest_attach(${PROJECT_NAME}
        PROFILE_DIR "${CMAKE_SOURCE_DIR}/hil"
        PROFILE "${HIL_PROFILE}"
        MANIFEST_INPUTS
            "${CMAKE_SOURCE_DIR}/ld/stm32f103.ld.in"
            "${CMAKE_SOURCE_DIR}/CMakeLists.txt"
            "${CMAKE_SOURCE_DIR}/cmake/arm-gcc.cmake"
            "${CMAKE_CURRENT_LIST_FILE}")
endif()
