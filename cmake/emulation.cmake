# =============================================================================
# Дымовой тест в эмуляторе Renode (без платы): ctest -L emu. Нужны Renode 1.16+ и Python 3.
# Путь к Renode: -DRENODE_EXECUTABLE=..., переменная RENODE_BINARY или PATH.
# =============================================================================
option(BLUEPILL_RENODE_TEST "Renode smoke test (ctest -L emu) when Renode is found" ON)
if(BLUEPILL_RENODE_TEST)
    if(DEFINED ENV{RENODE_BINARY} AND NOT RENODE_EXECUTABLE)
        set(RENODE_EXECUTABLE "$ENV{RENODE_BINARY}" CACHE FILEPATH "Renode executable")
    endif()
    find_program(RENODE_EXECUTABLE NAMES renode Renode PATHS "$ENV{ProgramFiles}/Renode")
endif()
if(BLUEPILL_RENODE_TEST AND RENODE_EXECUTABLE)
    find_package(Python3 3.11 COMPONENTS Interpreter QUIET)
endif()
if(BLUEPILL_RENODE_TEST AND RENODE_EXECUTABLE AND Python3_Interpreter_FOUND)
    enable_testing()
    add_test(NAME emu.renode_smoke
        COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_SOURCE_DIR}/tools/renode_smoke.py"
            --elf "$<TARGET_FILE:${PROJECT_NAME}>" --board "${BOARD}"
            --renode "${RENODE_EXECUTABLE}" --nm "${ARM_TOOLCHAIN_BIN}arm-none-eabi-nm${ARM_TOOLCHAIN_EXT}")
    set_tests_properties(emu.renode_smoke PROPERTIES LABELS emu TIMEOUT 180)
    message(STATUS "Renode smoke test: ${RENODE_EXECUTABLE}")
endif()


if(BLUEPILL_RENODE_TEST AND RENODE_EXECUTABLE AND Python3_Interpreter_FOUND)
    add_custom_target(emulate
        COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_SOURCE_DIR}/tools/renode_smoke.py"
            --elf "$<TARGET_FILE:${PROJECT_NAME}>" --board "${BOARD}"
            --renode "${RENODE_EXECUTABLE}" --nm "${ARM_TOOLCHAIN_BIN}arm-none-eabi-nm${ARM_TOOLCHAIN_EXT}"
        DEPENDS ${PROJECT_NAME} USES_TERMINAL VERBATIM)
    set(RENODE_MODEL "${CMAKE_SOURCE_DIR}/emu/renode/stm32f103.repl")
    set(RENODE_ELF "${CMAKE_BINARY_DIR}/${PROJECT_NAME}.elf")
    set(RENODE_LOG "${CMAKE_BINARY_DIR}/renode-debug/uart.log")
    file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/renode-debug")
    foreach(var RENODE_MODEL RENODE_ELF RENODE_LOG)
        string(REPLACE " " "\\ " ${var} "${${var}}")
    endforeach()
    configure_file("${CMAKE_SOURCE_DIR}/cmake/renode-debug.resc.in" "${CMAKE_BINARY_DIR}/renode-debug/debug.resc" @ONLY)
    string(REPLACE " " "\\ " RENODE_SCRIPT "${CMAKE_BINARY_DIR}/renode-debug/debug.resc")
    add_custom_target(emulate-debug
        COMMAND "${RENODE_EXECUTABLE}" --disable-gui --console --plain
            -e "include @${RENODE_SCRIPT}"
        DEPENDS ${PROJECT_NAME} USES_TERMINAL VERBATIM)
endif()
