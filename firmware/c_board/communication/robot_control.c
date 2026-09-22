#include "robot_control.h"
#include "usb_robot_protocol.h"
#include "wheelbot_actuator_diag.h"
#include "qd4310.h"
#include "INS_task.h"
#include "voltage_task.h"
#include "usbd_cdc_if.h"
#include "cmsis_os.h"
#include "main.h"
#include <string.h>

extern float battery_voltage;
static volatile wheelbot_command_t pending_command;
static volatile uint32_t command_tick;
static uint16_t state_sequence;

void wheelbot_robot_command_apply(const void *value)
{
    const wheelbot_command_t *command = (const wheelbot_command_t *)value;
    if (command != NULL) {
        pending_command = *command;
        command_tick = HAL_GetTick();
    }
}

static void apply_command(void)
{
    wheelbot_command_t command = pending_command;
    const uint32_t age = HAL_GetTick() - command_tick;
    if (age > 200U || command.enable == 0U) {
        (void)qd4310_set_speed(1U, 0.0f);
        (void)qd4310_disable(1U);
        return;
    }
    /* Mode 2 is the first real actuator mode: wheel velocity in rpm. */
    if (command.mode == 2U) {
        (void)qd4310_enable(1U);
        (void)qd4310_set_speed(1U, command.wheel_command[0]);
    } else {
        (void)qd4310_set_speed(1U, 0.0f);
        (void)qd4310_disable(1U);
    }
}

static void fill_state(wheelbot_state_t *state)
{
    const float *gyro = get_gyro_data_point();
    const float *accel = get_accel_data_point();
    const float *quat = get_INS_quat_point();
    const float *rpy = get_INS_angle_point();
    memset(state, 0, sizeof(*state));
    state->timestamp_ms = HAL_GetTick();
    if (gyro != NULL) memcpy(state->gyro, gyro, sizeof(state->gyro));
    if (accel != NULL) memcpy(state->accel, accel, sizeof(state->accel));
    if (quat != NULL) memcpy(state->quaternion, quat, sizeof(state->quaternion));
    if (rpy != NULL) memcpy(state->rpy, rpy, sizeof(state->rpy));
    state->wheel_position[0] = wheelbot_qd4310_state.angle_rad;
    state->wheel_velocity[0] = wheelbot_qd4310_state.speed_rpm;
    state->wheel_current[0] = wheelbot_qd4310_state.current_a;
    state->wheel_fault[0] = wheelbot_qd4310_state.error_code;
    state->joint_status[0] = wheelbot_servo_status;
    state->battery_voltage = battery_voltage;
}

void wheelbot_robot_control_task(void const *argument)
{
    (void)argument;
    for (;;) {
        apply_command();
        wheelbot_state_t state;
        uint8_t frame[160]; size_t length = 0U;
        fill_state(&state);
        if (wheelbot_encode_state(state_sequence++, &state, frame, sizeof(frame), &length) == 0) {
            (void)CDC_Transmit_FS(frame, (uint16_t)length);
        }
        osDelay(20U);
    }
}
