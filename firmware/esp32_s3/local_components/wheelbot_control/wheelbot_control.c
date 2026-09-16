#include "wheelbot_control.h"

#include "wheelbot_config.h"

#include "driver/uart.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <stdbool.h>

static const char *TAG = "wheelbot_control";

static wheelbot_input_router_t router;
static wheelbot_uart_transport_t transport;
static TaskHandle_t task_handle;
static bool started;

static int uart_tx(const uint8_t *data, size_t length, void *context)
{
    (void)context;
    const int written = uart_write_bytes(WHEELBOT_UART_PORT, data, length);
    return written == (int)length ? 0 : -1;
}

static void wheelbot_uart_task(void *context)
{
    (void)context;
    TickType_t last_wake = xTaskGetTickCount();

    while (true) {
        const uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000ULL);
        wheelbot_intent_t intent;
        if (wheelbot_input_router_select(&router, now_ms, &intent) != 0) {
            intent = (wheelbot_intent_t){
                .mode = WHEELBOT_MODE_STOP,
                .stop = 1U,
            };
        }

        if (wheelbot_uart_transport_send(&transport, &intent) != 0) {
            ESP_LOGW(TAG, "Failed to write WheelBot UART frame");
        }
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(WHEELBOT_COMMAND_PERIOD_MS));
    }
}

esp_err_t wheelbot_control_start(void)
{
    if (started) {
        return ESP_OK;
    }

    const uart_config_t uart_config = {
        .baud_rate = WHEELBOT_UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_RETURN_ON_ERROR(uart_driver_install(WHEELBOT_UART_PORT,
                                             WHEELBOT_UART_RX_BUFFER,
                                             WHEELBOT_UART_TX_BUFFER,
                                             0, NULL, 0), TAG,
                        "UART driver install failed");
    ESP_RETURN_ON_ERROR(uart_param_config(WHEELBOT_UART_PORT, &uart_config),
                        TAG, "UART configuration failed");
    ESP_RETURN_ON_ERROR(uart_set_pin(WHEELBOT_UART_PORT,
                                     WHEELBOT_UART_TX_GPIO,
                                     WHEELBOT_UART_RX_GPIO,
                                     UART_PIN_NO_CHANGE,
                                     UART_PIN_NO_CHANGE),
                        TAG, "UART pin configuration failed");

    wheelbot_input_router_init(&router, WHEELBOT_INTENT_TIMEOUT_MS);
    transport = (wheelbot_uart_transport_t){
        .tx = uart_tx,
        .drive = {
            .wheel_radius_m = WHEELBOT_WHEEL_RADIUS_M,
            .track_width_m = WHEELBOT_TRACK_WIDTH_M,
            .max_wheel_rpm = WHEELBOT_MAX_WHEEL_RPM,
        },
    };

    if (xTaskCreate(wheelbot_uart_task, "wheelbot_uart", 3072, NULL, 5,
                    &task_handle) != pdPASS) {
        uart_driver_delete(WHEELBOT_UART_PORT);
        task_handle = NULL;
        return ESP_ERR_NO_MEM;
    }

    started = true;
    ESP_LOGI(TAG, "UART safety link started on TX=%d RX=%d at %d baud",
             WHEELBOT_UART_TX_GPIO, WHEELBOT_UART_RX_GPIO,
             WHEELBOT_UART_BAUD);
    return ESP_OK;
}

wheelbot_input_router_t *wheelbot_control_router(void)
{
    return &router;
}
