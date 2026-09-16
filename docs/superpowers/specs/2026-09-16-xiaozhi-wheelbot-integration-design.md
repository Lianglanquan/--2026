# XiaoZhi WheelBot ESP32-S3 Integration Design

Date: 2026-09-16

## 1. Goal

Deliver one production ESP32-S3 firmware that connects the existing INMP441
microphone and MAX98357A amplifier to the official `xiaozhi.me` cloud service.
The device must wake on “你好小云”, capture speech, receive the cloud response,
and play it through the speaker.

The existing WheelBot UART protocol, input arbitration, differential-drive
conversion, and fail-safe stop loop remain available inside the same firmware.
Voice-to-motion control is explicitly out of scope for this phase.

## 2. Decisions

- Use the official `78/xiaozhi-esp32` project as the application framework.
- Keep a single firmware tree at `firmware/esp32_s3`; do not maintain separate
  XiaoZhi and legacy WheelBot firmware images.
- Import and pin a known upstream XiaoZhi revision, recording its source commit
  and license in the repository.
- Create a unique XiaoZhi board identity named `wheelbot-s3-audio`. Do not alter
  an unrelated upstream board definition.
- Standardize the ESP32 build environment on ESP-IDF 6.1. Remove the ESP-IDF
  5.5.5 checkout and its obsolete build artifacts only after the 6.1 build has
  passed, so the migration remains recoverable until verified.
- Use the official `xiaozhi.me` cloud service.
- Use the custom offline wake phrase “你好小云”.
- Do not map XiaoZhi intents or model output to robot movement in this phase.

## 3. Hardware Definition

The custom board uses the wiring already installed on the robot:

| ESP32-S3 | Device signal | Purpose |
|---|---|---|
| GPIO4 | INMP441 SCK and MAX98357A BCLK | Shared I2S bit clock |
| GPIO5 | INMP441 WS and MAX98357A LRC | Shared I2S word select |
| GPIO6 | INMP441 SD | Microphone data input |
| GPIO7 | MAX98357A DIN | Speaker data output |
| GPIO17 | C Board RX | WheelBot UART TX |
| GPIO16 | C Board TX | WheelBot UART RX |

INMP441 `L/R` remains tied to GND, selecting the left slot. The MAX98357A is
powered from 5 V/VBUS and the INMP441 from 3.3 V. All modules share ground.
The speaker connects only to `SPK+` and `SPK-`.

The detected target is an ESP32-S3 with 16 MB flash and 8 MB octal PSRAM. The
board configuration and partition layout must match those physical resources.

## 4. Firmware Architecture

### 4.1 XiaoZhi application layer

The official XiaoZhi application owns:

- Wi-Fi provisioning and station connectivity;
- device activation and communication with `xiaozhi.me`;
- offline wake detection;
- audio front-end processing and Opus streaming;
- conversation state, ASR/LLM/TTS transport, prompts, and reconnection;
- OTA identity and update handling.

The board class uses the official `NoAudioCodecDuplex` path because microphone
and amplifier share BCLK/WS while using separate data input/output pins. The I2S
transport uses 32-bit slots. This supports the INMP441 24-bit sample carried in
a 32-bit slot and is also accepted by the MAX98357A.

### 4.2 Custom board

Create `main/boards/wheelbot-s3-audio/` with:

- `config.h` for the GPIO and sample-rate definitions;
- `config.json` for the unique board and firmware identity;
- a board implementation deriving from the appropriate Wi-Fi board class;
- `README.md` containing wiring, build, flash, provisioning, activation, and
  recovery instructions.

No display, camera, codec-control I2C bus, or power-management hardware is
invented. Optional user interaction uses the development board BOOT button only
where the actual GPIO can be verified; normal operation is wake-word driven.

### 4.3 WheelBot control component

Migrate the reusable legacy sources into an internal `wheelbot_control`
component rather than preserving the old standalone application entry point.
The component contains:

- WheelBot command structures and binary frame codec;
- CRC16 and UART transport;
- differential-drive conversion and limit handling;
- input router and intent timeout logic;
- GPIO17/GPIO16 UART initialization;
- a 50 Hz fail-safe task that emits explicit stop frames when no valid intent
  is present.

The old WheelBot SoftAP is not started because XiaoZhi owns Wi-Fi provisioning
and station networking. The existing HTTP and BLE provider concepts may remain
as component boundaries, but they are disabled by default and are not part of
this phase’s acceptance criteria. This avoids unauthenticated motion control on
the LAN and avoids BLE/Wi-Fi resource conflicts.

No XiaoZhi callback, wake event, transcript, or MCP tool is connected to
`wheelbot_input_router` in this phase. Consequently, cloud dialogue cannot move
the robot. A future phase can add explicit, separately reviewed MCP tools at
this boundary.

## 5. Wake Word

Configure XiaoZhi’s custom MultiNet wake-word path for “你好小云”, including
the display text and generated/custom asset bundle required by the selected
upstream revision. Detection threshold remains a build-time setting so it can
be tuned during hardware testing without changing application logic.

Wake-word activation starts a normal XiaoZhi cloud conversation. Failure to
reach the cloud must return the device to an idle, wakeable state rather than
leaving the microphone pipeline blocked.

## 6. Audio Bring-Up and Diagnostics

Hardware success is not inferred from successful I2S initialization alone.
Bring-up occurs in this order:

1. Initialize the official 32-bit duplex codec path.
2. Run a controlled speaker prompt or startup chime to validate MAX98357A TX.
3. Observe microphone peak/RMS or the upstream audio debugger to verify that
   INMP441 samples respond to speech without being constant or fully clipped.
4. Verify repeated offline wake detection using “你好小云”.
5. Complete multiple cloud conversations and hear intelligible TTS playback.

Any temporary diagnostic mode must be build-time gated and disabled in the
final production configuration if it continuously logs or streams raw audio.

## 7. Error and Safety Behavior

- Audio initialization failure is reported clearly over USB serial and must not
  enable any movement command.
- Wi-Fi or cloud failure uses XiaoZhi’s normal provisioning/retry behavior while
  leaving wake/audio tasks recoverable.
- The WheelBot task defaults to stop, rejects invalid/non-finite intents, and
  expires stale intents.
- A global stop intent remains higher priority than any future non-stop source.
- UART failure is logged and retried by the periodic task; it does not crash the
  XiaoZhi conversation application.
- The firmware never drives motors directly. It only emits the existing C Board
  protocol on GPIO17/GPIO16.

## 8. Build and Repository Strategy

- Install ESP-IDF 6.1 under the existing `/data/esp` toolchain area.
- Update `tools/build_esp32_s3.sh` to select the verified 6.1 environment and the
  `wheelbot-s3-audio` variant deterministically.
- Provide a corresponding flash/monitor helper for `/dev/ttyACM0`, while still
  allowing an explicit port override.
- Record the pinned XiaoZhi upstream commit so future upstream updates are
  deliberate and reviewable.
- Preserve unrelated user changes in the dirty repository.
- After a successful 6.1 build, remove the 5.5.5 checkout, old generated build
  directories, obsolete `sdkconfig` backups, and superseded standalone entry
  point. Do not delete the reusable WheelBot control sources until their port
  and host tests pass.

## 9. Verification and Acceptance

### Automated verification

- Existing host unit tests continue to cover WheelBot frame encoding, CRC,
  intent routing, timeout behavior, and C Board receiver compatibility.
- Add or adapt tests for the migrated component where interfaces change.
- A clean ESP-IDF 6.1 build of `wheelbot-s3-audio` completes without errors.
- The final image fits the configured 16 MB partition layout.

### Hardware verification

- Flashing and booting on `/dev/ttyACM0` succeeds without reset loops.
- Serial logs identify the custom board, 16 MB flash, 8 MB PSRAM, and correct
  GPIO assignments.
- The speaker plays an intelligible startup prompt/chime.
- Microphone diagnostics show changing, non-clipped samples while speaking.
- “你好小云” wakes the device at least 8 out of 10 attempts in a quiet room at
  normal speaking distance.
- The device can be provisioned, activated in `xiaozhi.me`, and complete at
  least three consecutive spoken request/response exchanges.
- No spoken content generates a movement command.
- If the C Board is connected, observed command traffic remains stop-only until
  a separately authorized control provider supplies a valid intent.

## 10. Out of Scope

- Voice commands for driving, posture, balancing, or actuator control;
- MCP movement tools;
- replacing the C Board motor-control loop;
- display, camera, battery UI, or custom enclosure work;
- private XiaoZhi server deployment;
- full-duplex acoustic echo cancellation guarantees with the current physical
  microphone/speaker placement.
