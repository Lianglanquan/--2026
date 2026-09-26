#include "fashionstar_task.h"

#include "cmsis_os.h"
#include "fashionstar_uart.h"
#include "main.h"

static const uint8_t joint_ids[WHEELBOT_HA8_COUNT] = {
    WHEELBOT_HA8_LF_ID, WHEELBOT_HA8_LR_ID,
    WHEELBOT_HA8_RF_ID, WHEELBOT_HA8_RR_ID,
};

void wheelbot_fashionstar_task(void const *argument)
{
    (void)argument;
    wheelbot_fashionstar_init();
    uint32_t applied_generation = 0U;

    for (;;)
    {
        float targets[WHEELBOT_HA8_COUNT];
        uint8_t active;
        uint32_t generation;
        generation = wheelbot_fashionstar_take_targets(targets, &active);
#if defined(WHEELBOT_HA8_MOTION_ENABLED)
        if (active && generation != applied_generation) {
            for (unsigned i = 0U; i < WHEELBOT_HA8_COUNT; ++i) {
                if (!wheelbot_fashionstar_targets_active(generation)) break;
                (void)FSUS_SetServoAngle(&FSUS_Usart, joint_ids[i], targets[i], 200U, 0U);
            }
            applied_generation = generation;
        }
#else
        (void)targets;
        (void)active;
        (void)generation;
        (void)applied_generation;
#endif
        for (unsigned i = 0U; i < WHEELBOT_HA8_COUNT; ++i) {
            float angle = 0.0f;
            uint8_t status = 255U;
            const FSUS_STATUS angle_result = wheelbot_fashionstar_read_angle(joint_ids[i], &angle);
            const FSUS_STATUS status_result = wheelbot_fashionstar_read_status(joint_ids[i], &status);
            const uint32_t now = HAL_GetTick();
            wheelbot_fashionstar_record_sample(i, angle,
                angle_result == FSUS_STATUS_SUCCESS && status_result == FSUS_STATUS_SUCCESS
                    ? status : 255U, now);
        }
        osDelay(100U);
    }
}
