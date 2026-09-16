#include "wheelbot_providers.h"

int wheelbot_provider_submit_voice(wheelbot_input_router_t *router,
                                   const char *command, uint32_t now_ms)
{
    wheelbot_intent_t intent;
    if (wheelbot_parse_voice_command(command, &intent) != 0) return -1;
    return wheelbot_input_router_submit(router, WHEELBOT_INPUT_VOICE, &intent, now_ms);
}

int wheelbot_provider_submit_wifi(wheelbot_input_router_t *router,
                                  const char *control_text, uint32_t now_ms)
{
    wheelbot_intent_t intent;
    if (wheelbot_parse_control_text(control_text, &intent) != 0) return -1;
    return wheelbot_input_router_submit(router, WHEELBOT_INPUT_WIFI, &intent, now_ms);
}

int wheelbot_provider_submit_ble(wheelbot_input_router_t *router,
                                 const wheelbot_intent_t *intent, uint32_t now_ms)
{
    return wheelbot_input_router_submit(router, WHEELBOT_INPUT_BLE, intent, now_ms);
}
