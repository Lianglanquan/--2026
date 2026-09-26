#include "usb_robot_protocol.h"
#include "robot_protocol.h"
#include "uart_robot_protocol.h"

static wheelbot_uart_robot_protocol_t usb_parser;

__attribute__((weak)) void wheelbot_robot_command_apply(const void *command)
{
    (void)command;
}

void wheelbot_usb_robot_protocol_receive(const uint8_t *data, size_t length)
{
    (void)wheelbot_uart_robot_protocol_feed(&usb_parser, data, length);
}
