#include "application.h"
#include "button.h"
#include "codecs/no_audio_codec.h"
#include "config.h"
#include "wheelbot_control.h"
#include "wifi_board.h"

#include <esp_log.h>

#define TAG "WheelbotS3Audio"

class WheelbotS3AudioBoard : public WifiBoard {
private:
    Button boot_button_;

    void InitializeButtons() {
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
                return;
            }
            app.ToggleChatState();
        });
    }

    void InitializeWheelbotControl() {
        const esp_err_t err = wheelbot_control_start();
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "Failed to start WheelBot safety control: %s", esp_err_to_name(err));
        }
    }

public:
    WheelbotS3AudioBoard() : boot_button_(BOOT_BUTTON_GPIO) {
        InitializeButtons();
        InitializeWheelbotControl();
    }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecDuplex audio_codec(
            AUDIO_INPUT_SAMPLE_RATE,
            AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_GPIO_BCLK,
            AUDIO_I2S_GPIO_WS,
            AUDIO_I2S_GPIO_DOUT,
            AUDIO_I2S_GPIO_DIN);
        return &audio_codec;
    }
};

DECLARE_BOARD(WheelbotS3AudioBoard);
