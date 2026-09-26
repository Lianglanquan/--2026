#include "uart_robot_protocol.h"

#include "robot_protocol.h"

#include <string.h>

#define FRAME_HEADER_SIZE 8U
#define FRAME_CRC_SIZE 2U
#define FRAME_MAX_SIZE (FRAME_HEADER_SIZE + WHEELBOT_COMMAND_PAYLOAD_SIZE + FRAME_CRC_SIZE)

__attribute__((weak)) void wheelbot_robot_command_apply(const void *command)
{
    (void)command;
}

void wheelbot_uart_robot_protocol_init(wheelbot_uart_robot_protocol_t *parser)
{
    if (parser != NULL) memset(parser, 0, sizeof(*parser));
}

static void discard_until_magic(wheelbot_uart_robot_protocol_t *parser)
{
    size_t index = 0U;
    while (index < parser->length && parser->buffer[index] != WHEELBOT_PROTOCOL_MAGIC0) ++index;
    if (index != 0U) {
        memmove(parser->buffer, &parser->buffer[index], parser->length - index);
        parser->length -= index;
    }
    while (parser->length >= 2U && parser->buffer[1] != WHEELBOT_PROTOCOL_MAGIC1) {
        memmove(parser->buffer, &parser->buffer[1], --parser->length);
        index = 0U;
        while (index < parser->length && parser->buffer[index] != WHEELBOT_PROTOCOL_MAGIC0) ++index;
        if (index != 0U) {
            memmove(parser->buffer, &parser->buffer[index], parser->length - index);
            parser->length -= index;
        }
    }
}

int wheelbot_uart_robot_protocol_feed(wheelbot_uart_robot_protocol_t *parser,
                                      const uint8_t *data, size_t length)
{
    if (parser == NULL || (data == NULL && length != 0U)) return -1;
    for (size_t i = 0U; i < length; ++i) {
        if (parser->length == sizeof(parser->buffer)) {
            parser->length = 0U;
        }
        parser->buffer[parser->length++] = data[i];
        discard_until_magic(parser);
        if (parser->length < FRAME_HEADER_SIZE) continue;
        const uint16_t payload = (uint16_t)parser->buffer[4] |
                                 ((uint16_t)parser->buffer[5] << 8U);
        const size_t frame_size = FRAME_HEADER_SIZE + (size_t)payload + FRAME_CRC_SIZE;
        if (payload != WHEELBOT_COMMAND_PAYLOAD_SIZE || frame_size > sizeof(parser->buffer)) {
            memmove(parser->buffer, &parser->buffer[1], --parser->length);
            continue;
        }
        if (parser->length < frame_size) continue;
        wheelbot_command_t command;
        if (wheelbot_decode_command(parser->buffer, frame_size, NULL, &command) == 0) {
            wheelbot_robot_command_apply(&command);
        } else {
            memmove(parser->buffer, &parser->buffer[1], --parser->length);
            continue;
        }
        memmove(parser->buffer, &parser->buffer[frame_size], parser->length - frame_size);
        parser->length -= frame_size;
    }
    return 0;
}
