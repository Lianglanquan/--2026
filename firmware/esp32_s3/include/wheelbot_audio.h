#ifndef WHEELBOT_AUDIO_H
#define WHEELBOT_AUDIO_H

#include <stdint.h>
#include <stddef.h>

int wheelbot_audio_start(void);
int wheelbot_audio_beep(uint16_t frequency_hz, uint16_t duration_ms);

/* Read signed PCM samples from the INMP441. Returns 0 on success. */
int wheelbot_audio_read(int16_t *samples, size_t sample_count,
                        uint32_t timeout_ms, size_t *samples_read);

#endif
