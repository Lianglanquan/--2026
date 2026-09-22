import struct

MAGIC = b'WB'
VERSION = 1
MSG_COMMAND = 1
MSG_STATE = 2
HEADER = struct.Struct('<2sBBHH')
COMMAND = struct.Struct('<BB4f2f')
STATE = struct.Struct('<I3f3f4f3f4f4f4B2f2f2f2IfI')


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode_frame(message_type: int, sequence: int, payload: bytes) -> bytes:
    header = HEADER.pack(MAGIC, VERSION, message_type, len(payload), sequence & 0xFFFF)
    body = header + payload
    return body + struct.pack('<H', crc16(body))


def decode_frame(frame: bytes, expected_type: int | None = None) -> tuple[int, int, bytes]:
    if len(frame) < HEADER.size + 2:
        raise ValueError('frame too short')
    magic, version, message_type, payload_len, sequence = HEADER.unpack_from(frame)
    if magic != MAGIC or version != VERSION:
        raise ValueError('invalid frame header')
    if expected_type is not None and message_type != expected_type:
        raise ValueError('unexpected message type')
    expected_len = HEADER.size + payload_len + 2
    if len(frame) != expected_len:
        raise ValueError('invalid frame length')
    body, received_crc = frame[:-2], struct.unpack_from('<H', frame, len(frame) - 2)[0]
    if crc16(body) != received_crc:
        raise ValueError('invalid frame crc')
    return sequence, message_type, frame[HEADER.size:-2]


def encode_command(sequence: int, enable: bool, mode: int, joint_target, wheel_command) -> bytes:
    if len(joint_target) != 4 or len(wheel_command) != 2:
        raise ValueError('command array sizes must be 4 joints and 2 wheels')
    return encode_frame(MSG_COMMAND, sequence, COMMAND.pack(int(enable), mode, *joint_target, *wheel_command))


def decode_command(frame: bytes) -> dict:
    sequence, _, payload = decode_frame(frame, MSG_COMMAND)
    values = COMMAND.unpack(payload)
    return {'sequence': sequence, 'enable': bool(values[0]), 'mode': values[1],
            'joint_target': list(values[2:6]), 'wheel_command': list(values[6:8])}


def decode_state(frame: bytes) -> dict:
    sequence, _, payload = decode_frame(frame, MSG_STATE)
    values = STATE.unpack(payload)
    i = 0
    state = {'sequence': sequence, 'timestamp_ms': values[i]}; i += 1
    for key, count in [('gyro', 3), ('accel', 3), ('quaternion', 4), ('rpy', 3),
                       ('joint_position', 4), ('joint_velocity', 4)]:
        state[key] = list(values[i:i + count]); i += count
    state['joint_status'] = list(values[i:i + 4]); i += 4
    for key in ('wheel_position', 'wheel_velocity', 'wheel_current'):
        state[key] = list(values[i:i + 2]); i += 2
    state['wheel_fault'] = list(values[i:i + 2]); i += 2
    state['battery_voltage'], state['faults'] = values[i], values[i + 1]
    return state


def drain_serial_buffer(buffer: bytearray) -> tuple[list[bytes], list[bytes]]:
    """Extract complete WB frames and newline-delimited USB text messages.

    The C Board emits both protocols on the same CDC stream. Binary payloads
    must be consumed by length, rather than by ``readline()``, because a WB
    frame may contain arbitrary newline bytes.
    """
    frames = []
    lines = []
    while buffer:
        if buffer.startswith(MAGIC):
            if len(buffer) < HEADER.size:
                break
            payload_len = int.from_bytes(buffer[4:6], 'little')
            total = HEADER.size + payload_len + 2
            if len(buffer) < total:
                break
            frames.append(bytes(buffer[:total]))
            del buffer[:total]
            continue

        magic_at = buffer.find(MAGIC)
        newline_at = buffer.find(b'\n')
        if magic_at >= 0 and (newline_at < 0 or magic_at < newline_at):
            del buffer[:magic_at]
            continue
        if newline_at < 0:
            break
        lines.append(bytes(buffer[:newline_at]).rstrip(b'\r'))
        del buffer[:newline_at + 1]
    return frames, lines


def read_until_pong(port, max_reads=8):
    """Read newline-delimited USB CDC output, preserving non-PONG diagnostics."""
    diagnostics = []
    for _ in range(max_reads):
        line = port.readline().strip()
        if not line:
            continue
        if line == b'PONG':
            return line, diagnostics
        diagnostics.append(line)
    return b'', diagnostics
