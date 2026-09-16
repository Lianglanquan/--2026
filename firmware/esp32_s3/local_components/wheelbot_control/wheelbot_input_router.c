#include "wheelbot_esp32_core.h"

#include <math.h>
#include <string.h>

void wheelbot_input_router_init(wheelbot_input_router_t *router,
                                uint32_t timeout_ms)
{
    if (router == NULL) return;
    memset(router, 0, sizeof(*router));
    router->timeout_ms = timeout_ms;
}

int wheelbot_input_router_submit(wheelbot_input_router_t *router,
                                 wheelbot_input_source_t source,
                                 const wheelbot_intent_t *intent,
                                 uint32_t now_ms)
{
    if (router == NULL || intent == NULL || source >= WHEELBOT_INPUT_COUNT ||
        !isfinite(intent->vx_mps) || !isfinite(intent->yaw_rate_rps)) return -1;
    router->intent[source] = *intent;
    router->updated_at_ms[source] = now_ms;
    router->valid[source] = 1U;
    return 0;
}

int wheelbot_input_router_select(const wheelbot_input_router_t *router,
                                uint32_t now_ms,
                                wheelbot_intent_t *intent)
{
    if (router == NULL || intent == NULL) return -1;

    /* Stop is global and wins regardless of which input produced it. */
    for (unsigned source = 0U; source < WHEELBOT_INPUT_COUNT; ++source) {
        if (router->valid[source] != 0U && router->intent[source].stop != 0U &&
            (uint32_t)(now_ms - router->updated_at_ms[source]) < router->timeout_ms) {
            *intent = router->intent[source];
            return 0;
        }
    }

    /* BLE > Wi-Fi > voice for simultaneous non-stop intents. */
    for (int source = (int)WHEELBOT_INPUT_BLE; source >= (int)WHEELBOT_INPUT_VOICE; --source) {
        if (router->valid[source] != 0U &&
            (uint32_t)(now_ms - router->updated_at_ms[source]) < router->timeout_ms) {
            *intent = router->intent[source];
            return 0;
        }
    }
    return -1;
}
