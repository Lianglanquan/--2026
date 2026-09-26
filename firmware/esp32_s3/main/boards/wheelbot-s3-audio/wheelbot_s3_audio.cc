#include <string>

#include "application.h"
#include "boards/common/wifi_board.h"
#include "button.h"
#include "codecs/no_audio_codec.h"
#include "config.h"
#include "mcp_server.h"
#include "wheelbot_mission_client.h"

class WheelbotS3AudioBoard : public WifiBoard {
private:
    Button boot_button_;
    WheelbotMissionClient mission_client_;

    void InitializeButton() {
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
                return;
            }
            app.ToggleChatState();
        });
    }

    void InitializeTools() {
        auto& server = McpServer::GetInstance();
        server.AddTool(
            "self.wheelbot.navigate",
            "让轮足机器人自主导航到已配置的语义位置。不要用它生成底层速度或电机指令。",
            PropertyList({Property("location", kPropertyTypeString).SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Submit("NAVIGATE",
                                                     properties["location"].value<std::string>(),
                                                     "", "home");
                if (!result) {
                    return std::unexpected(result.error());
                }
                return *result;
            });
        server.AddTool(
            "self.wheelbot.fetch_item",
            "创建取物任务：机器人前往语义工作区，等待机械臂装载，再返回指定位置。",
            PropertyList({Property("item", kPropertyTypeString).SetMaxLength(120),
                          Property("pickup_location", kPropertyTypeString).SetMaxLength(80),
                          Property("return_location", kPropertyTypeString,
                                   std::string("home"))
                              .SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Submit(
                    "FETCH_ITEM", properties["pickup_location"].value<std::string>(),
                    properties["item"].value<std::string>(),
                    properties["return_location"].value<std::string>());
                if (!result) {
                    return std::unexpected(result.error());
                }
                return *result;
            });
        server.AddTool(
            "self.wheelbot.return_home", "让轮足机器人执行返回任务。",
            PropertyList({Property("location", kPropertyTypeString, std::string("home"))
                              .SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result = mission_client_.Submit(
                    "RETURN_HOME", "", "", properties["location"].value<std::string>());
                if (!result) {
                    return std::unexpected(result.error());
                }
                return *result;
            });
        server.AddTool(
            "self.wheelbot.get_mission_status", "查询当前任务或指定任务的真实执行状态。",
            PropertyList({Property("mission_id", kPropertyTypeString, std::string(""))
                              .SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result =
                    mission_client_.GetStatus(properties["mission_id"].value<std::string>());
                if (!result) {
                    return std::unexpected(result.error());
                }
                return *result;
            });
        server.AddTool(
            "self.wheelbot.cancel_mission", "取消指定任务；取消后不会继续后续阶段。",
            PropertyList({Property("mission_id", kPropertyTypeString).SetMaxLength(80)}),
            [this](const PropertyList& properties) -> ToolResult {
                auto result =
                    mission_client_.Cancel(properties["mission_id"].value<std::string>());
                if (!result) {
                    return std::unexpected(result.error());
                }
                return *result;
            });
    }

public:
    WheelbotS3AudioBoard() : boot_button_(BOOT_BUTTON_GPIO) {
        InitializeButton();
        InitializeTools();
    }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecDuplex codec(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
                                        AUDIO_I2S_GPIO_BCLK, AUDIO_I2S_GPIO_WS,
                                        AUDIO_I2S_GPIO_DOUT, AUDIO_I2S_GPIO_DIN);
        return &codec;
    }
};

DECLARE_BOARD(WheelbotS3AudioBoard);
