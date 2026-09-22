#include "fashionstar_uart.h"

#include "usart.h"
#include "user_uart.h"

volatile FSUS_STATUS wheelbot_fashionstar_last_ping = FSUS_STATUS_TIMEOUT;
volatile FSUS_STATUS wheelbot_fashionstar_last_status = FSUS_STATUS_TIMEOUT;
volatile uint8_t wheelbot_fashionstar_servo_status = 0U;

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
