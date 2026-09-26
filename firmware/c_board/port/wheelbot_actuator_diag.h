#ifndef WHEELBOT_ACTUATOR_DIAG_H
#define WHEELBOT_ACTUATOR_DIAG_H

#include <stdint.h>
#include "qd4310_protocol.h"

void wheelbot_actuator_diag_task(void const *argument);
extern volatile qd4310_state_t wheelbot_qd4310_state;
extern volatile qd4310_state_t wheelbot_qd4310_states[QD4310_MOTOR_COUNT];
extern volatile uint8_t wheelbot_servo_status;

#endif
