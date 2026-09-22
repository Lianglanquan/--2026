"""TCP-to-PTY byte bridge for transparent YDLIDAR serial transport."""

import argparse
import asyncio
import collections
import os
import pty
import time
import tty
from pathlib import Path


def forward_chunks(chunks, write_fn):
    for chunk in chunks:
        view = memoryview(chunk)
        while view:
            written = write_fn(view)
            if not written:
                raise IOError("PTY write made no progress")
            view = view[written:]


async def _relay(reader, master_fd, stats):
    while True:
        data = await reader.read(4096)
        if not data:
            return
        stats["bytes"] += len(data)
        stats["chunks"] += 1
        stats["unique"].update(data)
        stats["zeros"] += data.count(0)
        stats["a5"] += data.count(b"\xa5")
        stats["printable"] += sum(32 <= b < 127 for b in data)
        if stats["first_hex"] is None:
            stats["first_hex"] = data[:64].hex()
        forward_chunks((data,), lambda view: os.write(master_fd, view))


async def run(host, port, device_link=None):
    master_fd, slave_fd = pty.openpty()
    tty.setraw(slave_fd)
    slave_name = os.ttyname(slave_fd)
    if device_link:
        link = Path(device_link)
        tmp_link = link.with_name(link.name + ".tmp")
        try:
            tmp_link.unlink()
        except FileNotFoundError:
            pass
        tmp_link.symlink_to(slave_name)
        os.replace(tmp_link, link)
    print(slave_name, flush=True)

    stats = {"bytes": 0, "chunks": 0, "unique": set(), "zeros": 0,
             "a5": 0, "printable": 0, "first_hex": None,
             "last_report": time.monotonic()}

    async def report_stats():
        while True:
            await asyncio.sleep(5)
            print(
                "stats bytes=%d chunks=%d unique=%d zero=%d a5=%d printable=%d first=%s"
                % (stats["bytes"], stats["chunks"], len(stats["unique"]),
                   stats["zeros"], stats["a5"], stats["printable"],
                   stats["first_hex"] or "-"),
                flush=True,
            )

    async def handle(reader, writer):
        try:
            peer = writer.get_extra_info("peername")
            print(f"client_connected peer={peer}", flush=True)
            await _relay(reader, master_fd, stats)
        finally:
            print("client_disconnected", flush=True)
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, host, port)
    asyncio.create_task(report_stats())
    async with server:
        await server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8889)
    parser.add_argument('--device-link', default=None,
                        help='Atomically create a symlink to the PTY slave')
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, args.device_link))


if __name__ == '__main__':
    main()
