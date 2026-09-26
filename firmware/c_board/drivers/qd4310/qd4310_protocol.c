#include "qd4310_protocol.h"

#include <math.h>

#define QD4310_CONTROL_BASE 0x400u
#define QD4310_FEEDBACK_BASE 0x500u
#define QD4310_PI 3.14159265358979323846f

int qd4310_encode_control(const uint8_t id, const uint8_t command,
                          const int16_t control, qd4310_can_frame_t *frame) {
    if (frame == NULL || id > 0x0fu || command == 0x08u ||
        (command > QD4310_CMD_STEP_ANGLE && command != QD4310_CMD_REBOOT &&
         command != QD4310_CMD_SET_ZERO && command != QD4310_CMD_CLEAR_ERROR)) {
        return -1;
    }

    frame->std_id = (uint16_t)(QD4310_CONTROL_BASE + id);
    frame->dlc = 3u;
    frame->data[0] = command;
    frame->data[1] = (uint8_t)((uint16_t)control & 0xffu);
    frame->data[2] = (uint8_t)(((uint16_t)control >> 8) & 0xffu);
    return 0;
}

int qd4310_decode_feedback(const uint8_t id, const uint16_t std_id,
                           const uint8_t *data, const size_t length,
                           qd4310_state_t *state) {
    if (data == NULL || state == NULL || id > 0x0fu ||
        std_id != (uint16_t)(QD4310_FEEDBACK_BASE + id) || length != 8u) {
        return -1;
    }

    state->id = id;
    state->motor_state = data[0];
    state->enabled = (uint8_t)(data[0] & 0x01u);
    state->error_code = data[1];
    state->current_raw = (int16_t)((uint16_t)data[2] | ((uint16_t)data[3] << 8));
    state->speed_raw = (int16_t)((uint16_t)data[4] | ((uint16_t)data[5] << 8));
    state->angle_raw = (uint16_t)data[6] | ((uint16_t)data[7] << 8);
    state->current_a = (float)state->current_raw * 10.0f / 32767.0f;
    state->speed_rpm = (float)state->speed_raw * 1000.0f / 32767.0f;
    state->angle_rad = (float)state->angle_raw * (2.0f * QD4310_PI) / 65535.0f;
    return 0;
}
