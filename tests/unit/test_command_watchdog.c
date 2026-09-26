#include "robot_command_watchdog.h"

#include <assert.h>
#include <stdint.h>

int main(void)
{
    assert(wheelbot_robot_command_expired(1000U, 800U, 1U, 2U) == 0);
    assert(wheelbot_robot_command_expired(1001U, 800U, 1U, 2U) == 1);
    assert(wheelbot_robot_command_expired(5000U, 0U, 0U, 2U) == 0);
    assert(wheelbot_robot_command_expired(5000U, 0U, 1U, 0U) == 0);

    /* Unsigned subtraction keeps timeout handling correct across tick wrap. */
    assert(wheelbot_robot_command_expired(50U, UINT32_MAX - 100U, 1U, 2U) == 0);
    assert(wheelbot_robot_command_expired(150U, UINT32_MAX - 100U, 1U, 2U) == 1);
    return 0;
}
