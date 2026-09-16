#include "wheelbot_voice.h"

#include "wheelbot_providers.h"

#include <string.h>

void wheelbot_voice_session_init(wheelbot_voice_session_t *session,
                                 uint32_t wake_valid_ms)
{
    if (session == NULL) return;
    memset(session, 0, sizeof(*session));
    session->wake_valid_ms = wake_valid_ms;
}

void wheelbot_voice_on_wake(wheelbot_voice_session_t *session, uint32_t now_ms)
{
    if (session == NULL) return;
    session->last_wake_ms = now_ms;
    session->awake = 1U;
}

int wheelbot_voice_on_command(wheelbot_voice_session_t *session,
                              wheelbot_input_router_t *router,
                              const char *command,
                              uint32_t now_ms)
{
    if (session == NULL || router == NULL || command == NULL || session->awake == 0U ||
        (uint32_t)(now_ms - session->last_wake_ms) >= session->wake_valid_ms) return -1;
    const int result = wheelbot_provider_submit_voice(router, command, now_ms);
    session->awake = 0U;
    return result;
}
