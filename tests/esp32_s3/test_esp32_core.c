#include "wheelbot_ble.h"
#include "wheelbot_esp32_core.h"
#include "wheelbot_providers.h"
#include "wheelbot_voice.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

static void test_intent_to_command(void) {
  wheelbot_intent_t intent = {
      .vx_mps = 0.5f,
      .yaw_rate_rps = 1.0f,
      .mode = WHEELBOT_MODE_DRIVE,
      .stop = 0U,
  };
  wheelbot_drive_config_t cfg = {
      .wheel_radius_m = 0.05f,
      .track_width_m = 0.30f,
      .max_wheel_rpm = 180.0f,
  };
  wheelbot_command_t command;
  assert(wheelbot_intent_to_command(&intent, &cfg, &command) == 0);
  assert(command.enable == 1U);
  assert(command.mode == WHEELBOT_MODE_DRIVE);
  assert(command.wheel_command[0] < command.wheel_command[1]);
  assert(fabsf(command.wheel_command[0] - 66.8451f) < 0.2f);
  assert(fabsf(command.wheel_command[1] - 124.1410f) < 0.2f);
}

static void test_stop_overrides_motion(void) {
  wheelbot_intent_t intent = {
      .vx_mps = 1.0f,
      .yaw_rate_rps = 0.5f,
      .mode = WHEELBOT_MODE_DRIVE,
      .stop = 1U,
  };
  wheelbot_drive_config_t cfg = {
      .wheel_radius_m = 0.05f,
      .track_width_m = 0.30f,
      .max_wheel_rpm = 180.0f,
  };
  wheelbot_command_t command;
  assert(wheelbot_intent_to_command(&intent, &cfg, &command) == 0);
  assert(command.enable == 0U);
  assert(command.mode == WHEELBOT_MODE_STOP);
  assert(command.wheel_command[0] == 0.0f);
  assert(command.wheel_command[1] == 0.0f);
}

static void test_timeout_generates_stop(void) {
  wheelbot_intent_t intent = {
      .vx_mps = 0.4f,
      .yaw_rate_rps = 0.0f,
      .mode = WHEELBOT_MODE_DRIVE,
      .stop = 0U,
  };
  wheelbot_intent_watchdog_t watchdog;
  wheelbot_intent_watchdog_init(&watchdog, 200U);
  assert(wheelbot_intent_watchdog_accept(&watchdog, &intent, 1000U) == 0);
  assert(wheelbot_intent_watchdog_expired(&watchdog, 1199U) == 0);
  assert(wheelbot_intent_watchdog_expired(&watchdog, 1200U) == 1);
}

static void test_wire_frame_matches_cboard_codec(void) {
  wheelbot_command_t command;
  memset(&command, 0, sizeof(command));
  command.enable = 1U;
  command.mode = WHEELBOT_MODE_DRIVE;
  command.wheel_command[0] = 10.0f;
  command.wheel_command[1] = 12.0f;
  uint8_t frame[WHEELBOT_COMMAND_FRAME_SIZE];
  size_t length = 0U;
  assert(wheelbot_encode_command_frame(7U, &command, frame, sizeof(frame),
                                       &length) == 0);
  assert(length == WHEELBOT_COMMAND_FRAME_SIZE);
  assert(frame[0] == 'W' && frame[1] == 'B');
  wheelbot_command_t decoded;
  uint16_t sequence = 0U;
  assert(wheelbot_decode_command_frame(frame, length, &sequence, &decoded) ==
         0);
  assert(sequence == 7U);
  assert(fabsf(decoded.wheel_command[1] - 12.0f) < 0.001f);
  frame[length - 1U] ^= 0x01U;
  assert(wheelbot_decode_command_frame(frame, length, NULL, &decoded) != 0);
}

static size_t captured_length;
static uint8_t captured_frame[WHEELBOT_COMMAND_FRAME_SIZE];

static int capture_tx(const uint8_t *data, size_t length, void *context) {
  (void)context;
  memcpy(captured_frame, data, length);
  captured_length = length;
  return 0;
}

static void test_empty_router_emits_stop_frame(void) {
  wheelbot_input_router_t router;
  wheelbot_input_router_init(&router, 200U);

  wheelbot_intent_t selected = {
      .mode = WHEELBOT_MODE_STOP,
      .stop = 1U,
  };
  assert(wheelbot_input_router_select(&router, 0U, &selected) != 0);

  wheelbot_uart_transport_t transport = {
      .tx = capture_tx,
      .drive =
          {
              .wheel_radius_m = 0.05f,
              .track_width_m = 0.30f,
              .max_wheel_rpm = 180.0f,
          },
  };
  assert(wheelbot_uart_transport_send(&transport, &selected) == 0);

  wheelbot_command_t decoded;
  assert(wheelbot_decode_command_frame(captured_frame, captured_length, NULL,
                                       &decoded) == 0);
  assert(decoded.enable == 0U);
  assert(decoded.mode == WHEELBOT_MODE_STOP);
  assert(decoded.wheel_command[0] == 0.0f);
  assert(decoded.wheel_command[1] == 0.0f);
}

static void test_input_priority_and_uart_transport(void) {
  wheelbot_input_router_t router;
  wheelbot_input_router_init(&router, 200U);
  wheelbot_intent_t voice = {.vx_mps = 0.2f, .mode = WHEELBOT_MODE_DRIVE};
  wheelbot_intent_t ble = {.vx_mps = 0.4f, .mode = WHEELBOT_MODE_DRIVE};
  wheelbot_intent_t selected;
  assert(wheelbot_input_router_submit(&router, WHEELBOT_INPUT_VOICE, &voice,
                                      100U) == 0);
  assert(wheelbot_input_router_submit(&router, WHEELBOT_INPUT_BLE, &ble,
                                      110U) == 0);
  assert(wheelbot_input_router_select(&router, 150U, &selected) == 0);
  assert(fabsf(selected.vx_mps - 0.4f) < 0.001f);
  wheelbot_intent_t stop = {.stop = 1U, .mode = WHEELBOT_MODE_STOP};
  assert(wheelbot_input_router_submit(&router, WHEELBOT_INPUT_VOICE, &stop,
                                      160U) == 0);
  assert(wheelbot_input_router_select(&router, 170U, &selected) == 0 &&
         selected.stop == 1U);

  wheelbot_uart_transport_t transport = {
      .tx = capture_tx,
      .drive = {.wheel_radius_m = 0.05f,
                .track_width_m = 0.30f,
                .max_wheel_rpm = 180.0f},
  };
  assert(wheelbot_uart_transport_send(&transport, &ble) == 0);
  assert(captured_length == WHEELBOT_COMMAND_FRAME_SIZE);
  assert(captured_frame[6] == 0U && captured_frame[7] == 0U);
}

static void test_voice_and_phone_parsers(void) {
  wheelbot_intent_t intent;
  assert(wheelbot_parse_voice_command("前进", &intent) == 0);
  assert(fabsf(intent.vx_mps - 0.25f) < 0.001f && intent.stop == 0U);
  assert(wheelbot_parse_voice_command("停止", &intent) == 0);
  assert(intent.stop == 1U && intent.mode == WHEELBOT_MODE_STOP);
  assert(wheelbot_parse_control_text("vx=0.3;yaw_rate=-0.2;mode=2;stop=0",
                                     &intent) == 0);
  assert(fabsf(intent.vx_mps - 0.3f) < 0.001f);
  assert(fabsf(intent.yaw_rate_rps + 0.2f) < 0.001f);
  assert(wheelbot_parse_control_text("vx=0;yaw_rate=0;mode=2;stop=1",
                                     &intent) == 0);
  assert(intent.stop == 1U && intent.mode == WHEELBOT_MODE_STOP);
}

static void test_provider_adapters(void) {
  wheelbot_input_router_t router;
  wheelbot_input_router_init(&router, 200U);
  assert(wheelbot_provider_submit_voice(&router, "前进", 100U) == 0);
  assert(wheelbot_provider_submit_wifi(
             &router, "vx=0.5;yaw_rate=0;mode=2;stop=0", 110U) == 0);
  wheelbot_intent_t ble = {.vx_mps = -0.2f, .mode = WHEELBOT_MODE_DRIVE};
  assert(wheelbot_provider_submit_ble(&router, &ble, 120U) == 0);
  wheelbot_intent_t selected;
  assert(wheelbot_input_router_select(&router, 150U, &selected) == 0);
  assert(fabsf(selected.vx_mps + 0.2f) < 0.001f);
}

static void test_voice_wake_gate(void) {
  wheelbot_input_router_t router;
  wheelbot_voice_session_t session;
  wheelbot_input_router_init(&router, 200U);
  wheelbot_voice_session_init(&session, 1000U);
  assert(wheelbot_voice_on_command(&session, &router, "前进", 10U) != 0);
  wheelbot_voice_on_wake(&session, 100U);
  assert(wheelbot_voice_on_command(&session, &router, "前进", 200U) == 0);
  assert(wheelbot_voice_on_command(&session, &router, "前进", 300U) != 0);
  wheelbot_voice_on_wake(&session, 1000U);
  assert(wheelbot_voice_on_command(&session, &router, "前进", 2101U) != 0);
}

static void test_ble_gamepad_adapter(void) {
  wheelbot_ble_gamepad_report_t report = {
      .x_axis = 16384, .y_axis = -16384, .stop_button = 0U};
  wheelbot_intent_t intent;
  assert(wheelbot_ble_report_to_intent(&report, 32767, 0.5f, 1.0f, &intent) ==
         0);
  assert(fabsf(intent.vx_mps + 0.25f) < 0.01f);
  assert(fabsf(intent.yaw_rate_rps - 0.5f) < 0.01f);
  report.stop_button = 1U;
  assert(wheelbot_ble_report_to_intent(&report, 32767, 0.5f, 1.0f, &intent) ==
         0);
  assert(intent.stop == 1U && intent.vx_mps == 0.0f);
}

int main(void) {
  test_intent_to_command();
  test_stop_overrides_motion();
  test_timeout_generates_stop();
  test_wire_frame_matches_cboard_codec();
  test_empty_router_emits_stop_frame();
  test_input_priority_and_uart_transport();
  test_voice_and_phone_parsers();
  test_provider_adapters();
  test_voice_wake_gate();
  test_ble_gamepad_adapter();
  puts("esp32_s3 core tests: PASS");
  return 0;
}
