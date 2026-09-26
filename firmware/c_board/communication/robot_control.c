#include "robot_control.h"
#include "usb_robot_protocol.h"
#include "wheelbot_actuator_diag.h"
#include "qd4310.h"
#include "fashionstar_uart.h"
#include "INS_task.h"
#include "voltage_task.h"
#include "usbd_cdc_if.h"
#include "cmsis_os.h"
#include "main.h"
#include <string.h>
#include "FreeRTOS.h"
#include "task.h"

extern float battery_voltage;
static volatile wheelbot_command_t pending_command;
static volatile uint32_t command_generation;
static uint16_t state_sequence;

void wheelbot_robot_command_apply(const void *value)
{
    const wheelbot_command_t *command = (const wheelbot_command_t *)value;
    if (command != NULL) {
        pending_command = *command;
        ++command_generation;
    }
}

static void apply_command(uint32_t *applied_generation)
{
    wheelbot_command_t command;
    uint32_t generation;
    taskENTER_CRITICAL();
    generation = command_generation;
    command = pending_command;
    taskEXIT_CRITICAL();
    if (generation == *applied_generation) return;
    if (command.enable == 0U || command.mode == WHEELBOT_MODE_IDLE) {
        HAL_StatusTypeDef result = HAL_OK;
        wheelbot_fashionstar_cancel_targets();
        for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
            const uint8_t id = (uint8_t)(QD4310_MOTOR_ID_1 + i);
            if (qd4310_set_speed(id, 0.0f) != HAL_OK) result = HAL_ERROR;
            if (qd4310_disable(id) != HAL_OK) result = HAL_ERROR;
        }
        if (result == HAL_OK) *applied_generation = generation;
        return;
    }
    HAL_StatusTypeDef result = HAL_OK;
    if (command.mode == WHEELBOT_MODE_WHEEL || command.mode == WHEELBOT_MODE_COMBINED) {
        for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
            const uint8_t id = (uint8_t)(QD4310_MOTOR_ID_1 + i);
            if (qd4310_enable(id) != HAL_OK) result = HAL_ERROR;
            if (qd4310_set_speed(id, command.wheel_command[i]) != HAL_OK) result = HAL_ERROR;
        }
    } else {
        for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
            const uint8_t id = (uint8_t)(QD4310_MOTOR_ID_1 + i);
            if (qd4310_set_speed(id, 0.0f) != HAL_OK) result = HAL_ERROR;
            if (qd4310_disable(id) != HAL_OK) result = HAL_ERROR;
        }
    }
    if (result != HAL_OK) return;
    if (command.mode == WHEELBOT_MODE_JOINT || command.mode == WHEELBOT_MODE_COMBINED) {
        wheelbot_fashionstar_submit_targets(command.joint_target);
    } else {
        wheelbot_fashionstar_cancel_targets();
    }
    *applied_generation = generation;
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
    if (gyro == NULL || accel == NULL || quat == NULL || rpy == NULL) {
        state->faults |= WHEELBOT_FAULT_IMU;
    }
    wheelbot_fashionstar_snapshot(state->joint_position, state->joint_velocity,
                                  state->joint_status);
    for (unsigned i = 0U; i < WHEELBOT_HA8_COUNT; ++i) {
        if (state->joint_status[i] == 255U) state->faults |= WHEELBOT_FAULT_HA8(i);
    }
    for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
        state->wheel_position[i] = wheelbot_qd4310_states[i].angle_rad;
        state->wheel_velocity[i] = wheelbot_qd4310_states[i].speed_rpm;
        state->wheel_current[i] = wheelbot_qd4310_states[i].current_a;
        state->wheel_fault[i] = wheelbot_qd4310_states[i].error_code;
        if (qd4310_feedback_valid((uint8_t)(QD4310_MOTOR_ID_1 + i)) == 0U ||
            state->wheel_fault[i] != 0U) state->faults |= WHEELBOT_FAULT_QD4310(i);
    }
    state->battery_voltage = battery_voltage;
}

void wheelbot_robot_control_task(void const *argument)
{
    (void)argument;
    uint32_t applied_generation = 0U;
    for (;;) {
        apply_command(&applied_generation);
        wheelbot_state_t state;
        uint8_t frame[160]; size_t length = 0U;
        fill_state(&state);
        if (wheelbot_encode_state(state_sequence++, &state, frame, sizeof(frame), &length) == 0) {
            (void)CDC_Transmit_FS(frame, (uint16_t)length);
        }
        osDelay(20U);
    }
}
