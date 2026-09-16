#ifndef WHEELBOT_ESP32_CORE_H
#define WHEELBOT_ESP32_CORE_H

#include <stddef.h>
#include <stdint.h>

#define WHEELBOT_PROTOCOL_VERSION 1U
#define WHEELBOT_PROTOCOL_MAGIC0 ((uint8_t)'W')
#define WHEELBOT_PROTOCOL_MAGIC1 ((uint8_t)'B')
#define WHEELBOT_COMMAND_PAYLOAD_SIZE 26U
#define WHEELBOT_COMMAND_FRAME_SIZE 36U

typedef enum {
    WHEELBOT_MODE_STOP = 0U,
    WHEELBOT_MODE_DRIVE = 2U,
} wheelbot_mode_t;

typedef struct {
    float vx_mps;
    float yaw_rate_rps;
    uint8_t mode;
    uint8_t stop;
} wheelbot_intent_t;

/* The command layout is intentionally byte-compatible with the C Board. */
typedef struct {
    uint8_t enable;
    uint8_t mode;
    float joint_target[4];
    float wheel_command[2];
} wheelbot_command_t;

typedef struct {
    float wheel_radius_m;
    float track_width_m;
    float max_wheel_rpm;
} wheelbot_drive_config_t;

typedef struct {
    wheelbot_intent_t latest;
    uint32_t accepted_at_ms;
    uint32_t timeout_ms;
    uint8_t valid;
} wheelbot_intent_watchdog_t;

int wheelbot_intent_to_command(const wheelbot_intent_t *intent,
                               const wheelbot_drive_config_t *config,
                               wheelbot_command_t *command);

void wheelbot_intent_watchdog_init(wheelbot_intent_watchdog_t *watchdog,
                                   uint32_t timeout_ms);
int wheelbot_intent_watchdog_accept(wheelbot_intent_watchdog_t *watchdog,
                                    const wheelbot_intent_t *intent,
                                    uint32_t now_ms);
int wheelbot_intent_watchdog_expired(const wheelbot_intent_watchdog_t *watchdog,
                                     uint32_t now_ms);

uint16_t wheelbot_crc16(const uint8_t *data, size_t length);
int wheelbot_encode_command_frame(uint16_t sequence,
                                  const wheelbot_command_t *command,
                                  uint8_t *frame, size_t capacity,
                                  size_t *frame_length);
int wheelbot_decode_command_frame(const uint8_t *frame, size_t frame_length,
                                  uint16_t *sequence,
                                  wheelbot_command_t *command);

typedef enum {
    WHEELBOT_INPUT_VOICE = 0U,
    WHEELBOT_INPUT_WIFI = 1U,
    WHEELBOT_INPUT_BLE = 2U,
    WHEELBOT_INPUT_COUNT = 3U,
} wheelbot_input_source_t;

typedef struct {
    wheelbot_intent_t intent[WHEELBOT_INPUT_COUNT];
    uint32_t updated_at_ms[WHEELBOT_INPUT_COUNT];
    uint8_t valid[WHEELBOT_INPUT_COUNT];
    uint32_t timeout_ms;
} wheelbot_input_router_t;

void wheelbot_input_router_init(wheelbot_input_router_t *router,
                                uint32_t timeout_ms);
int wheelbot_input_router_submit(wheelbot_input_router_t *router,
                                 wheelbot_input_source_t source,
                                 const wheelbot_intent_t *intent,
                                 uint32_t now_ms);
int wheelbot_input_router_select(const wheelbot_input_router_t *router,
                                uint32_t now_ms,
                                wheelbot_intent_t *intent);

typedef int (*wheelbot_uart_tx_fn)(const uint8_t *data, size_t length, void *context);

typedef struct {
    wheelbot_uart_tx_fn tx;
    void *context;
    wheelbot_drive_config_t drive;
    uint16_t sequence;
} wheelbot_uart_transport_t;

int wheelbot_uart_transport_send(wheelbot_uart_transport_t *transport,
                                 const wheelbot_intent_t *intent);

/* Voice/Wi-Fi/BLE adapters normalize their payloads through these parsers. */
int wheelbot_parse_voice_command(const char *text, wheelbot_intent_t *intent);
int wheelbot_parse_control_text(const char *text, wheelbot_intent_t *intent);

#endif
