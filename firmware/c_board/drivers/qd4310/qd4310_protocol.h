#ifndef WHEELBOT_QD4310_PROTOCOL_H
#define WHEELBOT_QD4310_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

/* QDrive's official QD4310 CAN protocol (classic CAN, 1 Mbps). */
enum qd4310_command {
    QD4310_CMD_NOP = 0x00,
    QD4310_CMD_ENABLE = 0x01,
    QD4310_CMD_DISABLE = 0x02,
    QD4310_CMD_CURRENT = 0x03,
    QD4310_CMD_SPEED = 0x04,
    QD4310_CMD_ANGLE = 0x05,
    QD4310_CMD_LOW_SPEED = 0x06,
    QD4310_CMD_STEP_ANGLE = 0x07,
    QD4310_CMD_REBOOT = 0xff,
    QD4310_CMD_SET_ZERO = 0xfe,
    QD4310_CMD_CLEAR_ERROR = 0xfb
};

typedef struct {
    uint16_t std_id;
    uint8_t dlc;
    uint8_t data[8];
} qd4310_can_frame_t;

typedef struct {
    uint8_t id;
    uint8_t motor_state;
    uint8_t error_code;
    int16_t current_raw;
    int16_t speed_raw;
    uint16_t angle_raw;
    float current_a;
    float speed_rpm;
    float angle_rad;
} qd4310_state_t;

int qd4310_encode_control(uint8_t id, uint8_t command, int16_t control,
                          qd4310_can_frame_t *frame);
int qd4310_decode_feedback(uint8_t id, uint16_t std_id, const uint8_t *data,
                           size_t length, qd4310_state_t *state);

#endif
