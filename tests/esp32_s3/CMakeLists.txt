cmake_minimum_required(VERSION 3.16)
project(wheelbot_esp32_s3_host_tests C CXX)

if(NOT DEFINED WHEELBOT_COMPONENT_DIR)
    message(FATAL_ERROR "WHEELBOT_COMPONENT_DIR is required")
endif()

add_library(wheelbot_esp32_core
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_esp32_core.c"
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_input_router.c"
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_uart_transport.c"
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_command_parser.c"
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_providers.c"
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_voice.c"
    "${WHEELBOT_COMPONENT_DIR}/wheelbot_ble.c")
target_include_directories(wheelbot_esp32_core PUBLIC
    "${WHEELBOT_COMPONENT_DIR}/include")
target_compile_features(wheelbot_esp32_core PUBLIC c_std_11)
target_compile_options(wheelbot_esp32_core PRIVATE -Wall -Wextra -Werror)

enable_testing()
add_executable(test_esp32_core test_esp32_core.c)
target_link_libraries(test_esp32_core PRIVATE wheelbot_esp32_core m)
add_test(NAME esp32_core COMMAND test_esp32_core)

add_executable(test_wheelbot_face
    "${CMAKE_CURRENT_SOURCE_DIR}/../../firmware/esp32_s3/main/boards/wheelbot-s3-audio/face_state.cc"
    test_wheelbot_face.cc)
target_include_directories(test_wheelbot_face PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/../../firmware/esp32_s3/main/boards/wheelbot-s3-audio")
target_compile_features(test_wheelbot_face PRIVATE cxx_std_17)
target_compile_options(test_wheelbot_face PRIVATE -Wall -Wextra -Werror)
add_test(NAME wheelbot_face COMMAND test_wheelbot_face)
