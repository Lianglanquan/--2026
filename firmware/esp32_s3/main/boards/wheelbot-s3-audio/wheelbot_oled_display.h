#ifndef WHEELBOT_OLED_DISPLAY_H
#define WHEELBOT_OLED_DISPLAY_H

#include "display/oled_display.h"
#include "face_state.h"

class WheelbotOledDisplay : public OledDisplay {
public:
    WheelbotOledDisplay(esp_lcd_panel_io_handle_t io, esp_lcd_panel_handle_t panel);
    ~WheelbotOledDisplay() override;

    void SetupUI() override;
    void SetStatus(const char* status) override;
    void SetEmotion(const char* emotion) override;
    void SetChatMessage(const char* role, const char* content) override;
    void ClearChatMessages() override;

private:
    lv_obj_t* root_ = nullptr;
    lv_obj_t* canvas_ = nullptr;
    lv_obj_t* status_ = nullptr;
    lv_draw_buf_t* canvas_buffer_ = nullptr;
    lv_timer_t* animation_timer_ = nullptr;
    WheelbotFaceState face_ = WheelbotFaceState::kWake;
    uint8_t animation_phase_ = 0;

    void SetFace(WheelbotFaceState face);
    void DrawFace();
    static void AnimationTimer(lv_timer_t* timer);
};

#endif
