#include "fashionstar_uart.h"

#include "usart.h"
#include "user_uart.h"
#include "FreeRTOS.h"
#include "task.h"
#include <string.h>

volatile FSUS_STATUS wheelbot_fashionstar_last_ping = FSUS_STATUS_TIMEOUT;
volatile FSUS_STATUS wheelbot_fashionstar_last_status = FSUS_STATUS_TIMEOUT;
volatile uint8_t wheelbot_fashionstar_servo_status = 0U;
static float joint_position[WHEELBOT_HA8_COUNT];
static float joint_velocity[WHEELBOT_HA8_COUNT];
static uint8_t joint_status[WHEELBOT_HA8_COUNT] = {255U, 255U, 255U, 255U};
static float joint_targets[WHEELBOT_HA8_COUNT];
static uint32_t target_generation;
static uint8_t target_active;
static uint32_t last_sample[WHEELBOT_HA8_COUNT];

void wheelbot_fashionstar_submit_targets(const float targets[WHEELBOT_HA8_COUNT])
{
    if (targets == NULL) return;
    taskENTER_CRITICAL();
    memcpy(joint_targets, targets, sizeof(joint_targets));
    ++target_generation;
    target_active = 1U;
    taskEXIT_CRITICAL();
}

void wheelbot_fashionstar_cancel_targets(void)
{
    taskENTER_CRITICAL();
    target_active = 0U;
    ++target_generation;
    taskEXIT_CRITICAL();
}

uint32_t wheelbot_fashionstar_take_targets(float targets[WHEELBOT_HA8_COUNT],
                                           uint8_t *active)
{
    uint32_t generation;
    taskENTER_CRITICAL();
    generation = target_generation;
    memcpy(targets, joint_targets, sizeof(joint_targets));
    *active = target_active;
    taskEXIT_CRITICAL();
    return generation;
}

uint8_t wheelbot_fashionstar_targets_active(uint32_t generation)
{
    uint8_t active;
    taskENTER_CRITICAL();
    active = target_active && generation == target_generation;
    taskEXIT_CRITICAL();
    return active;
}

void wheelbot_fashionstar_record_sample(unsigned index, float angle,
                                        uint8_t status, uint32_t now)
{
    if (index >= WHEELBOT_HA8_COUNT) return;
    taskENTER_CRITICAL();
    if (status != 255U && last_sample[index] != 0U && now != last_sample[index]) {
        joint_velocity[index] = 1000.0f * (angle - joint_position[index]) /
                                (float)(now - last_sample[index]);
    }
    if (status != 255U) {
        joint_position[index] = angle;
        last_sample[index] = now;
    }
    joint_status[index] = status;
    taskEXIT_CRITICAL();
}

void wheelbot_fashionstar_snapshot(float positions[WHEELBOT_HA8_COUNT],
                                   float velocities[WHEELBOT_HA8_COUNT],
                                   uint8_t statuses[WHEELBOT_HA8_COUNT])
{
    taskENTER_CRITICAL();
    memcpy(positions, joint_position, sizeof(joint_position));
    memcpy(velocities, joint_velocity, sizeof(joint_velocity));
    memcpy(statuses, joint_status, sizeof(joint_status));
    taskEXIT_CRITICAL();
}

FSUS_STATUS wheelbot_fashionstar_read_angle(uint8_t servo_id, float *angle_deg)
{
    if (angle_deg == NULL) return FSUS_STATUS_FAIL;
    return FSUS_QueryServoAngle(&FSUS_Usart, servo_id, angle_deg);
}

void wheelbot_fashionstar_init(void)
{
    /* Reuse the official SDK's ring buffers and interrupt receive path. */
    User_Uart_Init(&huart6);
}

FSUS_STATUS wheelbot_fashionstar_ping(uint8_t servo_id)
{
    wheelbot_fashionstar_last_ping = FSUS_Ping(&FSUS_Usart, servo_id);
    return wheelbot_fashionstar_last_ping;
}

FSUS_STATUS wheelbot_fashionstar_read_status(uint8_t servo_id,
                                             uint8_t *status_value)
{
    uint8_t size = 0U;
    uint8_t value[1] = {0U};

    if (status_value == (uint8_t *)0)
    {
        wheelbot_fashionstar_last_status = FSUS_STATUS_FAIL;
        return wheelbot_fashionstar_last_status;
    }

    wheelbot_fashionstar_last_status =
        FSUS_ReadData(&FSUS_Usart, servo_id, FSUS_PARAM_SERVO_STATUS,
                      value, &size);
    if ((wheelbot_fashionstar_last_status == FSUS_STATUS_SUCCESS) &&
        (size == 1U))
    {
        *status_value = value[0];
        wheelbot_fashionstar_servo_status = value[0];
    }
    return wheelbot_fashionstar_last_status;
}
