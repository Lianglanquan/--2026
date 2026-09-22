import unittest

from wheelbot_bridge.usb_protocol import (
    MSG_STATE,
    drain_serial_buffer,
    encode_frame,
    read_until_pong,
)


class FakePort:
    def __init__(self, lines):
        self._lines = iter(lines)

    def readline(self):
        return next(self._lines, b'')


class UsbProtocolTest(unittest.TestCase):
    def test_drains_interleaved_ascii_and_binary_messages(self):
        frame = encode_frame(MSG_STATE, 3, b"state")
        buffer = bytearray(b"diagnostic\r\n" + frame + b"PONG\r\n")

        frames, lines = drain_serial_buffer(buffer)

        self.assertEqual([frame], frames)
        self.assertEqual([b"diagnostic", b"PONG"], lines)
        self.assertEqual(bytearray(), buffer)

    def test_skips_diagnostic_lines_before_pong(self):
        port = FakePort([
            b'chassis motor4:ERROR!\r\n',
            b'gimbal motor:ERROR!\r\n',
            b'PONG\r\n',
        ])

        reply, diagnostics = read_until_pong(port, max_reads=8)

        self.assertEqual(b'PONG', reply)
        self.assertEqual(
            [b'chassis motor4:ERROR!', b'gimbal motor:ERROR!'], diagnostics
        )


if __name__ == '__main__':
    unittest.main()
