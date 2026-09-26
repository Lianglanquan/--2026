#ifndef WHEELBOT_ROBOT_COMMAND_WATCHDOG_H
#define WHEELBOT_ROBOT_COMMAND_WATCHDOG_H

#include <stdint.h>

#define WHEELBOT_COMMAND_TIMEOUT_MS 200U

static inline int wheelbot_robot_command_expired(uint32_t now_ms, uint32_t last_command_ms,
                                                 uint8_t enable, uint8_t mode)
{
    if (enable == 0U || mode == 0U) return 0;
    return (uint32_t)(now_ms - last_command_ms) > WHEELBOT_COMMAND_TIMEOUT_MS;
}

#endif
