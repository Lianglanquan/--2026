#include "wheelbot_oled_display.h"

#include <esp_lvgl_port.h>
#include <cstring>

namespace {
constexpr int kCanvasWidth = 128;
// Keep the face canvas page-aligned (6 SSD1315 pages). The status label owns
// the last two pages; overlapping the two LVGL objects used to leave stale
// horizontal rows on I2C OLED refreshes.
constexpr int kCanvasHeight = 48;

void Rect(lv_layer_t* layer, int x, int y, int w, int h, int radius = 0) {
    lv_draw_rect_dsc_t dsc;
    lv_draw_rect_dsc_init(&dsc);
    dsc.bg_color = lv_color_white();
    dsc.bg_opa = LV_OPA_COVER;
    dsc.border_opa = LV_OPA_TRANSP;
    dsc.radius = radius;
    lv_area_t area = {x, y, x + w - 1, y + h - 1};
    lv_draw_rect(layer, &dsc, &area);
}

void Line(lv_layer_t* layer, int x1, int y1, int x2, int y2, int width = 3) {
    lv_draw_line_dsc_t dsc;
    lv_draw_line_dsc_init(&dsc);
    dsc.color = lv_color_white();
    dsc.opa = LV_OPA_COVER;
    dsc.width = width;
    dsc.round_start = 1;
    dsc.round_end = 1;
    dsc.p1 = {static_cast<lv_value_precise_t>(x1), static_cast<lv_value_precise_t>(y1)};
    dsc.p2 = {static_cast<lv_value_precise_t>(x2), static_cast<lv_value_precise_t>(y2)};
    lv_draw_line(layer, &dsc);
}
}  // namespace

WheelbotOledDisplay::WheelbotOledDisplay(esp_lcd_panel_io_handle_t io,
                                         esp_lcd_panel_handle_t panel)
    : OledDisplay(io, panel, 128, 64, false, false) {}

WheelbotOledDisplay::~WheelbotOledDisplay() {
    if (!lvgl_port_lock(1000)) return;
    if (animation_timer_) lv_timer_delete(animation_timer_);
    if (root_) lv_obj_del(root_);
    // The canvas owns the draw buffer after lv_canvas_set_draw_buf().
    canvas_buffer_ = nullptr;
    lvgl_port_unlock();
}

void WheelbotOledDisplay::SetupUI() {
    if (setup_ui_called_) return;
    Display::SetupUI();
    if (!lvgl_port_lock(30000)) return;

    auto* screen = lv_screen_active();
    lv_obj_set_style_bg_color(screen, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);
    root_ = lv_obj_create(screen);
    lv_obj_set_size(root_, 128, 64);
    lv_obj_set_style_pad_all(root_, 0, 0);
    lv_obj_set_style_border_width(root_, 0, 0);
    lv_obj_set_style_radius(root_, 0, 0);
    lv_obj_set_style_bg_color(root_, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(root_, LV_OPA_COVER, 0);
    lv_obj_set_scrollbar_mode(root_, LV_SCROLLBAR_MODE_OFF);

    canvas_buffer_ = lv_draw_buf_create(kCanvasWidth, kCanvasHeight, LV_COLOR_FORMAT_I1,
                                        LV_STRIDE_AUTO);
    canvas_ = lv_canvas_create(root_);
    lv_canvas_set_draw_buf(canvas_, canvas_buffer_);
    lv_canvas_set_palette(canvas_, 0, lv_color_to_32(lv_color_black(), LV_OPA_COVER));
    lv_canvas_set_palette(canvas_, 1, lv_color_to_32(lv_color_white(), LV_OPA_COVER));
    lv_obj_align(canvas_, LV_ALIGN_TOP_MID, 0, 0);

    status_ = lv_label_create(root_);
    lv_obj_set_width(status_, 124);
    lv_obj_set_height(status_, 16);
    lv_obj_set_style_bg_color(status_, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(status_, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_all(status_, 0, 0);
    lv_obj_set_style_text_color(status_, lv_color_white(), 0);
    lv_obj_set_style_text_align(status_, LV_TEXT_ALIGN_CENTER, 0);
    lv_label_set_long_mode(status_, LV_LABEL_LONG_CLIP);
    lv_label_set_text(status_, "WHEELBOT");
    lv_obj_align(status_, LV_ALIGN_BOTTOM_MID, 0, 0);

    animation_timer_ = lv_timer_create(AnimationTimer, 250, this);
    DrawFace();
    lvgl_port_unlock();
}

void WheelbotOledDisplay::SetStatus(const char* status) {
    if (!lvgl_port_lock(30000)) return;
    if (status_) lv_label_set_text(status_, status ? status : "");
    lvgl_port_unlock();
}

void WheelbotOledDisplay::SetEmotion(const char* emotion) {
    if (!emotion) return;
    if (!std::strcmp(emotion, "low_battery")) SetFace(WheelbotFaceState::kLowBattery);
    else if (!std::strcmp(emotion, "moving")) SetFace(WheelbotFaceState::kMoving);
    else if (!std::strcmp(emotion, "exploring")) SetFace(WheelbotFaceState::kExploring);
    else if (!std::strcmp(emotion, "wake")) SetFace(WheelbotFaceState::kWake);
    else SetFace(WheelbotFaceFromEmotion(emotion));
}

void WheelbotOledDisplay::SetChatMessage(const char* role, const char* content) {
    if (!content || content[0] == '\0') return;
    if (role && !std::strcmp(role, "user")) SetFace(WheelbotFaceState::kThinking);
    else if (role && !std::strcmp(role, "assistant")) SetFace(WheelbotFaceState::kHappy);
}

void WheelbotOledDisplay::ClearChatMessages() {}

void WheelbotOledDisplay::SetFace(WheelbotFaceState face) {
    if (!lvgl_port_lock(30000)) return;
    face_ = face;
    animation_phase_ = 0;
    DrawFace();
    lvgl_port_unlock();
}

void WheelbotOledDisplay::AnimationTimer(lv_timer_t* timer) {
    auto* self = static_cast<WheelbotOledDisplay*>(lv_timer_get_user_data(timer));
    self->animation_phase_++;
    if (self->face_ == WheelbotFaceState::kIdle ||
        self->face_ == WheelbotFaceState::kListening ||
        self->face_ == WheelbotFaceState::kThinking ||
        self->face_ == WheelbotFaceState::kMoving ||
        self->face_ == WheelbotFaceState::kExploring) {
        self->DrawFace();
    }
}

void WheelbotOledDisplay::DrawFace() {
    if (!canvas_) return;
    lv_canvas_fill_bg(canvas_, lv_color_black(), LV_OPA_COVER);
    lv_layer_t layer;
    lv_canvas_init_layer(canvas_, &layer);
    const bool blink = face_ == WheelbotFaceState::kBlink ||
                       (face_ == WheelbotFaceState::kIdle && animation_phase_ % 24 == 23);

    if (blink || face_ == WheelbotFaceState::kSleep) {
        Line(&layer, 35, 24, 53, 24, 3);
        Line(&layer, 75, 24, 93, 24, 3);
    } else if (face_ == WheelbotFaceState::kHappy) {
        Line(&layer, 34, 25, 44, 17, 3); Line(&layer, 44, 17, 54, 25, 3);
        Line(&layer, 74, 25, 84, 17, 3); Line(&layer, 84, 17, 94, 25, 3);
    } else if (face_ == WheelbotFaceState::kMoving) {
        Line(&layer, 34, 20, 54, 26, 4); Line(&layer, 74, 26, 94, 20, 4);
    } else if (face_ == WheelbotFaceState::kThinking) {
        Rect(&layer, 36, 16, 10, 16, 5); Line(&layer, 75, 24, 94, 24, 3);
        Rect(&layer, 105, 13 + animation_phase_ % 3, 3, 3, 2);
        Rect(&layer, 112, 9 + animation_phase_ % 3, 3, 3, 2);
    } else {
        const int eye_h = face_ == WheelbotFaceState::kListening ? 18 : 13;
        Rect(&layer, 35, 17, 14, eye_h, 7); Rect(&layer, 79, 17, 14, eye_h, 7);
    }

    if (face_ == WheelbotFaceState::kWake || face_ == WheelbotFaceState::kListening) {
        Rect(&layer, 59, 37, 10, 8, 5);
    } else if (face_ == WheelbotFaceState::kHappy) {
        Line(&layer, 50, 37, 64, 45, 3); Line(&layer, 64, 45, 78, 37, 3);
    } else if (face_ == WheelbotFaceState::kLowBattery) {
        Line(&layer, 52, 42, 76, 42, 3);
        Rect(&layer, 104, 34, 16, 9, 1); Rect(&layer, 120, 37, 3, 3, 0);
        Rect(&layer, 106, 36, 3, 5, 0);
    } else if (face_ == WheelbotFaceState::kSleep) {
        Line(&layer, 54, 41, 74, 41, 2);
        Line(&layer, 101, 15, 112, 15, 2); Line(&layer, 112, 15, 101, 23, 2); Line(&layer, 101, 23, 112, 23, 2);
    } else if (face_ == WheelbotFaceState::kThinking) {
        Line(&layer, 55, 43, 75, 38, 3);
    } else {
        Line(&layer, 53, 39, 64, 44, 3); Line(&layer, 64, 44, 75, 39, 3);
    }

    if (face_ == WheelbotFaceState::kListening) {
        const int spread = 2 + animation_phase_ % 3;
        Line(&layer, 22 - spread, 20, 22 - spread, 32, 2);
        Line(&layer, 106 + spread, 20, 106 + spread, 32, 2);
    } else if (face_ == WheelbotFaceState::kMoving) {
        Line(&layer, 7, 17, 22, 17, 2); Line(&layer, 3, 25, 20, 25, 2);
        Line(&layer, 106, 17, 121, 17, 2); Line(&layer, 108, 25, 125, 25, 2);
    } else if (face_ == WheelbotFaceState::kExploring) {
        Line(&layer, 13, 26, 27, 26, 2); Line(&layer, 20, 19, 20, 33, 2);
        Rect(&layer, 17, 23, 7, 7, 4);
    }

    lv_canvas_finish_layer(canvas_, &layer);
    lv_obj_invalidate(canvas_);
}
