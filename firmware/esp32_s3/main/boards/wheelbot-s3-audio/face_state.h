#ifndef WHEELBOT_FACE_STATE_H
#define WHEELBOT_FACE_STATE_H

#include <cstdint>

enum class WheelbotFaceState : uint8_t {
    kWake = 0,
    kIdle,
    kBlink,
    kListening,
    kThinking,
    kHappy,
    kMoving,
    kExploring,
    kLowBattery,
    kSleep,
};

const char* WheelbotFaceStateName(WheelbotFaceState state);
WheelbotFaceState WheelbotFaceFromDeviceState(const char* state_name);
WheelbotFaceState WheelbotFaceFromEmotion(const char* emotion);

#endif
