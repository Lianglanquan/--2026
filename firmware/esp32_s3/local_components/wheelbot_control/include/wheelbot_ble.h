#ifndef WHEELBOT_BLE_H
#define WHEELBOT_BLE_H

#include "wheelbot_esp32_core.h"

typedef struct {
    int16_t x_axis;
    int16_t y_axis;
    uint8_t stop_button;
} wheelbot_ble_gamepad_report_t;

int wheelbot_ble_report_to_intent(const wheelbot_ble_gamepad_report_t *report,
                                  int16_t axis_full_scale,
                                  float max_vx_mps,
                                  float max_yaw_rate_rps,
                                  wheelbot_intent_t *intent);

int wheelbot_provider_submit_ble_report(wheelbot_input_router_t *router,
                                        const wheelbot_ble_gamepad_report_t *report,
                                        int16_t axis_full_scale,
                                        float max_vx_mps,
                                        float max_yaw_rate_rps,
                                        uint32_t now_ms);

#endif
