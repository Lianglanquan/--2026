#include "ssd1315_panel.h"

#include <esp_check.h>
#include <esp_lcd_panel_vendor.h>
#include <driver/gpio.h>

namespace {
constexpr char kTag[] = "WheelbotSSD1315";

esp_err_t Send(esp_lcd_panel_io_handle_t io, int command, uint8_t value) {
    return esp_lcd_panel_io_tx_param(io, command, &value, 1);
}
}  // namespace

esp_err_t wheelbot_new_ssd1315_panel(esp_lcd_panel_io_handle_t io,
                                     esp_lcd_panel_handle_t* panel) {
    esp_lcd_panel_ssd1306_config_t compatible_config = {};
    compatible_config.height = 64;
    compatible_config.contrast = 0x8F;
    esp_lcd_panel_dev_config_t panel_config = {};
    panel_config.reset_gpio_num = GPIO_NUM_NC;
    panel_config.bits_per_pixel = 1;
    panel_config.vendor_config = &compatible_config;

    // SSD1315 uses the same horizontal-addressing transfer commands as SSD1306.
    return esp_lcd_new_panel_ssd1306(io, &panel_config, panel);
}

esp_err_t wheelbot_ssd1315_apply_module_init(esp_lcd_panel_io_handle_t io) {
    ESP_RETURN_ON_ERROR(Send(io, 0xD5, 0x80), kTag, "clock divider");
    ESP_RETURN_ON_ERROR(Send(io, 0xD3, 0x00), kTag, "display offset");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(io, 0x40, nullptr, 0), kTag, "start line");
    ESP_RETURN_ON_ERROR(Send(io, 0xD9, 0xF1), kTag, "pre-charge");
    ESP_RETURN_ON_ERROR(Send(io, 0xDB, 0x40), kTag, "vcomh");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_io_tx_param(io, 0xA4, nullptr, 0), kTag, "resume RAM");
    return esp_lcd_panel_io_tx_param(io, 0xA6, nullptr, 0);
}
