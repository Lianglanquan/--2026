#include "wheelbot_actuator_diag.h"

#include "cmsis_os.h"
#include "qd4310.h"

volatile qd4310_state_t wheelbot_qd4310_state;
volatile uint8_t wheelbot_servo_status;

void wheelbot_actuator_diag_task(void const *argument)
{
    (void)argument;

#if defined(WHEELBOT_QD4310_TEST)
    /* One-shot bench test: enable ID1, apply only 0.2 A, then disable. */
    (void)qd4310_enable(1U);
    osDelay(100U);
    (void)qd4310_set_current(1U, 0.2f);
    osDelay(2000U);
    (void)qd4310_set_current(1U, 0.0f);
    (void)qd4310_disable(1U);
#endif

    for (;;) {
        /* NOP requests feedback only; no enable or motion command is sent. */
        (void)qd4310_get_state(1U, (qd4310_state_t *)&wheelbot_qd4310_state);
        osDelay(1000U);
    }
}
