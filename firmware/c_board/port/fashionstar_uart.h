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
#define WHEELBOT_HA8_COUNT 4U
#define WHEELBOT_HA8_LF_ID 1U
#define WHEELBOT_HA8_LR_ID 2U
#define WHEELBOT_HA8_RF_ID 3U
#define WHEELBOT_HA8_RR_ID 4U

void wheelbot_fashionstar_init(void);

/* These wrappers intentionally expose the vendor SDK status type. */
FSUS_STATUS wheelbot_fashionstar_ping(uint8_t servo_id);
FSUS_STATUS wheelbot_fashionstar_read_status(uint8_t servo_id,
                                             uint8_t *status_value);
FSUS_STATUS wheelbot_fashionstar_read_angle(uint8_t servo_id, float *angle_deg);
void wheelbot_fashionstar_submit_targets(const float target_deg[WHEELBOT_HA8_COUNT]);
void wheelbot_fashionstar_cancel_targets(void);
uint32_t wheelbot_fashionstar_take_targets(float target_deg[WHEELBOT_HA8_COUNT],
                                          uint8_t *active);
uint8_t wheelbot_fashionstar_targets_active(uint32_t generation);
void wheelbot_fashionstar_record_sample(unsigned index, float angle_deg,
                                        uint8_t status, uint32_t timestamp_ms);
void wheelbot_fashionstar_snapshot(float position_deg[WHEELBOT_HA8_COUNT],
                                   float velocity_dps[WHEELBOT_HA8_COUNT],
                                   uint8_t status[WHEELBOT_HA8_COUNT]);

/* Last safe diagnostic results, updated only by explicit calls. */
extern volatile FSUS_STATUS wheelbot_fashionstar_last_ping;
extern volatile FSUS_STATUS wheelbot_fashionstar_last_status;
extern volatile uint8_t wheelbot_fashionstar_servo_status;

#endif
