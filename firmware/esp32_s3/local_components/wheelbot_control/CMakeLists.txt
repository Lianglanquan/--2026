idf_component_register(
    SRCS
        "wheelbot_control.c"
        "wheelbot_esp32_core.c"
        "wheelbot_input_router.c"
        "wheelbot_uart_transport.c"
        "wheelbot_command_parser.c"
        "wheelbot_providers.c"
        "wheelbot_voice.c"
        "wheelbot_ble.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_common esp_driver_gpio esp_driver_uart esp_timer freertos
)
