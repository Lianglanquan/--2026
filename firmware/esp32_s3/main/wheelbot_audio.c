#include "wheelbot_audio.h"

#include "driver/gpio.h"
#include "driver/i2s.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"

#include "wheelbot_config.h"

static const char *TAG = "wheelbot_audio";

int wheelbot_audio_start(void)
{
    const i2s_config_t config = {
        .mode = I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_RX,
        .sample_rate = WHEELBOT_AUDIO_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = 0,
        .dma_buf_count = WHEELBOT_AUDIO_DMA_BUF_COUNT,
        .dma_buf_len = WHEELBOT_AUDIO_DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0,
    };
    const i2s_pin_config_t pins = {
        .bck_io_num = WHEELBOT_I2S_BCLK_GPIO,
        .ws_io_num = WHEELBOT_I2S_WS_GPIO,
        .data_out_num = WHEELBOT_I2S_SPK_DIN_GPIO,
        .data_in_num = WHEELBOT_I2S_MIC_SD_GPIO,
    };
    esp_err_t result = i2s_driver_install(WHEELBOT_I2S_PORT, &config, 0, NULL);
    if (result != ESP_OK && result != ESP_ERR_INVALID_STATE) return -1;
    if (i2s_set_pin(WHEELBOT_I2S_PORT, &pins) != ESP_OK) return -1;
    ESP_LOGI(TAG, "I2S audio ready: %u Hz, INMP441 RX GPIO%d, MAX98357A TX GPIO%d",
             WHEELBOT_AUDIO_SAMPLE_RATE, WHEELBOT_I2S_MIC_SD_GPIO,
             WHEELBOT_I2S_SPK_DIN_GPIO);
    return 0;
}

int wheelbot_audio_beep(uint16_t frequency_hz, uint16_t duration_ms)
{
    if (frequency_hz == 0U || frequency_hz > WHEELBOT_AUDIO_SAMPLE_RATE / 2U || duration_ms == 0U) return -1;
    const uint32_t samples = (WHEELBOT_AUDIO_SAMPLE_RATE * (uint32_t)duration_ms) / 1000U;
    int16_t buffer[256];
    size_t written = 0U;
    for (uint32_t offset = 0U; offset < samples; ) {
        const size_t count = (samples - offset > 256U) ? 256U : (size_t)(samples - offset);
        for (size_t i = 0U; i < count; ++i) {
            const uint32_t period = WHEELBOT_AUDIO_SAMPLE_RATE / frequency_hz;
            const uint32_t phase = (offset + (uint32_t)i) % period;
            buffer[i] = phase < period / 2U ? 12000 : -12000;
        }
        if (i2s_write(WHEELBOT_I2S_PORT, buffer, count * sizeof(buffer[0]), &written,
                      portMAX_DELAY) != ESP_OK) return -1;
        offset += (uint32_t)count;
    }
    return 0;
}

int wheelbot_audio_read(int16_t *samples, size_t sample_count,
                        uint32_t timeout_ms, size_t *samples_read)
{
    if (samples == NULL || samples_read == NULL || sample_count == 0U) return -1;
    size_t bytes_read = 0U;
    const esp_err_t result = i2s_read(WHEELBOT_I2S_PORT, samples,
                                      sample_count * sizeof(samples[0]),
                                      &bytes_read, pdMS_TO_TICKS(timeout_ms));
    if (result != ESP_OK) {
        *samples_read = 0U;
        return -1;
    }
    *samples_read = bytes_read / sizeof(samples[0]);
    return 0;
}
