idf_component_register(
    SRCS "main.c" "wheelbot_wifi.c" "wheelbot_audio.c"
         "../src/wheelbot_esp32_core.c"
         "../src/wheelbot_input_router.c"
         "../src/wheelbot_uart_transport.c"
         "../src/wheelbot_command_parser.c"
         "../src/wheelbot_providers.c"
         "../src/wheelbot_voice.c"
         "../src/wheelbot_ble.c"
    INCLUDE_DIRS "../include"
    REQUIRES driver esp_timer esp_http_server esp_wifi esp_netif nvs_flash
)
