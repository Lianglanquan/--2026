#include "face_state.h"

#include <cstring>

const char* WheelbotFaceStateName(WheelbotFaceState state) {
    switch (state) {
        case WheelbotFaceState::kWake: return "wake";
        case WheelbotFaceState::kIdle: return "idle";
        case WheelbotFaceState::kBlink: return "blink";
        case WheelbotFaceState::kListening: return "listening";
        case WheelbotFaceState::kThinking: return "thinking";
        case WheelbotFaceState::kHappy: return "happy";
        case WheelbotFaceState::kMoving: return "moving";
        case WheelbotFaceState::kExploring: return "exploring";
        case WheelbotFaceState::kLowBattery: return "low_battery";
        case WheelbotFaceState::kSleep: return "sleep";
    }
    return "idle";
}

WheelbotFaceState WheelbotFaceFromDeviceState(const char* s) {
    if (!s) return WheelbotFaceState::kIdle;
    if (!std::strcmp(s, "starting") || !std::strcmp(s, "activating")) return WheelbotFaceState::kWake;
    if (!std::strcmp(s, "listening")) return WheelbotFaceState::kListening;
    if (!std::strcmp(s, "speaking") || !std::strcmp(s, "notifying")) return WheelbotFaceState::kHappy;
    if (!std::strcmp(s, "connecting") || !std::strcmp(s, "upgrading")) return WheelbotFaceState::kThinking;
    if (!std::strcmp(s, "wifi_configuring") || !std::strcmp(s, "audio_testing")) return WheelbotFaceState::kExploring;
    if (!std::strcmp(s, "sleep")) return WheelbotFaceState::kSleep;
    if (!std::strcmp(s, "moving")) return WheelbotFaceState::kMoving;
    return WheelbotFaceState::kIdle;
}

WheelbotFaceState WheelbotFaceFromEmotion(const char* e) {
    if (!e) return WheelbotFaceState::kIdle;
    if (!std::strcmp(e, "happy") || !std::strcmp(e, "laughing") || !std::strcmp(e, "love") || !std::strcmp(e, "excited")) return WheelbotFaceState::kHappy;
    if (!std::strcmp(e, "thinking") || !std::strcmp(e, "confused")) return WheelbotFaceState::kThinking;
    if (!std::strcmp(e, "listening") || !std::strcmp(e, "surprised")) return WheelbotFaceState::kListening;
    if (!std::strcmp(e, "sleep") || !std::strcmp(e, "sleeping")) return WheelbotFaceState::kSleep;
    return WheelbotFaceState::kIdle;
}
