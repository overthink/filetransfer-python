"""
Registry that keeps track of all the known file receivers in the network.
"""
import asyncio
import json
import os
import sys
from typing import *

REGISTRY_IP = os.environ.get("REGISTRY_IP", "127.0.0.1")
REGISTRY_PORT = int(os.environ.get("REGISTRY_PORT", "60000"))
SAVE_DIR = os.environ.get("SAVE_DIR", "files")


async def client_connected(reader, writer) -> None:
    try:
        remote_addr = writer.get_extra_info("peername")
        print(f"connection from {remote_addr}")
        await _client_connected(reader, writer)
    finally:
        print(f"closing connection to {remote_addr}")
        writer.close()
        await writer.wait_closed()


async def aio_input(message: str) -> str:
    """Collect user inptu from console in an async way."""
    loop = asyncio.get_running_loop()

    def write_message():
        sys.stdout.write(message)
        sys.stdout.flush()

    await loop.run_in_executor(None, write_message)
    return await loop.run_in_executor(None, sys.stdin.readline)


async def _client_connected(reader, writer) -> None:
    args = (await reader.readline()).decode("utf8").split()
    print(f"received: {args}")
    if not args:
        return
    if args[0] == "send" and len(args) >= 4:
        username = args[1]
        filename = args[2]
        filesize = args[3]
        print(f"{username} wants to send you {filename} ({filesize} bytes)")
        while True:
            result = (await aio_input("Accept? y/n: ")).lower().strip()
            if result in ["y", "n"]:
                break
        if result == "n":
            writer.write("403\n".encode("utf8"))
            await writer.drain()
            return
        writer.write("200\n".encode("utf8"))
        await writer.drain()

        # TODO: make async
        written = 0
        with open(SAVE_DIR + "/" + filename, "wb") as f:
            while True:
                chunk = await reader.read(4096)
                if chunk == b"" or written == filesize:
                    break
                # TODO: check we're not writing too many bytes
                f.write(chunk)
                written += len(chunk)


async def register(registry_addr: Tuple[str, int], name: str, port: int) -> None:
    """Contact the registry server and let it know we exist."""
    _, writer = await asyncio.open_connection(*registry_addr)
    writer.write(f"register {name} {port}\n".encode("utf8"))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def unregister(registry_addr: Tuple[str, int], name: str, port: int) -> None:
    """Tell the registry we're going away."""
    _, writer = await asyncio.open_connection(*registry_addr)
    writer.write(f"unregister {name} {port}\n".encode("utf8"))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main() -> None:
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <host> <port> <username>")
        sys.exit(1)
    host, port = sys.argv[1], int(sys.argv[2])
    username = sys.argv[3]

    server = await asyncio.start_server(client_connected, host, port)
    registry_addr = (REGISTRY_IP, REGISTRY_PORT)
    await register(registry_addr, username, port)
    print(f"receiver listening on {host}:{port}")
    try:
        async with server:
            await server.serve_forever()
    finally:
        await unregister(registry_addr, username, port)


if __name__ == "__main__":
    asyncio.run(main())
