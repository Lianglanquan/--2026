#include "usb_robot_protocol.h"
#include "robot_protocol.h"

__attribute__((weak)) void wheelbot_robot_command_apply(const void *command)
{
    (void)command;
}

void wheelbot_usb_robot_protocol_receive(const uint8_t *data, size_t length)
{
    wheelbot_command_t command;
    if (wheelbot_decode_command(data, length, NULL, &command) == 0) {
        wheelbot_robot_command_apply(&command);
    }
}
