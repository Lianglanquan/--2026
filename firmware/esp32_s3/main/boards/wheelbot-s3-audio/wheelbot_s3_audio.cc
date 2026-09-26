#include "application.h"
#include "button.h"
#include "codecs/no_audio_codec.h"
#include "config.h"
#include "ssd1315_panel.h"
#include "wheelbot_oled_display.h"
#include "wheelbot_control.h"
#include "wheelbot_mission_client.h"
#include "wifi_board.h"
#include "mcp_server.h"

#include <string>
#include <esp_log.h>
#include <driver/gpio.h>
#include <driver/i2c_master.h>
#include <esp_lcd_panel_io.h>
#include <esp_lcd_panel_ops.h>

#define TAG "WheelbotS3Audio"

class WheelbotS3AudioBoard : public WifiBoard {
private:
    Button boot_button_;
    Button key1_;
    Button key2_;
    Button key3_;
    WheelbotMissionClient mission_client_;
    Display* display_ = nullptr;
    i2c_master_bus_handle_t display_i2c_bus_ = nullptr;
    esp_lcd_panel_io_handle_t display_io_ = nullptr;
    esp_lcd_panel_handle_t display_panel_ = nullptr;

    void InitializeDisplay() {
        i2c_master_bus_config_t bus_config = {};
        bus_config.i2c_port = I2C_NUM_0;
        bus_config.sda_io_num = WHEELBOT_OLED_SDA_GPIO;
        bus_config.scl_io_num = WHEELBOT_OLED_SCL_GPIO;
        bus_config.clk_source = I2C_CLK_SRC_DEFAULT;
        bus_config.glitch_ignore_cnt = 7;
        bus_config.flags.enable_internal_pullup = true;
        ESP_ERROR_CHECK(i2c_new_master_bus(&bus_config, &display_i2c_bus_));

        esp_lcd_panel_io_i2c_config_t io_config = {};
        io_config.dev_addr = WHEELBOT_OLED_I2C_ADDRESS_7BIT;
        io_config.scl_speed_hz = 400 * 1000;
        io_config.control_phase_bytes = 1;
        io_config.dc_bit_offset = 6;
        io_config.lcd_cmd_bits = 8;
        io_config.lcd_param_bits = 8;
        ESP_ERROR_CHECK(esp_lcd_new_panel_io_i2c(display_i2c_bus_, &io_config, &display_io_));
        ESP_ERROR_CHECK(wheelbot_new_ssd1315_panel(display_io_, &display_panel_));
        ESP_ERROR_CHECK(esp_lcd_panel_reset(display_panel_));
        ESP_ERROR_CHECK(esp_lcd_panel_init(display_panel_));
        ESP_ERROR_CHECK(wheelbot_ssd1315_apply_module_init(display_io_));
        // LVGL's monochrome conversion uses the opposite pixel polarity from
        // this SSD1315 module. Invert in the controller so text remains
        // logically upright and white-on-black at the application layer.
        ESP_ERROR_CHECK(esp_lcd_panel_invert_color(display_panel_, true));
        ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(display_panel_, true));
        display_ = new WheelbotOledDisplay(display_io_, display_panel_);
    }

    void InitializeAmplifier() {
        gpio_config_t cfg = {};
        cfg.pin_bit_mask = 1ULL << AUDIO_AMP_SD_GPIO;
        cfg.mode = GPIO_MODE_OUTPUT_OD;
        cfg.pull_up_en = GPIO_PULLUP_DISABLE;
        cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
        cfg.intr_type = GPIO_INTR_DISABLE;
        ESP_ERROR_CHECK(gpio_config(&cfg));
        ESP_ERROR_CHECK(gpio_set_level(AUDIO_AMP_SD_GPIO, 1));
    }

    void InitializeButtons() {
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
                return;
            }
            app.ToggleChatState();
        });
        key1_.OnClick([this]() { Application::GetInstance().ToggleChatState(); });
        key2_.OnClick([this]() { GetDisplay()->SetEmotion("happy"); });
        key3_.OnClick([this]() { GetDisplay()->SetEmotion("sleep"); });
    }

    void InitializeWheelbotControl() {
        const esp_err_t err = wheelbot_control_start();
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to start WheelBot safety control: %s", esp_err_to_name(err));
        }
    }

    void InitializeMissionTools() {
        auto& server = McpServer::GetInstance();
        server.AddTool(
            "self.wheelbot.navigate",
            "让轮足机器人自主导航到已配置的语义位置。不要用它生成底层速度或电机指令。",
            PropertyList({Property("location", kPropertyTypeString).SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Submit(
                    "NAVIGATE", properties["location"].value<std::string>(), "", "home");
                if (!result) return std::unexpected(result.error());
                return *result;
            });
        server.AddTool(
            "self.wheelbot.fetch_item",
            "创建取物任务：机器人前往语义工作区，等待机械臂装载，再返回指定位置。",
            PropertyList({Property("item", kPropertyTypeString).SetMaxLength(120),
                          Property("pickup_location", kPropertyTypeString).SetMaxLength(80),
                          Property("return_location", kPropertyTypeString, std::string("home"))
                              .SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Submit(
                    "FETCH_ITEM", properties["pickup_location"].value<std::string>(),
                    properties["item"].value<std::string>(),
                    properties["return_location"].value<std::string>());
                if (!result) return std::unexpected(result.error());
                return *result;
            });
        server.AddTool(
            "self.wheelbot.return_home", "让轮足机器人执行返回任务。",
            PropertyList({Property("location", kPropertyTypeString, std::string("home"))
                              .SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Submit(
                    "RETURN_HOME", "", "", properties["location"].value<std::string>());
                if (!result) return std::unexpected(result.error());
                return *result;
            });
        server.AddTool(
            "self.wheelbot.get_mission_status", "查询当前任务或指定任务的真实执行状态。",
            PropertyList({Property("mission_id", kPropertyTypeString, std::string(""))
                              .SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.GetStatus(
                    properties["mission_id"].value<std::string>());
                if (!result) return std::unexpected(result.error());
                return *result;
            });
        server.AddTool(
            "self.wheelbot.cancel_mission", "取消指定任务；取消后不会继续后续阶段。",
            PropertyList({Property("mission_id", kPropertyTypeString).SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Cancel(
                    properties["mission_id"].value<std::string>());
                if (!result) return std::unexpected(result.error());
                return *result;
            });
    }

public:
    WheelbotS3AudioBoard()
        : boot_button_(BOOT_BUTTON_GPIO), key1_(WHEELBOT_KEY1_GPIO),
          key2_(WHEELBOT_KEY2_GPIO), key3_(WHEELBOT_KEY3_GPIO) {
        InitializeDisplay();
        InitializeAmplifier();
        InitializeButtons();
        InitializeWheelbotControl();
        InitializeMissionTools();
    }

    Display* GetDisplay() override { return display_; }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex audio_codec(
            AUDIO_INPUT_SAMPLE_RATE,
            AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK,
            AUDIO_I2S_SPK_GPIO_WS,
            AUDIO_I2S_SPK_GPIO_DOUT,
            AUDIO_I2S_MIC_GPIO_BCLK,
            AUDIO_I2S_MIC_GPIO_WS,
            AUDIO_I2S_MIC_GPIO_DIN);
        return &audio_codec;
    }
};

DECLARE_BOARD(WheelbotS3AudioBoard);
