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


class RegistryConnector:
    """
    Logic for working with a Registry over the network.
    - protocol is line-oriented UTF-8 strings
    - one request per connection
    - input is whitespace sepearated args
    - output is json
    - yes it's weird that input and output are not both json, but it's easier
      to test with nc this way
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
        args = (await reader.readline()).decode("utf8").split()
        print(f"received: {args}")
        if not args:
            return
        if args[0] == "ls":
            content = json.dumps(self.reg.list(), sort_keys=True) + "\n"
            writer.write(content.encode("utf8"))
            await writer.drain()
        elif args[0] == "register":
            name = args[1]
            port = int(args[2])
            self.reg.register(name, (remote_addr[0], port))
        elif args[0] == "unregister":
            name = args[1]
            port = int(args[2])
            self.reg.unregister(name, (remote_addr[0], port))


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
