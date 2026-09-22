#include "wheelbot_esp32_core.h"
#include "wheelbot_config.h"
#include "wheelbot_wifi.h"
#include "wheelbot_audio.h"

#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "wheelbot_esp32";
static wheelbot_input_router_t input_router;
static wheelbot_uart_transport_t uart_transport;
static wheelbot_battery_parser_t battery_parser;

static int uart_tx(const uint8_t *data, size_t length, void *context)
{
    (void)context;
    return uart_write_bytes(WHEELBOT_UART_PORT, (const char *)data, length) == (int)length ? 0 : -1;
}

void app_main(void)
{
    const uart_config_t config = {
        .baud_rate = WHEELBOT_UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_param_config(WHEELBOT_UART_PORT, &config));
    ESP_ERROR_CHECK(uart_set_pin(WHEELBOT_UART_PORT, WHEELBOT_UART_TX_GPIO,
                                  WHEELBOT_UART_RX_GPIO, UART_PIN_NO_CHANGE,
                                  UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(WHEELBOT_UART_PORT,
                                         WHEELBOT_UART_RX_BUFFER,
                                         WHEELBOT_UART_TX_BUFFER, 0, NULL, 0));
    ESP_LOGI(TAG, "UART ready: port=%d tx=%d rx=%d baud=%d",
             WHEELBOT_UART_PORT, WHEELBOT_UART_TX_GPIO,
             WHEELBOT_UART_RX_GPIO, WHEELBOT_UART_BAUD);
    wheelbot_battery_parser_init(&battery_parser);
    wheelbot_input_router_init(&input_router, WHEELBOT_INTENT_TIMEOUT_MS);
    if (wheelbot_wifi_start(&input_router) != 0) {
        ESP_LOGW(TAG, "Wi-Fi control endpoint unavailable; UART safety loop continues");
    }
    if (wheelbot_audio_start() != 0) {
        ESP_LOGW(TAG, "I2S audio unavailable; control loop continues");
    }
    uart_transport.tx = uart_tx;
    uart_transport.drive.wheel_radius_m = WHEELBOT_WHEEL_RADIUS_M;
    uart_transport.drive.track_width_m = WHEELBOT_TRACK_WIDTH_M;
    uart_transport.drive.max_wheel_rpm = WHEELBOT_MAX_WHEEL_RPM;

    /* Providers submit into input_router from their callbacks. Until one is
     * active, the loop emits an explicit stop command at 50 Hz. */
    for (;;) {
        wheelbot_intent_t intent = {
            .mode = WHEELBOT_MODE_STOP,
            .stop = 1U,
        };
        const uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000LL);
        if (wheelbot_input_router_select(&input_router, now_ms, &intent) != 0) {
            intent.mode = WHEELBOT_MODE_STOP;
            intent.stop = 1U;
        }
        if (wheelbot_uart_transport_send(&uart_transport, &intent) != 0) {
            ESP_LOGW(TAG, "UART command send failed");
        }
        uint8_t telemetry[64];
        const int received = uart_read_bytes(WHEELBOT_UART_PORT, telemetry,
                                             sizeof(telemetry), 0);
        if (received > 0 &&
            wheelbot_battery_parser_feed(&battery_parser, telemetry,
                                         (size_t)received) != 0) {
            ESP_LOGW(TAG, "invalid battery telemetry input");
        }
        if (battery_parser.frames_received != 0U) {
            ESP_LOGI(TAG, "C Board battery: %.2f V (%u%%)",
                     (double)battery_parser.latest.voltage,
                     (unsigned)battery_parser.latest.percentage);
            battery_parser.frames_received = 0U;
        }
        vTaskDelay(pdMS_TO_TICKS(WHEELBOT_COMMAND_PERIOD_MS));
    }
}
