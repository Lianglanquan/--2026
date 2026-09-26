#ifndef WHEELBOT_USB_ROBOT_PROTOCOL_H
#define WHEELBOT_USB_ROBOT_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

void wheelbot_usb_robot_protocol_receive(const uint8_t *data, size_t length);

/* Application may override this weak hook to apply a validated command. */
void wheelbot_robot_command_apply(const void *command);

#endif
