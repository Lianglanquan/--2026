cmake_minimum_required(VERSION 3.16)

if(DEFINED ENV{IDF_PATH})
    include($ENV{IDF_PATH}/tools/cmake/project.cmake)
    project(wheelbot_esp32_s3)
else()
    project(wheelbot_esp32_s3 C)
    add_library(wheelbot_esp32_core
        src/wheelbot_esp32_core.c
        src/wheelbot_input_router.c
        src/wheelbot_uart_transport.c
        src/wheelbot_command_parser.c
        src/wheelbot_providers.c
        src/wheelbot_voice.c
        src/wheelbot_ble.c)
    target_include_directories(wheelbot_esp32_core PUBLIC include)
    target_compile_features(wheelbot_esp32_core PUBLIC c_std_11)
    target_compile_options(wheelbot_esp32_core PRIVATE -Wall -Wextra -Werror)
    option(WHEELBOT_BUILD_TESTS "Build host-side ESP32 core tests" OFF)
    if(WHEELBOT_BUILD_TESTS)
        enable_testing()
        add_executable(test_esp32_core ../../tests/esp32_s3/test_esp32_core.c)
        target_link_libraries(test_esp32_core PRIVATE wheelbot_esp32_core m)
        add_test(NAME esp32_core COMMAND test_esp32_core)
        add_executable(test_battery_telemetry ../../tests/esp32_s3/test_battery_telemetry.c)
        target_link_libraries(test_battery_telemetry PRIVATE wheelbot_esp32_core m)
        add_test(NAME battery_telemetry COMMAND test_battery_telemetry)
    endif()
endif()
