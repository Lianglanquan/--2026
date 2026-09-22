#ifndef WHEELBOT_FASHIONSTAR_UART_H
#define WHEELBOT_FASHIONSTAR_UART_H

#include <stdint.h>

#include "fashion_star_uart_servo.h"

/*
 * The C Board connector marked USART1 is wired to the MCU's USART6:
 * PG14 (TX) and PG9 (RX).  The mapping is taken from the C Board user
 * manual and the vendor DJI CubeMX-generated HAL project, not from the
 * connector label alone.
 */
#define WHEELBOT_FASHIONSTAR_UART_INSTANCE USART6
/* FashionStar factory default ID is 0; verify/change this in the servo
 * configuration before selecting another bus ID. */
#define WHEELBOT_FASHIONSTAR_DEFAULT_ID   0U

void wheelbot_fashionstar_init(void);

/* These wrappers intentionally expose the vendor SDK status type. */
FSUS_STATUS wheelbot_fashionstar_ping(uint8_t servo_id);
FSUS_STATUS wheelbot_fashionstar_read_status(uint8_t servo_id,
                                             uint8_t *status_value);

/* Last safe diagnostic results, updated only by explicit calls. */
extern volatile FSUS_STATUS wheelbot_fashionstar_last_ping;
extern volatile FSUS_STATUS wheelbot_fashionstar_last_status;
extern volatile uint8_t wheelbot_fashionstar_servo_status;

#endif
