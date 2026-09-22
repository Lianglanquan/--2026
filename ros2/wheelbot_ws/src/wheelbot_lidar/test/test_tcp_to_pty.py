import pytest

from wheelbot_lidar.tcp_to_pty import forward_chunks


def test_forward_chunks_preserves_binary_lidar_bytes_and_handles_partial_writes():
    chunks = [b"\xaa\x55\x00", b"\x01\xff\x00"]
    written = bytearray()

    def partial_write(data):
        count = min(2, len(data))
        written.extend(data[:count])
        return count

    forward_chunks(chunks, partial_write)

    assert bytes(written) == b"\xaa\x55\x00\x01\xff\x00"


def test_forward_chunks_rejects_zero_progress_to_avoid_busy_loop():
    with pytest.raises(IOError, match="no progress"):
        forward_chunks([b"data"], lambda _: 0)
