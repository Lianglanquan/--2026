#include "wheelbot_ble.h"

#include "wheelbot_providers.h"

#include <math.h>
#include <string.h>

static float normalize_axis(int16_t value, int16_t full_scale)
{
    float result = (float)value / (float)full_scale;
    if (fabsf(result) < 0.10f) return 0.0f;
    if (result > 1.0f) return 1.0f;
    if (result < -1.0f) return -1.0f;
    return result;
}

int wheelbot_ble_report_to_intent(const wheelbot_ble_gamepad_report_t *report,
                                  int16_t axis_full_scale,
                                  float max_vx_mps,
                                  float max_yaw_rate_rps,
                                  wheelbot_intent_t *intent)
{
    if (report == NULL || intent == NULL || axis_full_scale <= 0 ||
        !isfinite(max_vx_mps) || !isfinite(max_yaw_rate_rps) ||
        max_vx_mps < 0.0f || max_yaw_rate_rps < 0.0f) return -1;
    memset(intent, 0, sizeof(*intent));
    intent->mode = WHEELBOT_MODE_DRIVE;
    intent->vx_mps = normalize_axis(report->y_axis, axis_full_scale) * max_vx_mps;
    intent->yaw_rate_rps = normalize_axis(report->x_axis, axis_full_scale) * max_yaw_rate_rps;
    if (report->stop_button != 0U) {
        intent->stop = 1U;
        intent->mode = WHEELBOT_MODE_STOP;
        intent->vx_mps = 0.0f;
        intent->yaw_rate_rps = 0.0f;
    }
    return 0;
}

int wheelbot_provider_submit_ble_report(wheelbot_input_router_t *router,
                                        const wheelbot_ble_gamepad_report_t *report,
                                        int16_t axis_full_scale,
                                        float max_vx_mps,
                                        float max_yaw_rate_rps,
                                        uint32_t now_ms)
{
    wheelbot_intent_t intent;
    if (wheelbot_ble_report_to_intent(report, axis_full_scale, max_vx_mps,
                                      max_yaw_rate_rps, &intent) != 0) return -1;
    return wheelbot_provider_submit_ble(router, &intent, now_ms);
}
