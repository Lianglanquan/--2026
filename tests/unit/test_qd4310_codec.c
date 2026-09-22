#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "qd4310_protocol.h"

#define QD4310_PI 3.14159265358979323846f

static void test_enable_frame(void) {
    qd4310_can_frame_t frame;
    assert(qd4310_encode_control(1u, QD4310_CMD_ENABLE, 0, &frame) == 0);
    assert(frame.std_id == 0x401u);
    assert(frame.dlc == 3u);
    assert(frame.data[0] == QD4310_CMD_ENABLE);
    assert(frame.data[1] == 0u && frame.data[2] == 0u);
}

static void test_signed_control_is_little_endian(void) {
    qd4310_can_frame_t frame;
    assert(qd4310_encode_control(0x0fu, QD4310_CMD_CURRENT, -1234, &frame) == 0);
    assert(frame.std_id == 0x40fu);
    assert(frame.data[0] == QD4310_CMD_CURRENT);
    assert(frame.data[1] == 0x2eu && frame.data[2] == 0xfbu);
}

static void test_official_speed_and_angle_frames(void) {
    qd4310_can_frame_t frame;
    assert(qd4310_encode_control(1u, QD4310_CMD_SPEED, 8192, &frame) == 0);
    assert(frame.std_id == 0x401u && frame.dlc == 3u);
    assert(frame.data[0] == 0x04u && frame.data[1] == 0x00u && frame.data[2] == 0x20u);
    assert(qd4310_encode_control(1u, QD4310_CMD_ANGLE, (int16_t)5218, &frame) == 0);
    assert(frame.data[0] == 0x05u && frame.data[1] == 0x62u && frame.data[2] == 0x14u);
}

static void test_feedback_decode(void) {
    const uint8_t payload[8] = {
        0x12u, 0x02u,       /* state, error */
        0x00u, 0x40u,       /* current raw = 16384 */
        0x00u, 0x80u,       /* speed raw = -32768 */
        0x00u, 0x20u        /* angle raw = 8192 */
    };
    qd4310_state_t state;
    assert(qd4310_decode_feedback(1u, 0x501u, payload, sizeof(payload), &state) == 0);
    assert(state.id == 1u);
    assert(state.motor_state == 0x12u);
    assert(state.error_code == 0x02u);
    assert(state.current_raw == 16384);
    assert(state.speed_raw == -32768);
    assert(state.angle_raw == 8192u);
    assert(fabsf(state.current_a - (16384.0f * 10.0f / 32767.0f)) < 1e-5f);
    assert(fabsf(state.speed_rpm - (-32768.0f * 1000.0f / 32767.0f)) < 1e-5f);
    assert(fabsf(state.angle_rad - (8192.0f * 2.0f * QD4310_PI / 65535.0f)) < 1e-5f);
}

static void test_bad_feedback_is_rejected(void) {
    const uint8_t payload[8] = {0};
    qd4310_state_t state;
    assert(qd4310_decode_feedback(1u, 0x400u, payload, sizeof(payload), &state) != 0);
    assert(qd4310_decode_feedback(1u, 0x501u, payload, 7u, &state) != 0);
}

int main(void) {
    test_enable_frame();
    test_signed_control_is_little_endian();
    test_official_speed_and_angle_frames();
    test_feedback_decode();
    test_bad_feedback_is_rejected();
    puts("qd4310 codec tests: ok");
    return 0;
}
