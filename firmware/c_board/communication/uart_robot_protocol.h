#ifndef WHEELBOT_UART_ROBOT_PROTOCOL_H
#define WHEELBOT_UART_ROBOT_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define WHEELBOT_UART_PROTOCOL_BUFFER_SIZE 64U

typedef struct {
    uint8_t buffer[WHEELBOT_UART_PROTOCOL_BUFFER_SIZE];
    size_t length;
} wheelbot_uart_robot_protocol_t;

void wheelbot_uart_robot_protocol_init(wheelbot_uart_robot_protocol_t *parser);
int wheelbot_uart_robot_protocol_feed(wheelbot_uart_robot_protocol_t *parser,
                                      const uint8_t *data, size_t length);

/* Application overrides this weak hook, shared with the USB command path. */
void wheelbot_robot_command_apply(const void *command);

#endif
