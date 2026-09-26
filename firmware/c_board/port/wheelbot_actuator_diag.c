#include "wheelbot_actuator_diag.h"

#include "cmsis_os.h"
#include "qd4310.h"

volatile qd4310_state_t wheelbot_qd4310_state;
volatile qd4310_state_t wheelbot_qd4310_states[QD4310_MOTOR_COUNT];
volatile uint8_t wheelbot_servo_status;

void wheelbot_actuator_diag_task(void const *argument)
{
    (void)argument;

#if defined(WHEELBOT_QD4310_TEST)
    /* Explicit bench test only: both commissioned IDs, low current, then stop. */
    (void)qd4310_enable(QD4310_MOTOR_ID_1);
    (void)qd4310_enable(QD4310_MOTOR_ID_2);
    osDelay(100U);
    (void)qd4310_set_current(QD4310_MOTOR_ID_1, 0.2f);
    (void)qd4310_set_current(QD4310_MOTOR_ID_2, 0.2f);
    osDelay(2000U);
    (void)qd4310_set_current(QD4310_MOTOR_ID_1, 0.0f);
    (void)qd4310_set_current(QD4310_MOTOR_ID_2, 0.0f);
    (void)qd4310_disable(QD4310_MOTOR_ID_1);
    (void)qd4310_disable(QD4310_MOTOR_ID_2);
#endif

    for (;;) {
        /* NOP requests feedback only; no enable or motion command is sent. */
        (void)qd4310_get_state(QD4310_MOTOR_ID_1, (qd4310_state_t *)&wheelbot_qd4310_states[0]);
        (void)qd4310_get_state(QD4310_MOTOR_ID_2, (qd4310_state_t *)&wheelbot_qd4310_states[1]);
        wheelbot_qd4310_state = wheelbot_qd4310_states[0];
        osDelay(1000U);
    }
}
