#include "face_state.h"

#include <cassert>
#include <cstring>

int main() {
    const WheelbotFaceState all[] = {
        WheelbotFaceState::kWake, WheelbotFaceState::kIdle, WheelbotFaceState::kBlink,
        WheelbotFaceState::kListening, WheelbotFaceState::kThinking, WheelbotFaceState::kHappy,
        WheelbotFaceState::kMoving, WheelbotFaceState::kExploring, WheelbotFaceState::kLowBattery,
        WheelbotFaceState::kSleep};
    for (auto state : all) assert(std::strlen(WheelbotFaceStateName(state)) > 0);
    assert(WheelbotFaceFromDeviceState("listening") == WheelbotFaceState::kListening);
    assert(WheelbotFaceFromDeviceState("speaking") == WheelbotFaceState::kHappy);
    assert(WheelbotFaceFromDeviceState("sleep") == WheelbotFaceState::kSleep);
    assert(WheelbotFaceFromEmotion("happy") == WheelbotFaceState::kHappy);
    assert(WheelbotFaceFromEmotion("thinking") == WheelbotFaceState::kThinking);
    return 0;
}
