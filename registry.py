"""
Registry that keeps track of all the known file receivers in the network.
"""
import asyncio
import json
import sys
from typing import *


class Registry:
    """
    Maintains a name->address mapping for known file receivers.
    """

    def __init__(self):
        self.receivers = {}

    def list(self) -> Dict[str, Tuple[str, int]]:
        return self.receivers

    def register(self, name: str, addr: Tuple[str, int]) -> None:
        self.receivers[name] = addr

    def unregister(self, name: str, addr: Tuple[str, int]) -> None:
        if name in self.receivers and self.receivers[name] == addr:
            del self.receivers[name]

    def receiver_by_name(self, name: str) -> Optional[Tuple[str, int]]:
        return self.receivers.get(name)


async def write_line(writer, message: str) -> None:
    writer.write((message + "\n").encode("utf8"))
    await writer.drain()


async def write_err(writer, e: Union[str, Exception]) -> None:
    await write_line(writer, f"ERR: {e}")


class RegistryConnector:
    """
    Logic for working with a Registry over the network.
    - requests and responses are line-oriented UTF-8 strings ending with `\n`
      - i.e. embedded newlines not allowed
    - error responses start with ERR
    """

    def __init__(self, reg: Registry):
        self.reg = reg

    async def client_connected(self, reader, writer) -> None:
        try:
            remote_addr = writer.get_extra_info("peername")
            print(f"connection from {remote_addr}")
            await self._client_connected(remote_addr, reader, writer)
        finally:
            print(f"closing connection to {remote_addr}")
            writer.close()
            await writer.wait_closed()

    async def _client_connected(
        self, remote_addr: Tuple[str, int], reader, writer
    ) -> None:
        while not reader.at_eof():
            args = (await reader.readline()).decode("utf8").split()
            print(f"{remote_addr}: received: {args}")
            if not args:
                continue
            if args[0] == "ls":
                content = json.dumps(self.reg.list(), sort_keys=True)
                await write_line(writer, content)
            elif args[0] == "register":
                try:
                    name = args[1]
                    port = int(args[2])
                    self.reg.register(name, (remote_addr[0], port))
                except Exception as e:
                    await write_err(writer, e)
                else:
                    await write_line(writer, "OK")

            elif args[0] == "unregister":
                try:
                    name = args[1]
                    port = int(args[2])
                    self.reg.unregister(name, (remote_addr[0], port))
                except Exception as e:
                    await write_err(writer, e)
                else:
                    await write_line(writer, "OK")
            elif args[0] == "lookup":
                try:
                    name = args[1]
                    addr = self.reg.receiver_by_name(name)
                    if not addr:
                        await write_err(writer, "not found")
                        continue
                    await write_line(writer, json.dumps(addr))
                except Exception as e:
                    await write_err(writer, e)


async def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>")
        sys.exit(1)
    host, port = sys.argv[1], int(sys.argv[2])

    reg = Registry()
    connector = RegistryConnector(reg)

    server = await asyncio.start_server(connector.client_connected, host, port)
    print(f"registry listening on {host}:{port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
