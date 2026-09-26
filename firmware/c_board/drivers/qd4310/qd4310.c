#include "qd4310.h"

#include <string.h>

#include "can.h"
#include "FreeRTOS.h"
#include "task.h"

#define QD4310_MAX_ID 0x0fu
#define QD4310_PI 3.14159265358979323846f

static qd4310_state_t qd4310_states[QD4310_MAX_ID + 1u];
static uint8_t qd4310_state_valid[QD4310_MAX_ID + 1u];
static uint32_t qd4310_last_feedback_ms[QD4310_MAX_ID + 1u];

static int16_t qd4310_clamp_i16(const float value) {
    if (value >= 32767.0f) return 32767;
    if (value <= -32768.0f) return -32768;
    return (int16_t)value;
}

static HAL_StatusTypeDef qd4310_send(const uint8_t id, const uint8_t command,
                                     const int16_t control) {
    qd4310_can_frame_t frame;
    CAN_TxHeaderTypeDef header;
    uint32_t mailbox;

    if (qd4310_encode_control(id, command, control, &frame) != 0) {
        return HAL_ERROR;
    }
    memset(&header, 0, sizeof(header));
    header.StdId = frame.std_id;
    header.IDE = CAN_ID_STD;
    header.RTR = CAN_RTR_DATA;
    header.DLC = frame.dlc;
    for (unsigned attempt = 0U; attempt < 5U; ++attempt) {
        taskENTER_CRITICAL();
        const HAL_StatusTypeDef result = HAL_CAN_AddTxMessage(&hcan1, &header,
                                                               frame.data, &mailbox);
        taskEXIT_CRITICAL();
        if (result == HAL_OK) return HAL_OK;
        vTaskDelay(1U);
    }
    return HAL_ERROR;
}

HAL_StatusTypeDef qd4310_enable(const uint8_t id) {
    return qd4310_send(id, QD4310_CMD_ENABLE, 0);
}

HAL_StatusTypeDef qd4310_disable(const uint8_t id) {
    return qd4310_send(id, QD4310_CMD_DISABLE, 0);
}

HAL_StatusTypeDef qd4310_set_current(const uint8_t id, const float current_a) {
    return qd4310_send(id, QD4310_CMD_CURRENT,
                       qd4310_clamp_i16(current_a * 32767.0f / 10.0f));
}

HAL_StatusTypeDef qd4310_set_speed(const uint8_t id, const float speed_rpm) {
    return qd4310_send(id, QD4310_CMD_SPEED,
                       qd4310_clamp_i16(speed_rpm * 32767.0f / 1000.0f));
}

HAL_StatusTypeDef qd4310_set_angle(const uint8_t id, const float angle_rad) {
    /* The official HAL example clamps absolute angle to [0, 2*pi]. */
    float normalized = angle_rad;
    if (normalized < 0.0f) normalized = 0.0f;
    if (normalized > 2.0f * QD4310_PI) normalized = 2.0f * QD4310_PI;
    return qd4310_send(id, QD4310_CMD_ANGLE,
                       (int16_t)(normalized * 65535.0f / (2.0f * QD4310_PI)));
}

HAL_StatusTypeDef qd4310_get_state(const uint8_t id, qd4310_state_t *state) {
    const HAL_StatusTypeDef status = qd4310_send(id, QD4310_CMD_NOP, 0);
    if (state != NULL) {
        if (id <= QD4310_MAX_ID && qd4310_state_valid[id] != 0u) {
            *state = qd4310_states[id];
        } else {
            memset(state, 0, sizeof(*state));
            state->id = id;
        }
    }
    return status;
}

uint8_t qd4310_feedback_valid(const uint8_t id) {
    return id <= QD4310_MAX_ID && qd4310_state_valid[id] &&
           (HAL_GetTick() - qd4310_last_feedback_ms[id] <= 500U);
}

void qd4310_handle_can_rx(const uint16_t std_id, const uint8_t *data,
                          const uint8_t length) {
    qd4310_state_t state;
    if (std_id < 0x500u || std_id > 0x50fu || data == NULL || length != 8u) {
        return;
    }
    const uint8_t id = (uint8_t)(std_id - 0x500u);
    if (qd4310_decode_feedback(id, std_id, data, length, &state) == 0) {
        qd4310_states[id] = state;
        qd4310_last_feedback_ms[id] = HAL_GetTick();
        qd4310_state_valid[id] = 1u;
    }
}
