#ifndef WHEELBOT_QD4310_H
#define WHEELBOT_QD4310_H

#include "main.h"
#include "qd4310_protocol.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Sends official QD4310 control frames on the existing C Board CAN1. */
HAL_StatusTypeDef qd4310_enable(uint8_t id);
HAL_StatusTypeDef qd4310_disable(uint8_t id);
HAL_StatusTypeDef qd4310_set_current(uint8_t id, float current_a);
HAL_StatusTypeDef qd4310_set_speed(uint8_t id, float speed_rpm);
HAL_StatusTypeDef qd4310_set_angle(uint8_t id, float angle_rad);
HAL_StatusTypeDef qd4310_get_state(uint8_t id, qd4310_state_t *state);
uint8_t qd4310_feedback_valid(uint8_t id);

/* Call from the existing HAL CAN1 RX callback for 0x500 + id feedback. */
void qd4310_handle_can_rx(uint16_t std_id, const uint8_t *data, uint8_t length);

#ifdef __cplusplus
}
#endif

#endif
