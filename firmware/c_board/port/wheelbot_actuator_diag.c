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
    /* Explicit bench test only: configured IDs, low current, then stop. */
    for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
        (void)qd4310_enable((uint8_t)(QD4310_MOTOR_ID_1 + i));
    }
    osDelay(100U);
    for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
        (void)qd4310_set_current((uint8_t)(QD4310_MOTOR_ID_1 + i), 0.2f);
    }
    osDelay(2000U);
    for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
        const uint8_t id = (uint8_t)(QD4310_MOTOR_ID_1 + i);
        (void)qd4310_set_current(id, 0.0f);
        (void)qd4310_disable(id);
    }
#endif

    for (;;) {
        /* NOP requests feedback only; no enable or motion command is sent. */
        for (unsigned i = 0U; i < QD4310_MOTOR_COUNT; ++i) {
            (void)qd4310_get_state((uint8_t)(QD4310_MOTOR_ID_1 + i),
                                   (qd4310_state_t *)&wheelbot_qd4310_states[i]);
        }
        wheelbot_qd4310_state = wheelbot_qd4310_states[0];
        osDelay(100U);
    }
}
