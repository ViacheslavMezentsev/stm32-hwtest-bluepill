# =============================================================================
# HIL-тесты stm32-gdbtest (метод DDTT), выключены по умолчанию.
# Включение: пресеты f103c8-hil и f103cb-hil (-DBLUEPILL_HIL=ON, генератор Ninja).
# Сценарии и требования общие (hil/common/tests). Плату описывает конфигурация прогона
# hil/<MCU>/session.toml: описание MCU (hil/<MCU>/target.toml), общий hil/api.toml и файл данных платы (hil/<MCU>/board.toml).
# =============================================================================
option(BLUEPILL_HIL "Hardware tests via stm32-gdbtest" OFF)

if(BLUEPILL_HIL)
    string(REGEX REPLACE "_.*$" "" HIL_PROFILE "${BOARD}")
    set(HIL_SESSION "${CMAKE_SOURCE_DIR}/hil/${HIL_PROFILE}/session.toml")
    if(NOT EXISTS "${HIL_SESSION}")
        message(FATAL_ERROR "No HIL run configuration for BOARD=${BOARD}: ${HIL_SESSION}")
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
    # отладочную информацию. Типы нужны для офлайн-сверки SVD с адресами CMSIS;
    # аппаратные чтения сценариев идут через MMIO, код прошивки не меняется.
    target_compile_options(${PROJECT_NAME} PRIVATE -fno-eliminate-unused-debug-types)

    message(STATUS "HIL: run configuration ${HIL_SESSION}")
    include(CTest)
    include("${STM32_GDBTEST_SOURCE_DIR}/stm32_gdbtest/cmake/STM32GDBTest.cmake")
    stm32_gdbtest_attach(${PROJECT_NAME}
        PROFILE_DIR "${CMAKE_SOURCE_DIR}/hil/common"
        SESSION_CONFIG "${HIL_SESSION}"
        MANIFEST_INPUTS
            "${CMAKE_SOURCE_DIR}/ld/stm32f103.ld.in"
            "${CMAKE_SOURCE_DIR}/CMakeLists.txt"
            "${CMAKE_SOURCE_DIR}/cmake/arm-gcc.cmake"
            "${CMAKE_CURRENT_LIST_FILE}")
    # Чисто офлайн: контракт сценариев и соответствие SVD текущему ELF.
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME host.mmio
        COMMAND "${Python3_EXECUTABLE}" -m unittest discover
                -s "${CMAKE_SOURCE_DIR}/hil/tools" -p "test_mmio_*.py")
    add_test(NAME host.svd_elf
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/hil/tools/check_mmio_elf.py"
                --elf "$<TARGET_FILE:${PROJECT_NAME}>" --gdb "${STM32_GDBTEST_GDB}")
    set_tests_properties(host.mmio host.svd_elf PROPERTIES LABELS host TIMEOUT 45)
endif()
