#include "uart_robot_protocol.h"
#include "robot_protocol.h"

#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

static int received;
static wheelbot_command_t last_command;

void wheelbot_robot_command_apply(const void *value)
{
    received++;
    last_command = *(const wheelbot_command_t *)value;
}

int main(void)
{
    wheelbot_command_t command;
    memset(&command, 0, sizeof(command));
    command.enable = 1U;
    command.mode = 2U;
    command.wheel_command[0] = 11.0f;
    command.wheel_command[1] = 12.0f;
    uint8_t frame[36];
    size_t length = 0U;
    assert(wheelbot_encode_command(9U, &command, frame, sizeof(frame), &length) == 0);

    wheelbot_uart_robot_protocol_t parser;
    wheelbot_uart_robot_protocol_init(&parser);
    for (size_t i = 0U; i < length; ++i) {
        assert(wheelbot_uart_robot_protocol_feed(&parser, &frame[i], 1U) == 0);
    }
    assert(received == 1);
    assert(last_command.wheel_command[1] == 12.0f);

    frame[length - 1U] ^= 1U;
    assert(wheelbot_uart_robot_protocol_feed(&parser, frame, length) == 0);
    assert(received == 1);
    return 0;
}
