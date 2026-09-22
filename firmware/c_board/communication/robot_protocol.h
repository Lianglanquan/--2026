#ifndef WHEELBOT_ROBOT_PROTOCOL_H
#define WHEELBOT_ROBOT_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define WHEELBOT_PROTOCOL_VERSION 1U
#define WHEELBOT_PROTOCOL_MAGIC0 ((uint8_t)'W')
#define WHEELBOT_PROTOCOL_MAGIC1 ((uint8_t)'B')
#define WHEELBOT_MAX_JOINTS 4U
#define WHEELBOT_MAX_WHEELS 2U
#define WHEELBOT_COMMAND_PAYLOAD_SIZE 26U
#define WHEELBOT_BATTERY_PAYLOAD_SIZE 8U

typedef enum {
    WHEELBOT_MSG_COMMAND = 1U,
    WHEELBOT_MSG_STATE = 2U,
    WHEELBOT_MSG_BATTERY = 3U,
} wheelbot_message_type_t;

typedef struct {
    uint8_t enable;
    uint8_t mode;
    float joint_target[WHEELBOT_MAX_JOINTS];
    float wheel_command[WHEELBOT_MAX_WHEELS];
} wheelbot_command_t;

typedef struct {
    uint32_t timestamp_ms;
    float gyro[3];
    float accel[3];
    float quaternion[4];
    float rpy[3];
    float joint_position[WHEELBOT_MAX_JOINTS];
    float joint_velocity[WHEELBOT_MAX_JOINTS];
    uint8_t joint_status[WHEELBOT_MAX_JOINTS];
    float wheel_position[WHEELBOT_MAX_WHEELS];
    float wheel_velocity[WHEELBOT_MAX_WHEELS];
    float wheel_current[WHEELBOT_MAX_WHEELS];
    uint32_t wheel_fault[WHEELBOT_MAX_WHEELS];
    float battery_voltage;
    uint32_t faults;
} wheelbot_state_t;

typedef struct {
    float voltage;
    uint16_t percentage;
} wheelbot_battery_t;

uint16_t wheelbot_crc16(const uint8_t *data, size_t length);
int wheelbot_encode_command(uint16_t sequence, const wheelbot_command_t *command,
                            uint8_t *frame, size_t capacity, size_t *frame_length);
int wheelbot_decode_command(const uint8_t *frame, size_t frame_length,
                            uint16_t *sequence, wheelbot_command_t *command);
int wheelbot_encode_state(uint16_t sequence, const wheelbot_state_t *state,
                          uint8_t *frame, size_t capacity, size_t *frame_length);
int wheelbot_decode_state(const uint8_t *frame, size_t frame_length,
                          uint16_t *sequence, wheelbot_state_t *state);
int wheelbot_encode_battery(uint16_t sequence, const wheelbot_battery_t *battery,
                            uint8_t *frame, size_t capacity, size_t *frame_length);
int wheelbot_decode_battery(const uint8_t *frame, size_t frame_length,
                            uint16_t *sequence, wheelbot_battery_t *battery);

#endif
