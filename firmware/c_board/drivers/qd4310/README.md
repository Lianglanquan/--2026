# QD4310 CAN1 adapter

This directory contains only the C Board transport/codec adapter. It does not
implement FOC, an encoder, or a replacement CAN stack.

## Protocol evidence

The frame definitions were cross-checked against the supplied official files
`QD4310使用手册.pdf` and `QD4310例程代码.zip` (STM32 C example), as well as
the public QDrive source repository at commit
`3e4c73b42183fc4cf4afab04f04fd502f3c7d73e`:

- `Applications/Src/CommunicationProtocol.md`
- `Applications/Src/CommunicateTask.cpp`

The official source states classic CAN at 1 Mbps, command IDs `0x400 + ID`,
feedback IDs `0x500 + ID`, 3-byte control frames, and 8-byte feedback frames.
The command byte is byte 0 and the signed control value is little-endian in
bytes 1..2. Feedback is `state,error,current(int16),speed(int16),angle(uint16)`
in little-endian order. Current, speed, and angle are scaled respectively to
`[-10,10] A`, `[-1000,1000] rpm`, and `[0,2pi] rad`.

The implementation follows the public QGimbal QD4310 transport behavior:
`NOP`, enable, disable, current, speed, angle, low-speed, step-angle, reboot,
set-zero, and clear-error are all available through the C API. Speed and
current inputs are clamped to the device ranges before conversion; absolute
angle is clamped to `[0,2pi]`, and step angle to `[-2pi,2pi]`. Source reference:
<https://github.com/Liu-Curiousity/QGimbal>.

## C Board integration

`qd4310.c` calls the existing `HAL_CAN_AddTxMessage(&hcan1, ...)`; it does not
configure a second CAN peripheral or abstract the DJI BSP. The existing RX
callback should call `qd4310_handle_can_rx()` after `HAL_CAN_GetRxMessage()` for
feedback frames. The cached state is updated asynchronously; `qd4310_get_state`
sends the official NOP request and returns the most recently received state.

The current CMake build is configured for one installed motor, ID 1. The
second wheel remains reserved as ID 2; rebuild with
`-DWHEELBOT_QD4310_COUNT=2` after that motor is installed and the CAN bus has
been verified. Correct CANH/CANL termination, common ground, and a verified
1 Mbps bus are required for end-to-end validation.
