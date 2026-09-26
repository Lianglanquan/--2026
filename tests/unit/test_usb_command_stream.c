#include "robot_protocol.h"
#include "usb_robot_protocol.h"

#include <assert.h>
#include <string.h>

static unsigned received;
static wheelbot_command_t last;

void wheelbot_robot_command_apply(const void *value)
{
    ++received;
    last = *(const wheelbot_command_t *)value;
}

int main(void)
{
    wheelbot_command_t input = {0};
    uint8_t frame[36];
    size_t length = 0;
    input.enable = 1;
    input.mode = 3;
    input.joint_target[2] = 34.0f;
    assert(wheelbot_encode_command(11, &input, frame, sizeof(frame), &length) == 0);
    wheelbot_usb_robot_protocol_receive(frame, 7);
    assert(received == 0);
    wheelbot_usb_robot_protocol_receive(frame + 7, length - 7);
    assert(received == 1 && last.mode == 3 && last.joint_target[2] == 34.0f);
    uint8_t combined[72];
    memcpy(combined, frame, length);
    memcpy(combined + length, frame, length);
    wheelbot_usb_robot_protocol_receive(combined, length * 2);
    assert(received == 3);
    frame[length - 1] ^= 1;
    wheelbot_usb_robot_protocol_receive(frame, length);
    assert(received == 3);
    frame[length - 1] ^= 1;
    frame[9] = 255;
    frame[length - 2] = (uint8_t)wheelbot_crc16(frame, length - 2);
    frame[length - 1] = (uint8_t)(wheelbot_crc16(frame, length - 2) >> 8);
    wheelbot_usb_robot_protocol_receive(frame, length);
    assert(received == 3);
    /* A corrupt prefix must not consume the following valid command. */
    uint8_t shifted[72];
    memcpy(shifted, frame, 10);
    memcpy(shifted + 10, combined, length);
    wheelbot_usb_robot_protocol_receive(shifted, length + 10);
    assert(received == 4);
    return 0;
}
