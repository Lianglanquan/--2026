#ifndef WHEELBOT_PROVIDERS_H
#define WHEELBOT_PROVIDERS_H

#include "wheelbot_esp32_core.h"

/* Providers are deliberately transport agnostic. ESP-SR/Wi-Fi/BLE callbacks
 * normalize into these three functions; only the app owns the router. */
int wheelbot_provider_submit_voice(wheelbot_input_router_t *router,
                                   const char *command, uint32_t now_ms);
int wheelbot_provider_submit_wifi(wheelbot_input_router_t *router,
                                  const char *control_text, uint32_t now_ms);
int wheelbot_provider_submit_ble(wheelbot_input_router_t *router,
                                 const wheelbot_intent_t *intent, uint32_t now_ms);

/* Audio provider boundary for I2S/MAX98357A integration. */
typedef int (*wheelbot_audio_play_fn)(const int16_t *samples,
                                      size_t sample_count,
                                      uint32_t sample_rate_hz,
                                      void *context);

#endif
