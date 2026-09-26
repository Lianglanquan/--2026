#include "wheelbot_esp32_core.h"

#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>

int main(void)
{
    const wheelbot_battery_t expected = {.voltage = 24.36f, .percentage = 78U};
    uint8_t frame[WHEELBOT_BATTERY_FRAME_SIZE];
    size_t length = 0U;
    assert(wheelbot_encode_battery_frame(17U, &expected, frame,
                                         sizeof(frame), &length) == 0);
    assert(length == WHEELBOT_BATTERY_FRAME_SIZE);

    wheelbot_battery_parser_t parser;
    wheelbot_battery_parser_init(&parser);
    for (size_t i = 0U; i < length; ++i) {
        assert(wheelbot_battery_parser_feed(&parser, &frame[i], 1U) == 0);
    }
    assert(parser.frames_received == 1U);
    assert(fabsf(parser.latest.voltage - expected.voltage) < 0.001f);
    assert(parser.latest.percentage == expected.percentage);

    frame[length - 1U] ^= 1U;
    assert(wheelbot_battery_parser_feed(&parser, frame, length) == 0);
    assert(parser.frames_received == 1U);
    return 0;
}
