#ifndef WHEELBOT_VOICE_H
#define WHEELBOT_VOICE_H

#include "wheelbot_esp32_core.h"

typedef struct {
    uint32_t wake_valid_ms;
    uint32_t last_wake_ms;
    uint8_t awake;
} wheelbot_voice_session_t;

void wheelbot_voice_session_init(wheelbot_voice_session_t *session,
                                 uint32_t wake_valid_ms);
void wheelbot_voice_on_wake(wheelbot_voice_session_t *session, uint32_t now_ms);
int wheelbot_voice_on_command(wheelbot_voice_session_t *session,
                              wheelbot_input_router_t *router,
                              const char *command,
                              uint32_t now_ms);

#endif
