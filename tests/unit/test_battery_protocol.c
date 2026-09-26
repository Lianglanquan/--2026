#include "robot_protocol.h"

#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>

int main(void)
{
    const wheelbot_battery_t expected = {.voltage = 24.36f, .percentage = 78U};
    uint8_t frame[18];
    size_t length = 0U;
    wheelbot_battery_t decoded;
    uint16_t sequence = 0U;

    assert(wheelbot_encode_battery(17U, &expected, frame,
                                   sizeof(frame), &length) == 0);
    assert(length == sizeof(frame));
    assert(wheelbot_decode_battery(frame, length, &sequence, &decoded) == 0);
    assert(sequence == 17U);
    assert(fabsf(decoded.voltage - expected.voltage) < 0.001f);
    assert(decoded.percentage == expected.percentage);
    frame[length - 1U] ^= 1U;
    assert(wheelbot_decode_battery(frame, length, NULL, &decoded) != 0);
    return 0;
}
