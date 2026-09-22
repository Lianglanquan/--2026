#include "wheelbot_esp32_core.h"

#include <stdio.h>
#include <string.h>

static void clear_intent(wheelbot_intent_t *intent)
{
    memset(intent, 0, sizeof(*intent));
    intent->mode = WHEELBOT_MODE_DRIVE;
}

int wheelbot_parse_voice_command(const char *text, wheelbot_intent_t *intent)
{
    if (text == NULL || intent == NULL) return -1;
    clear_intent(intent);
    if (strcmp(text, "停止") == 0 || strcmp(text, "stop") == 0) {
        intent->stop = 1U;
        intent->mode = WHEELBOT_MODE_STOP;
    } else if (strcmp(text, "前进") == 0 || strcmp(text, "forward") == 0) {
        intent->vx_mps = 0.25f;
    } else if (strcmp(text, "后退") == 0 || strcmp(text, "backward") == 0) {
        intent->vx_mps = -0.25f;
    } else if (strcmp(text, "左转") == 0 || strcmp(text, "left") == 0) {
        intent->yaw_rate_rps = 0.8f;
    } else if (strcmp(text, "右转") == 0 || strcmp(text, "right") == 0) {
        intent->yaw_rate_rps = -0.8f;
    } else if (strcmp(text, "趴下") == 0 || strcmp(text, "crouch") == 0) {
        intent->mode = 3U; /* Pose mode is reserved for the C Board adapter. */
    } else {
        return -1;
    }
    return 0;
}

int wheelbot_parse_control_text(const char *text, wheelbot_intent_t *intent)
{
    if (text == NULL || intent == NULL) return -1;
    clear_intent(intent);
    float vx = 0.0f;
    float yaw = 0.0f;
    unsigned mode = WHEELBOT_MODE_DRIVE;
    unsigned stop = 0U;
    if (sscanf(text, "vx=%f;yaw_rate=%f;mode=%u;stop=%u", &vx, &yaw, &mode, &stop) != 4) {
        return -1;
    }
    intent->vx_mps = vx;
    intent->yaw_rate_rps = yaw;
    intent->mode = (uint8_t)mode;
    intent->stop = stop != 0U ? 1U : 0U;
    if (intent->stop != 0U) intent->mode = WHEELBOT_MODE_STOP;
    return 0;
}
