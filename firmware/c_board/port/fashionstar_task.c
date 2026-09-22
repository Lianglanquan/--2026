#include "fashionstar_task.h"

#include "cmsis_os.h"
#include "fashionstar_uart.h"

/* Diagnostics only: no angle, wheel, damping, or origin commands are sent. */
void wheelbot_fashionstar_task(void const *argument)
{
    (void)argument;
    wheelbot_fashionstar_init();

    for (;;)
    {
        (void)wheelbot_fashionstar_ping(WHEELBOT_FASHIONSTAR_DEFAULT_ID);
        (void)wheelbot_fashionstar_read_status(
            WHEELBOT_FASHIONSTAR_DEFAULT_ID,
            (uint8_t *)&wheelbot_fashionstar_servo_status);
        osDelay(1000U);
    }
}
