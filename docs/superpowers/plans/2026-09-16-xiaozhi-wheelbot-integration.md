# XiaoZhi WheelBot ESP32-S3 Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and flash one ESP32-S3 firmware that wakes on “你好小云”, talks to the official `xiaozhi.me` service through the connected INMP441/MAX98357A, and preserves the WheelBot UART safety/control core without enabling voice movement.

**Architecture:** Replace the standalone WheelBot ESP-IDF application with a pinned import of official `78/xiaozhi-esp32`, then add a unique `wheelbot-s3-audio` board using `NoAudioCodecDuplex`. Move the reusable WheelBot protocol/router/UART code into an ESP-IDF component started by the board, while XiaoZhi exclusively owns Wi-Fi, audio processing, wake detection, and cloud dialogue.

**Tech Stack:** ESP-IDF 6.1, ESP32-S3 N16R8, official `78/xiaozhi-esp32`, ESP-SR MultiNet, I2S standard mode, INMP441, MAX98357A, FreeRTOS, C/C++, CMake, host CTest.

**Spec:** `docs/superpowers/specs/2026-09-16-xiaozhi-wheelbot-integration-design.md`

## Global Constraints

- Final repository contains one ESP32-S3 firmware tree at `firmware/esp32_s3`.
- Use official XiaoZhi upstream revision `5d54beb743ff49c4e8db81bbef9413bdd6e2ba17` as the initial pinned baseline unless that revision cannot resolve its declared dependencies; record any necessary newer revision before importing it.
- Use ESP-IDF 6.1; ESP-IDF 5.5.5 is removed only after a successful 6.1 build.
- Preserve GPIO4 BCLK, GPIO5 WS, GPIO6 microphone DIN, GPIO7 speaker DOUT, GPIO17 WheelBot UART TX, and GPIO16 WheelBot UART RX.
- Configure 16 MB flash and 8 MB octal PSRAM.
- The wake phrase is “你好小云”.
- Do not connect any XiaoZhi transcript, wake callback, MCP tool, or cloud response to a non-stop WheelBot intent.
- Default WheelBot UART output is stop-only until an independently authorized provider submits an intent.
- Do not stage or commit unrelated dirty-worktree files.

---

## Planned File Structure

```text
firmware/esp32_s3/
├── UPSTREAM.md                              # pinned XiaoZhi source provenance
├── CMakeLists.txt                           # official XiaoZhi project root
├── main/
│   ├── boards/wheelbot-s3-audio/
│   │   ├── config.h                         # N16R8 and GPIO mapping
│   │   ├── config.json                      # unique OTA/build identity
│   │   ├── README.md                        # board bring-up instructions
│   │   └── wheelbot_s3_audio.cc             # board, audio codec, BOOT button, control start
│   └── CMakeLists.txt                        # selects board and requires wheelbot_control
├── components/wheelbot_control/
│   ├── CMakeLists.txt                       # ESP-IDF component registration
│   ├── include/
│   │   ├── wheelbot_control.h               # start/status API
│   │   ├── wheelbot_esp32_core.h            # protocol/router public types
│   │   ├── wheelbot_ble.h
│   │   ├── wheelbot_providers.h
│   │   └── wheelbot_voice.h
│   ├── wheelbot_control.c                    # UART initialization and fail-safe task
│   ├── wheelbot_esp32_core.c
│   ├── wheelbot_input_router.c
│   ├── wheelbot_uart_transport.c
│   ├── wheelbot_command_parser.c
│   ├── wheelbot_providers.c
│   ├── wheelbot_voice.c
│   └── wheelbot_ble.c
tests/esp32_s3/                               # host protocol/safety tests
tools/build_esp32_s3.sh                       # IDF 6.1 custom-board build
tools/flash_esp32_s3.sh                       # flash/monitor helper
tools/test_esp32_s3.sh                        # host regression tests
docs/wiring/README.md                         # final wiring and validation flow
```

### Task 1: Capture Baseline and Protect Legacy Sources

**Files:**
- Create: `artifacts/migration/esp32_s3-legacy-manifest.txt`
- Create: `artifacts/migration/esp32_s3-legacy.sha256`
- Read: `firmware/esp32_s3/**`
- Read: `tools/build_esp32_s3.sh`
- Test: `tests/esp32_s3/**`

**Interfaces:**
- Consumes: current dirty-worktree WheelBot source tree.
- Produces: a verified source manifest and archive/checksum that lets migration proceed without losing untracked legacy files.

- [ ] **Step 1: Run the existing host tests before moving anything**

Run: `bash tools/test_esp32_s3.sh`

Expected: `100% tests passed` and `cboard uart receiver tests: PASS`.

- [ ] **Step 2: Inventory every legacy source file**

Run: `find firmware/esp32_s3 -type f -not -path '*/build/*' -print0 | sort -z | xargs -0 sha256sum > artifacts/migration/esp32_s3-legacy.sha256`

Run: `find firmware/esp32_s3 -type f -not -path '*/build/*' | sort > artifacts/migration/esp32_s3-legacy-manifest.txt`

Expected: the manifest contains the current `include`, `src`, `main`, and test/build files.

- [ ] **Step 3: Create a recoverable archive outside the replacement tree**

Run: `tar --exclude='firmware/esp32_s3/build' -czf artifacts/migration/esp32_s3-legacy.tar.gz firmware/esp32_s3`

Run: `tar -tzf artifacts/migration/esp32_s3-legacy.tar.gz | head`

Expected: archive listing starts with `firmware/esp32_s3/` and exits zero.

- [ ] **Step 4: Record the baseline without committing generated archive bytes**

Update `.gitignore` only if `artifacts/migration/*.tar.gz` is not already ignored. Commit only the manifest/checksum if the repository’s artifact policy permits them; otherwise retain them locally until migration completes.

### Task 2: Install and Pin ESP-IDF 6.1

**Files:**
- Modify: `tools/build_esp32_s3.sh`
- Create: `tools/esp32_idf_env.sh`
- Test: shell version checks.

**Interfaces:**
- Consumes: `/data/esp` and `/data/esp/.espressif`.
- Produces: `source tools/esp32_idf_env.sh` with `IDF_PATH=/data/esp/esp-idf-6.1` and a build helper that rejects IDF versions below 6.1.

- [ ] **Step 1: Verify available disk, Git transport, and current toolchain**

Run: `df -h /data/esp && git -C /data/esp/esp-idf describe --tags --always && env | rg -i 'http.*proxy|all_proxy'`

Expected: enough disk for a second temporary checkout and current checkout reports v5.5.5.

- [ ] **Step 2: Install ESP-IDF 6.1 beside 5.5.5**

Clone the official Espressif repository with proxy variables unset for the command if the stale `127.0.0.1:7890` proxy is present:

```bash
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  git clone --branch v6.1 --recursive --depth 1 \
  https://github.com/espressif/esp-idf.git /data/esp/esp-idf-6.1
IDF_TOOLS_PATH=/data/esp/.espressif /data/esp/esp-idf-6.1/install.sh esp32s3
```

Expected: installation exits zero and does not modify the existing 5.5.5 checkout.

- [ ] **Step 3: Add a deterministic environment helper**

Create `tools/esp32_idf_env.sh` with:

```bash
#!/usr/bin/env bash
export IDF_PATH="${WHEELBOT_IDF_PATH:-/data/esp/esp-idf-6.1}"
export IDF_TOOLS_PATH="${IDF_TOOLS_PATH:-/data/esp/.espressif}"
source "$IDF_PATH/export.sh"
```

- [ ] **Step 4: Make the build reject the wrong major/minor version**

Modify `tools/build_esp32_s3.sh` to source `tools/esp32_idf_env.sh`, run `idf.py --version`, and fail unless the output starts with `ESP-IDF v6.1`.

- [ ] **Step 5: Verify the new environment**

Run: `bash -lc 'source tools/esp32_idf_env.sh >/dev/null && idf.py --version'`

Expected: output starts with `ESP-IDF v6.1`.

- [ ] **Step 6: Commit the environment helpers**

```bash
git add tools/esp32_idf_env.sh tools/build_esp32_s3.sh
git commit -m "build: select ESP-IDF 6.1 for ESP32-S3"
```

### Task 3: Import the Pinned Official XiaoZhi Baseline

**Files:**
- Replace contents under: `firmware/esp32_s3/`
- Create: `firmware/esp32_s3/UPSTREAM.md`
- Preserve into component staging: legacy `include/*.h` and `src/*.c`

**Interfaces:**
- Consumes: official `78/xiaozhi-esp32` commit `5d54beb743ff49c4e8db81bbef9413bdd6e2ba17` and the Task 1 archive.
- Produces: a buildable official XiaoZhi source tree with recorded provenance and legacy WheelBot sources staged under `components/wheelbot_control`.

- [ ] **Step 1: Fetch the exact upstream revision into a temporary directory**

```bash
migration_dir="$(mktemp -d /tmp/wheelbot-xiaozhi.XXXXXX)"
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  git clone https://github.com/78/xiaozhi-esp32.git "$migration_dir/upstream"
git -C "$migration_dir/upstream" checkout 5d54beb743ff49c4e8db81bbef9413bdd6e2ba17
git -C "$migration_dir/upstream" submodule update --init --recursive
```

Expected: `git rev-parse HEAD` prints the exact pinned SHA.

- [ ] **Step 2: Stage reusable legacy files before replacing the root**

Copy the current `include/*.h`, `src/*.c`, and host test CMake inputs to the temporary migration directory. Verify copied hashes against `artifacts/migration/esp32_s3-legacy.sha256`.

- [ ] **Step 3: Replace only the ESP32 firmware tree**

Use a validated mechanical sync from the temporary upstream checkout into `firmware/esp32_s3`, excluding upstream `.git`, `build`, and generated release directories. Do not modify `firmware/c_board`, ROS 2, mechanical assets, or unrelated documentation.

- [ ] **Step 4: Restore legacy code into the new component directory**

Create `firmware/esp32_s3/components/wheelbot_control/include` and restore the legacy headers/sources there, excluding legacy `main/main.c`, `wheelbot_wifi.c`, and `wheelbot_audio.c` because XiaoZhi replaces those owners.

- [ ] **Step 5: Record source provenance**

Create `firmware/esp32_s3/UPSTREAM.md` containing:

```markdown
# Upstream provenance

- Project: https://github.com/78/xiaozhi-esp32
- Commit: 5d54beb743ff49c4e8db81bbef9413bdd6e2ba17
- Imported: 2026-09-16
- License: MIT; see LICENSE
- Local additions: wheelbot-s3-audio board and wheelbot_control component
```

- [ ] **Step 6: Resolve managed components without compiling local changes**

Run: `bash -lc 'source tools/esp32_idf_env.sh >/dev/null && cd firmware/esp32_s3 && idf.py set-target esp32s3 && idf.py reconfigure'`

Expected: component resolution completes under ESP-IDF 6.1.

- [ ] **Step 7: Commit the upstream baseline and provenance separately**

Stage only `firmware/esp32_s3` and confirm no unrelated paths are staged. Commit with `vendor: import pinned xiaozhi esp32 baseline`.

### Task 4: Port and Test the WheelBot Control Component

**Files:**
- Create: `firmware/esp32_s3/components/wheelbot_control/CMakeLists.txt`
- Create: `firmware/esp32_s3/components/wheelbot_control/include/wheelbot_control.h`
- Create: `firmware/esp32_s3/components/wheelbot_control/wheelbot_control.c`
- Modify: restored WheelBot sources under the same component.
- Modify: `tools/test_esp32_s3.sh`
- Modify: `tests/esp32_s3/test_esp32_core.c`

**Interfaces:**
- Consumes: existing `wheelbot_input_router_t`, `wheelbot_uart_transport_t`, and frame codec.
- Produces: `esp_err_t wheelbot_control_start(void)` and `wheelbot_input_router_t *wheelbot_control_router(void)`; start is idempotent and the router is never fed by XiaoZhi in this phase.

- [ ] **Step 1: Add a failing host test for the safe default**

Add a test that initializes an empty router and verifies selection fails, then sends the explicit stop intent through a capture transport and verifies `enable == 0`, `mode == WHEELBOT_MODE_STOP`, and both wheel commands are zero.

```c
static void test_empty_router_emits_stop_frame(void) {
    wheelbot_input_router_t router;
    wheelbot_input_router_init(&router, 200U);
    wheelbot_intent_t selected = {.mode = WHEELBOT_MODE_STOP, .stop = 1U};
    assert(wheelbot_input_router_select(&router, 0U, &selected) != 0);
    wheelbot_uart_transport_t transport = {
        .tx = capture_tx,
        .drive = {
            .wheel_radius_m = 0.05f,
            .track_width_m = 0.30f,
            .max_wheel_rpm = 180.0f,
        },
    };
    assert(wheelbot_uart_transport_send(&transport, &selected) == 0);
    wheelbot_command_t decoded;
    assert(wheelbot_decode_command_frame(captured_frame, captured_length, NULL, &decoded) == 0);
    assert(decoded.enable == 0U && decoded.mode == WHEELBOT_MODE_STOP);
}
```

- [ ] **Step 2: Run the test and confirm the migrated build wiring is incomplete**

Run: `bash tools/test_esp32_s3.sh`

Expected: FAIL until the test script points at the migrated component sources and any missing shared fixture declarations are fixed.

- [ ] **Step 3: Register the component**

Use `idf_component_register` with the protocol, router, parser, provider, BLE adapter, voice gate, UART transport, and runtime task sources; require `driver`, `esp_timer`, and `freertos`.

- [ ] **Step 4: Implement the runtime API**

`wheelbot_control_start()` must:

1. configure UART1 at 115200 8N1 on TX GPIO17/RX GPIO16;
2. initialize the input router with the existing timeout;
3. create exactly one FreeRTOS task;
4. send a selected intent when present, otherwise construct `{mode = STOP, stop = 1}`;
5. transmit at 50 Hz and log write failures without aborting XiaoZhi.

- [ ] **Step 5: Keep voice and network movement disconnected**

Search the XiaoZhi application and custom board additions for calls to `wheelbot_provider_submit_voice`, `wheelbot_input_router_submit`, or `wheelbot_control_router`. The only allowed runtime reference in this phase is board startup; no cloud callback may submit a motion intent.

- [ ] **Step 6: Run all host tests**

Run: `bash tools/test_esp32_s3.sh`

Expected: all ESP32 core and C Board receiver tests pass.

- [ ] **Step 7: Commit the component port**

Stage the component, test, and test helper only. Commit with `feat: integrate wheelbot control safety component`.

### Task 5: Add the `wheelbot-s3-audio` Board

**Files:**
- Create: `firmware/esp32_s3/main/boards/wheelbot-s3-audio/config.h`
- Create: `firmware/esp32_s3/main/boards/wheelbot-s3-audio/config.json`
- Create: `firmware/esp32_s3/main/boards/wheelbot-s3-audio/wheelbot_s3_audio.cc`
- Create: `firmware/esp32_s3/main/boards/wheelbot-s3-audio/README.md`
- Modify: `firmware/esp32_s3/main/CMakeLists.txt`
- Modify: `firmware/esp32_s3/main/Kconfig.projbuild` only if upstream board discovery requires an explicit symbol.

**Interfaces:**
- Consumes: `NoAudioCodecDuplex`, `WifiBoard`, `Application`, and `wheelbot_control_start()`.
- Produces: unique build/OTA identity `wheelbot-s3-audio` with 32-bit duplex audio pins and optional GPIO0 BOOT-button interaction.

- [ ] **Step 1: Add a board metadata validation test**

Extend a small Python or shell validation in `tools/test_esp32_s3.sh` to parse `config.json` and assert:

```python
assert config["type"] == "wheelbot-s3-audio"
assert config["target"] == "esp32s3"
assert config["builds"][0]["name"] == "wheelbot-s3-audio"
```

Also assert `config.h` maps BCLK=4, WS=5, DIN=6, and DOUT=7.

- [ ] **Step 2: Run metadata validation and confirm it fails**

Run: `bash tools/test_esp32_s3.sh`

Expected: FAIL because the custom board does not exist yet.

- [ ] **Step 3: Define the hardware configuration**

Create `config.h` with:

```c
#define AUDIO_INPUT_SAMPLE_RATE 16000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000
#define AUDIO_I2S_GPIO_BCLK GPIO_NUM_4
#define AUDIO_I2S_GPIO_WS GPIO_NUM_5
#define AUDIO_I2S_GPIO_DIN GPIO_NUM_6
#define AUDIO_I2S_GPIO_DOUT GPIO_NUM_7
#define BOOT_BUTTON_GPIO GPIO_NUM_0
```

Do not define `AUDIO_I2S_METHOD_SIMPLEX`.

- [ ] **Step 4: Define the release variant**

Create `config.json` with one `wheelbot-s3-audio` build and append exact N16R8 settings: 16 MB flash, the upstream 16 MB partition table, PSRAM enabled, octal PSRAM mode, and 80 MHz PSRAM speed.

- [ ] **Step 5: Implement the board class**

Derive `WheelbotS3AudioBoard` from `WifiBoard`. Return one static `NoAudioCodecDuplex(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE, GPIO4, GPIO5, GPIO7, GPIO6)`. Start the WheelBot safety component once. Configure GPIO0 click to toggle chat and use the starting-state behavior to enter Wi-Fi configuration.

- [ ] **Step 6: Register the component dependency and board source**

Add `wheelbot_control` to the XiaoZhi main component dependency list and ensure the official board-discovery/build script includes the new directory without changing any existing board identity.

- [ ] **Step 7: Run host/metadata tests**

Run: `bash tools/test_esp32_s3.sh`

Expected: PASS.

- [ ] **Step 8: Commit the board definition**

Commit only the board directory and necessary XiaoZhi build-selection changes with `feat: add wheelbot s3 audio board`.

### Task 6: Configure “你好小云” and Build the Production Image

**Files:**
- Modify/Create: `firmware/esp32_s3/sdkconfig.defaults` or board build arguments generated by `scripts/build.py`.
- Modify: `tools/build_esp32_s3.sh`
- Create: `tools/flash_esp32_s3.sh`

**Interfaces:**
- Consumes: official custom MultiNet wake-word path and custom asset generator/build pipeline.
- Produces: a reproducible build selecting Chinese locale, custom wake phrase “你好小云”, `wheelbot-s3-audio`, and `/dev/ttyACM0` flashing by default.

- [ ] **Step 1: Resolve managed components and inspect available custom-wake options**

Run `idf.py reconfigure`, then inspect `main/Kconfig.projbuild`, resolved ESP-SR Kconfig, and `scripts/build.py` help. Record the exact supported custom-phrase encoding used by the pinned revision instead of guessing it.

- [ ] **Step 2: Add the build arguments**

Update `tools/build_esp32_s3.sh` to invoke the official board build path for `wheelbot-s3-audio`, Chinese locale, and custom wake word. Set display text to `你好小云` and start threshold at the upstream default; do not hard-code a different threshold until hardware measurements justify it.

- [ ] **Step 3: Add the flash helper**

Create `tools/flash_esp32_s3.sh`:

```bash
port="${WHEELBOT_ESP32_PORT:-/dev/ttyACM0}"
source "$repo_root/tools/esp32_idf_env.sh" >/dev/null
cd "$repo_root/firmware/esp32_s3"
idf.py -p "$port" flash
exec idf.py -p "$port" monitor
```

- [ ] **Step 4: Build from a clean configuration**

Run: `rm -rf firmware/esp32_s3/build` only after validating that path is exactly the project build directory, then run `bash tools/build_esp32_s3.sh`.

Expected: clean ESP-IDF 6.1 build succeeds and reports the `wheelbot-s3-audio` variant.

- [ ] **Step 5: Verify size and configuration**

Run: `idf.py size` and inspect generated `sdkconfig` for ESP32-S3, 16 MB flash, octal 8 MB PSRAM, custom wake-word mode, and the custom board identity.

Expected: application fits its partition with margin and all settings match hardware.

- [ ] **Step 6: Commit reproducible build/flash tooling**

Commit configuration and helpers with `build: add xiaozhi wheelbot firmware workflow`.

### Task 7: Flash and Validate the Physical Audio Path

**Files:**
- Modify only if diagnostics are required: board/runtime diagnostic source under `firmware/esp32_s3/main/boards/wheelbot-s3-audio/`.
- Record: `artifacts/esp32_s3/boot.log`
- Record: `artifacts/esp32_s3/audio-validation.md`

**Interfaces:**
- Consumes: `/dev/ttyACM0`, connected INMP441/MAX98357A, built image.
- Produces: serial evidence of correct board/PSRAM/audio initialization plus audible speaker and dynamic microphone verification.

- [ ] **Step 1: Confirm the exact serial target before flashing**

Run: `ls -l /dev/ttyACM0 && source tools/esp32_idf_env.sh >/dev/null && esptool.py --port /dev/ttyACM0 chip-id`

Expected: ESP32-S3 responds and MAC remains `44:bd:8d:fd:4f:4c`.

- [ ] **Step 2: Flash without erasing NVS first**

Run: `WHEELBOT_ESP32_PORT=/dev/ttyACM0 bash tools/flash_esp32_s3.sh`

Capture boot output. Expected: no reset loop; board, flash, PSRAM, audio codec, Wi-Fi, and WheelBot UART initialize.

- [ ] **Step 3: Verify speaker output**

Use the official startup/provisioning prompt. If no prompt is emitted, add a build-gated one-shot diagnostic through the same `AudioCodec` path, rebuild, and confirm the MAX98357A/speaker audibly reproduces it.

- [ ] **Step 4: Verify microphone signal**

Use upstream audio debugging or a build-gated RMS/peak log through the same codec pipeline. Speak near the INMP441 and confirm values change, silence is not stuck at full scale, and speech does not remain fully clipped.

- [ ] **Step 5: Remove continuous raw-audio diagnostics**

Disable any temporary audio streaming or continuous sample logging, rebuild, and reflash the production configuration.

### Task 8: Provision and Validate Official Cloud Dialogue

**Files:**
- Record: `artifacts/esp32_s3/xiaozhi-cloud-validation.md`
- Modify: `firmware/esp32_s3/main/boards/wheelbot-s3-audio/README.md`

**Interfaces:**
- Consumes: Wi-Fi credentials supplied during official provisioning and the user’s `xiaozhi.me` account for device activation.
- Produces: an activated device that wakes on “你好小云” and completes spoken cloud dialogue.

- [ ] **Step 1: Enter official Wi-Fi provisioning**

Use the startup provisioning prompt/BOOT-button path, connect the device to the intended 2.4 GHz network, and record the assigned IP and successful cloud transport connection from serial logs. Do not store the Wi-Fi password in repository files or logs.

- [ ] **Step 2: Complete device activation**

If the firmware announces an activation code, have the user add it in `xiaozhi.me`. This is the only mandatory user/account action; continue serial verification immediately after activation.

- [ ] **Step 3: Tune and test “你好小云”**

Perform 10 attempts at normal speaking distance in a quiet room. Acceptance is at least 8 successful wakes. If below 8, adjust only the custom wake threshold, rebuild, and repeat the same test.

- [ ] **Step 4: Run three consecutive conversations**

For each round: say “你好小云”, ask a simple factual question, confirm microphone capture, cloud response, and intelligible speaker playback. Record pass/fail and serial timestamps without storing private dialogue content beyond a short benign test phrase.

- [ ] **Step 5: Confirm no motion coupling**

Search serial logs for WheelBot non-stop intents and, if the C Board is connected, inspect decoded command traffic. Expected: `enable=0`, stop mode, zero wheel commands throughout voice interaction.

- [ ] **Step 6: Document the final operating flow**

Update board README with provisioning, activation, wake phrase, volume notes, re-entering config mode, serial monitor, and recovery flashing.

### Task 9: Remove ESP-IDF 5.5.5 and Finalize

**Files:**
- Modify: `docs/wiring/README.md`
- Modify: `firmware/esp32_s3/README.md`
- Remove: superseded generated `sdkconfig.old`, legacy standalone application files already migrated, and old build output.
- Remove external checkout: `/data/esp/esp-idf` only after verifying it is the v5.5.5 checkout and not the new 6.1 directory.

**Interfaces:**
- Consumes: successful automated, flash, audio, wake, and cloud validation evidence.
- Produces: one maintained firmware, one active ESP-IDF 6.1 environment, and final documentation.

- [ ] **Step 1: Run the complete verification suite**

Run:

```bash
bash tools/test_esp32_s3.sh
bash tools/build_esp32_s3.sh
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 2: Verify the old IDF target before deletion**

Run: `git -C /data/esp/esp-idf describe --tags --always` and `realpath /data/esp/esp-idf`.

Expected: the path is exactly `/data/esp/esp-idf` and reports v5.5.5. If either check differs, stop and do not delete it.

- [ ] **Step 3: Remove only the verified old checkout and unused generated files**

Delete `/data/esp/esp-idf` after the exact-path/version checks. Use ESP-IDF’s tool-management command to list unused tools before removing any shared tools from `/data/esp/.espressif`; retain anything required by 6.1.

- [ ] **Step 4: Update final documentation**

Document the single-firmware architecture, IDF 6.1 environment, final pin map, `你好小云`, build/flash commands, official cloud activation, and explicit absence of voice-to-motion control.

- [ ] **Step 5: Inspect repository scope**

Run: `git status --short` and separate pre-existing unrelated changes from files touched by this implementation. Do not stage unrelated files.

- [ ] **Step 6: Commit final docs and cleanup**

Commit only in-scope source/docs/tool changes with `docs: finalize xiaozhi wheelbot bring-up`.

- [ ] **Step 7: Final evidence report**

Report exact build/test results, firmware size, flashed MAC/port, speaker test, microphone signal result, wake success count, cloud dialogue count, stop-only control verification, and any remaining user/account action.
