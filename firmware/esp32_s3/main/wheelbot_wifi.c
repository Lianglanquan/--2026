#include "wheelbot_wifi.h"

#include "wheelbot_providers.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#include <string.h>

static const char *TAG = "wheelbot_wifi";
static wheelbot_input_router_t *input_router;

static esp_err_t control_get(httpd_req_t *request)
{
    char query[160];
    char command[128];
    if (httpd_req_get_url_query_str(request, query, sizeof(query)) != ESP_OK ||
        httpd_query_key_value(query, "cmd", command, sizeof(command)) != ESP_OK) {
        httpd_resp_send_err(request, HTTPD_400_BAD_REQUEST,
                            "use /control?cmd=vx=0.2;yaw_rate=0;mode=2;stop=0");
        return ESP_OK;
    }
    const uint32_t now_ms = (uint32_t)(esp_log_timestamp());
    if (wheelbot_provider_submit_wifi(input_router, command, now_ms) != 0) {
        httpd_resp_send_err(request, HTTPD_400_BAD_REQUEST, "invalid control command");
        return ESP_OK;
    }
    httpd_resp_set_type(request, "text/plain");
    httpd_resp_sendstr(request, "accepted\n");
    return ESP_OK;
}

int wheelbot_wifi_start(wheelbot_input_router_t *router)
{
    if (router == NULL) return -1;
    input_router = router;
    if (nvs_flash_init() != ESP_OK) return -1;
    if (esp_netif_init() != ESP_OK || esp_event_loop_create_default() != ESP_OK) return -1;
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t init_config = WIFI_INIT_CONFIG_DEFAULT();
    if (esp_wifi_init(&init_config) != ESP_OK) return -1;
    wifi_config_t ap_config = {
        .ap = {
            .ssid = "WheelBot-ESP32",
            .ssid_len = 0,
            .channel = 1,
            .password = "wheelbot42",
            .max_connection = 2,
            .authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    if (esp_wifi_set_mode(WIFI_MODE_AP) != ESP_OK ||
        esp_wifi_set_config(WIFI_IF_AP, &ap_config) != ESP_OK ||
        esp_wifi_start() != ESP_OK) return -1;

    httpd_config_t server_config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    if (httpd_start(&server, &server_config) != ESP_OK) return -1;
    const httpd_uri_t control_uri = {
        .uri = "/control", .method = HTTP_GET, .handler = control_get, .user_ctx = NULL,
    };
    if (httpd_register_uri_handler(server, &control_uri) != ESP_OK) return -1;
    ESP_LOGI(TAG, "SoftAP ready: SSID=WheelBot-ESP32 endpoint=/control");
    return 0;
}
