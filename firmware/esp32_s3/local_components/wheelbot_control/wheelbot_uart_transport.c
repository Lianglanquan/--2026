#include "wheelbot_esp32_core.h"

int wheelbot_uart_transport_send(wheelbot_uart_transport_t *transport,
                                 const wheelbot_intent_t *intent)
{
    if (transport == NULL || transport->tx == NULL || intent == NULL) return -1;
    wheelbot_command_t command;
    if (wheelbot_intent_to_command(intent, &transport->drive, &command) != 0) return -1;
    uint8_t frame[WHEELBOT_COMMAND_FRAME_SIZE];
    size_t length = 0U;
    if (wheelbot_encode_command_frame(transport->sequence++, &command,
                                      frame, sizeof(frame), &length) != 0) return -1;
    return transport->tx(frame, length, transport->context);
}
