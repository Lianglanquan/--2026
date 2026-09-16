#include "wheelbot_esp32_core.h"

#include <math.h>
#include <string.h>

#define HEADER_SIZE 8U
#define CRC_SIZE 2U
#define COMMAND_TYPE 1U
#define WHEELBOT_PI 3.14159265358979323846f

static void put_u16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8U);
}

static uint16_t get_u16(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8U);
}

static void put_f32(uint8_t *p, float value)
{
    memcpy(p, &value, sizeof(value));
}

static float get_f32(const uint8_t *p)
{
    float value;
    memcpy(&value, p, sizeof(value));
    return value;
}

static float clamp_rpm(float value, float limit)
{
    if (value > limit) return limit;
    if (value < -limit) return -limit;
    return value;
}

int wheelbot_intent_to_command(const wheelbot_intent_t *intent,
                               const wheelbot_drive_config_t *config,
                               wheelbot_command_t *command)
{
    if (intent == NULL || config == NULL || command == NULL ||
        !isfinite(intent->vx_mps) || !isfinite(intent->yaw_rate_rps) ||
        !isfinite(config->wheel_radius_m) || !isfinite(config->track_width_m) ||
        !isfinite(config->max_wheel_rpm) || config->wheel_radius_m <= 0.0f ||
        config->track_width_m < 0.0f || config->max_wheel_rpm <= 0.0f) {
        return -1;
    }

    memset(command, 0, sizeof(*command));
    if (intent->stop != 0U || intent->mode == WHEELBOT_MODE_STOP) {
        return 0;
    }

    const float half_track = config->track_width_m * 0.5f;
    const float left_mps = intent->vx_mps - intent->yaw_rate_rps * half_track;
    const float right_mps = intent->vx_mps + intent->yaw_rate_rps * half_track;
    const float meters_to_rpm = 60.0f / (2.0f * WHEELBOT_PI * config->wheel_radius_m);

    command->enable = 1U;
    command->mode = intent->mode;
    command->wheel_command[0] = clamp_rpm(left_mps * meters_to_rpm,
                                           config->max_wheel_rpm);
    command->wheel_command[1] = clamp_rpm(right_mps * meters_to_rpm,
                                           config->max_wheel_rpm);
    return 0;
}

void wheelbot_intent_watchdog_init(wheelbot_intent_watchdog_t *watchdog,
                                   uint32_t timeout_ms)
{
    if (watchdog == NULL) return;
    memset(watchdog, 0, sizeof(*watchdog));
    watchdog->timeout_ms = timeout_ms;
}

int wheelbot_intent_watchdog_accept(wheelbot_intent_watchdog_t *watchdog,
                                    const wheelbot_intent_t *intent,
                                    uint32_t now_ms)
{
    if (watchdog == NULL || intent == NULL ||
        !isfinite(intent->vx_mps) || !isfinite(intent->yaw_rate_rps)) {
        return -1;
    }
    watchdog->latest = *intent;
    watchdog->accepted_at_ms = now_ms;
    watchdog->valid = 1U;
    return 0;
}

int wheelbot_intent_watchdog_expired(const wheelbot_intent_watchdog_t *watchdog,
                                     uint32_t now_ms)
{
    if (watchdog == NULL || watchdog->valid == 0U) return 1;
    return (uint32_t)(now_ms - watchdog->accepted_at_ms) >= watchdog->timeout_ms;
}

uint16_t wheelbot_crc16(const uint8_t *data, size_t length)
{
    uint16_t crc = 0xffffU;
    if (data == NULL) return 0U;
    for (size_t i = 0U; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8U;
        for (unsigned bit = 0U; bit < 8U; ++bit) {
            crc = (crc & 0x8000U) != 0U
                ? (uint16_t)((crc << 1U) ^ 0x1021U)
                : (uint16_t)(crc << 1U);
        }
    }
    return crc;
}

int wheelbot_encode_command_frame(uint16_t sequence,
                                  const wheelbot_command_t *command,
                                  uint8_t *frame, size_t capacity,
                                  size_t *frame_length)
{
    if (command == NULL || frame == NULL || frame_length == NULL ||
        capacity < WHEELBOT_COMMAND_FRAME_SIZE) return -1;
    frame[0] = WHEELBOT_PROTOCOL_MAGIC0;
    frame[1] = WHEELBOT_PROTOCOL_MAGIC1;
    frame[2] = WHEELBOT_PROTOCOL_VERSION;
    frame[3] = COMMAND_TYPE;
    put_u16(&frame[4], WHEELBOT_COMMAND_PAYLOAD_SIZE);
    put_u16(&frame[6], sequence);
    frame[8] = command->enable;
    frame[9] = command->mode;
    size_t offset = 10U;
    for (unsigned i = 0U; i < 4U; ++i, offset += 4U) put_f32(&frame[offset], command->joint_target[i]);
    for (unsigned i = 0U; i < 2U; ++i, offset += 4U) put_f32(&frame[offset], command->wheel_command[i]);
    put_u16(&frame[34], wheelbot_crc16(frame, 34U));
    *frame_length = WHEELBOT_COMMAND_FRAME_SIZE;
    return 0;
}

int wheelbot_decode_command_frame(const uint8_t *frame, size_t frame_length,
                                  uint16_t *sequence,
                                  wheelbot_command_t *command)
{
    if (frame == NULL || command == NULL || frame_length != WHEELBOT_COMMAND_FRAME_SIZE ||
        frame[0] != WHEELBOT_PROTOCOL_MAGIC0 || frame[1] != WHEELBOT_PROTOCOL_MAGIC1 ||
        frame[2] != WHEELBOT_PROTOCOL_VERSION || frame[3] != COMMAND_TYPE ||
        get_u16(&frame[4]) != WHEELBOT_COMMAND_PAYLOAD_SIZE ||
        wheelbot_crc16(frame, 34U) != get_u16(&frame[34])) return -1;
    if (sequence != NULL) *sequence = get_u16(&frame[6]);
    command->enable = frame[8];
    command->mode = frame[9];
    size_t offset = 10U;
    for (unsigned i = 0U; i < 4U; ++i, offset += 4U) command->joint_target[i] = get_f32(&frame[offset]);
    for (unsigned i = 0U; i < 2U; ++i, offset += 4U) command->wheel_command[i] = get_f32(&frame[offset]);
    return 0;
}
