"""
Client for sending files to a named receiver.
This thing doesn't really need asyncio, but I stuck with it for symmetry with
the other pieces of the system.
"""
import asyncio
import json
import os
import sys
from typing import *


REGISTRY_IP = os.environ.get("REGISTRY_IP", "127.0.0.1")
REGISTRY_PORT = int(os.environ.get("REGISTRY_PORT", "60000"))


async def write_line(writer, message: str) -> None:
    writer.write((message + "\n").encode("utf8"))
    await writer.drain()


async def get_receiver(recipient: str) -> Tuple[str, int]:
    reader, writer = await asyncio.open_connection(REGISTRY_IP, REGISTRY_PORT)
    await write_line(writer, f"lookup {recipient}")
    resp = (await reader.readline()).decode("utf8")
    if resp.startswith("ERR"):
        raise Exception(f"user {recipient} not found: {resp}")
    json_resp = json.loads(resp)
    return (json_resp[0], json_resp[1])


async def main() -> None:
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} send <recipient> <file>")
        sys.exit(1)
    command = "send"
    recipient = sys.argv[2]
    file_ = sys.argv[3]
    filesize = os.path.getsize(file_)

    peer_addr = await get_receiver(recipient)
    print(f"{recipient} found at {peer_addr}")

    reader, writer = await asyncio.open_connection(*peer_addr)
    filename = file_.rsplit("/", 1)[-1]
    await write_line(writer, f"send {recipient} {filename} {filesize}")
    response = (await reader.readline()).decode("utf8").strip()
    if response == "OK":
        with open(file_, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        print("file sent")
        writer.close()
        await writer.wait_closed()
    else:
        print("computer said no")


if __name__ == "__main__":
    asyncio.run(main())
