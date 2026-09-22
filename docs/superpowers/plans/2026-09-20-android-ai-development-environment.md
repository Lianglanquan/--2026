# Android AI Development Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install and verify a complete command-line Android development environment that Codex can use without Android Studio.

**Architecture:** Store large Android SDK, emulator, AVD, and Gradle cache data under `/data` because the root filesystem is nearly full. Expose the SDK at the conventional `~/Android/Sdk` path through a symlink, configure all interactive shells from one environment file, and retain Android Studio only as an optional GUI.

**Tech Stack:** OpenJDK 21, Android SDK command-line tools 15859902, SDK Platforms 36 and 36.1, Build Tools 36.0.0 and 36.1.0, Android Emulator, Google APIs API 36.1 x86_64 system image, Google Android CLI, Gradle Wrapper, NDK 30, CMake 4.1.2.

**Spec:** Direct user request in the 2026-09-20 Codex task to install the complete environment required for AI-driven Android app development.

## Global Constraints

- Do not modify or discard any existing project changes.
- Install large artifacts under `/data`, not the 93%-full root filesystem.
- Use stable Android SDK packages only.
- Android Studio must remain optional; every verification step must work from the command line.
- Verify downloads with the SHA-256 checksum published by Android Developers.

---

### Task 1: Install the command-line front ends

**Files:**
- Create: `/data/Android/Sdk/cmdline-tools/latest/**`
- Create: `/home/fool/Android/Sdk` symlink to `/data/Android/Sdk`
- Create: Google Android CLI files under its official per-user install location

**Interfaces:**
- Consumes: OpenJDK 21 and network access.
- Produces: `sdkmanager`, `avdmanager`, and `android` commands.

- [x] **Step 1: Download the official Linux command-line tools archive**

Run: download `https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip` to a temporary directory.

- [x] **Step 2: Verify the archive**

Run: `sha256sum commandlinetools-linux-15859902_latest.zip`

Expected: `4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583`.

- [x] **Step 3: Extract the standard tools and install Google Android CLI**

Create the documented `cmdline-tools/latest` layout, then execute the official Google Android CLI installer after inspecting the downloaded installer script.

- [x] **Step 4: Verify both front ends**

Run: `sdkmanager --version`, `avdmanager list target`, and `android --version`.

Expected: all commands exit successfully.

### Task 2: Install SDK, native, and emulator packages

**Files:**
- Create: `/data/Android/Sdk/platform-tools/**`
- Create: `/data/Android/Sdk/platforms/android-36/**`
- Create: `/data/Android/Sdk/platforms/android-36.1/**`
- Create: `/data/Android/Sdk/build-tools/36.0.0/**`
- Create: `/data/Android/Sdk/build-tools/36.1.0/**`
- Create: `/data/Android/Sdk/emulator/**`
- Create: `/data/Android/Sdk/system-images/android-36.1/google_apis/x86_64/**`
- Create: current stable NDK and CMake package directories selected from `sdkmanager --list`

**Interfaces:**
- Consumes: `sdkmanager` from Task 1.
- Produces: tools and APIs required for Kotlin/Compose, APK/AAB, emulator, and optional native-code builds.

- [x] **Step 1: Accept Android SDK package licenses**

Run: `yes | sdkmanager --licenses --sdk_root=/data/Android/Sdk`.

- [x] **Step 2: Install stable packages**

Install `platform-tools`, `platforms;android-36`, `platforms;android-36.1`, `build-tools;36.0.0`, `build-tools;36.1.0`, `emulator`, `system-images;android-36.1;google_apis;x86_64`, `ndk;30.0.16248370`, and `cmake;4.1.2`, as reported by the stable `sdkmanager --list` channel.

- [x] **Step 3: Verify package inventory**

Run: `sdkmanager --list_installed --sdk_root=/data/Android/Sdk`.

Expected: every requested package is listed as installed.

### Task 3: Configure persistent environment and an AVD

**Files:**
- Create: `/home/fool/.config/android/env.sh`
- Modify: `/home/fool/.profile`
- Modify: `/home/fool/.bashrc`
- Modify: `/home/fool/.zshrc`
- Create: `/data/Android/avd/AI_Android_API_36_1.avd/**`

**Interfaces:**
- Consumes: installed SDK tools and system image.
- Produces: reliable paths for Codex shell sessions and a reusable API 36 emulator.

- [x] **Step 1: Create data directories and compatibility symlink**

Create `/data/Android/avd`, `/data/Android/user-home`, `/data/Gradle`, and point `/home/fool/Android/Sdk` to `/data/Android/Sdk`.

- [x] **Step 2: Create a shared shell environment file**

Set `ANDROID_HOME`, `ANDROID_SDK_ROOT`, `ANDROID_USER_HOME`, `ANDROID_AVD_HOME`, and `GRADLE_USER_HOME`; prepend the command-line tools, platform tools, and emulator directories to `PATH` without duplicates.

- [x] **Step 3: Source the environment from supported shells**

Add one guarded source line to `.profile`, `.bashrc`, and `.zshrc`.

- [x] **Step 4: Create the virtual device**

Run `avdmanager create avd` using `system-images;android-36.1;google_apis;x86_64` and a Pixel hardware profile.

- [x] **Step 5: Verify shell and AVD discovery**

Start a fresh login shell and run `sdkmanager --version`, `adb version`, `emulator -list-avds`, and `android --version`.

Expected: tools resolve from the configured paths and `AI_Android_API_36_1` is listed.

### Task 4: End-to-end validation

**Files:**
- Create: `/data/Android/validation/HelloAndroid/**`
- Create: `/data/Android/validation/emulator.log`

**Interfaces:**
- Consumes: the complete environment from Tasks 1-3.
- Produces: evidence that project generation, dependency resolution, compilation, emulator boot, installation, and launch all work without Android Studio.

- [x] **Step 1: Generate a minimal Android application**

Run the Google Android CLI `create empty-activity` command under `/data/Android/validation/HelloAndroid`.

- [x] **Step 2: Build a debug APK**

Run: `./gradlew assembleDebug --stacktrace`.

Expected: `BUILD SUCCESSFUL` and a debug APK under the app module's `build/outputs/apk/` directory.

- [x] **Step 3: Boot the API 36 AVD headlessly**

Launch `AI_Android_API_36_1` with KVM acceleration and wait until `adb shell getprop sys.boot_completed` returns `1`.

- [x] **Step 4: Install and launch the debug APK**

Run the project's `installDebug` task or `adb install`, then launch its main activity.

- [x] **Step 5: Verify runtime state**

Confirm the package is installed, the main activity process is running, and capture a screenshot under `/data/Android/validation/`.

- [x] **Step 6: Stop the emulator cleanly**

Run: `adb emu kill`.
