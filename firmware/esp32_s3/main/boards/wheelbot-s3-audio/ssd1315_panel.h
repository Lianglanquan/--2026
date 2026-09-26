#ifndef WHEELBOT_SSD1315_PANEL_H
#define WHEELBOT_SSD1315_PANEL_H

#include <esp_lcd_panel_io.h>
#include <esp_lcd_panel_ops.h>
#include <esp_err.h>

esp_err_t wheelbot_new_ssd1315_panel(esp_lcd_panel_io_handle_t io,
                                     esp_lcd_panel_handle_t* panel);
esp_err_t wheelbot_ssd1315_apply_module_init(esp_lcd_panel_io_handle_t io);

#endif
