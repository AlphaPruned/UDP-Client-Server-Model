#!/usr/bin/env python3

import struct
import asyncio
import sys

class UAPAsyncServer:
    FORMAT = '!HBBIIQI'
    HELLO, DATA, GOODBYE = 0, 1, 2

    def __init__(self, host="localhost", port=12345, timer=10):
        self.host = host
        self.magic_num, self.version = 0xC461, 1
        self.port = port
        self.DEFAULT_TIMER = timer
        self.server = None
        self.sessionData = {}
        self.received_message = ""

    async def receive_data(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"Connection at {addr}")

        try:
            while True:
                # data is header + message
                data = await asyncio.wait_for(reader.read(100), timeout=self.DEFAULT_TIMER)
                header = struct.unpack(self.FORMAT, data[:7])

                if header[0]!=self.magic_num or header[1]!=self.version:
                    raise Exception("Protocol error: Magic Number Or version issue")

                command = header[2]
                session_id = header[4]
                if command == 0:  # HELLO from client
                    print(f"HELLO from {addr} received")
                    if session_id in self.sessionData:
                        raise Exception("Protocol Error: Session initiated")
                    else:
                        self.sessionData[session_id] = {
                            "seq": header[3],
                            "addr": addr,
                            "log_clk": header[5],
                            "state": self.HELLO
                        }
                        await self.send_data(0, session_id, writer)  # send HELLO to client
                elif command == 1:  # DATA from client
                    print(f"DATA from {addr} received")
                    if session_id in self.sessionData:
                        if self.sessionData[session_id]['state']!=self.DATA:
                            self.sessionData[session_id]['state'] = self.DATA

                        expected_seq_num = self.sessionData[session_id]['seq'] + 1
                        if header[3] > expected_seq_num:
                            raise Exception(f"Lost Packet. Expected Sequence Number {expected_seq_num}, received {header[3]}")
                        elif header[3] < expected_seq_num:
                            print(f"Duplicate Packet")
                        else:
                            self.sessionData[session_id]['seq'] = header[3]

                        self.received_message = data[7:].decode() if header[6] != 0 else ""
                        print(f"Data received from client addr {addr} : {self.received_message}")
                        await self.send_data(2, session_id, writer)
                    else:
                        raise Exception("Wild DATA request sent")
                elif command == 2:  # ALIVE from client
                    raise Exception("Protocol: Wild ALIVE request sent")
                elif command == 3:  #  GOODBYE from client
                    print(f"GOODBYE from {addr} received")
                    if session_id in self.sessionData:
                        self.sessionData[session_id]['state'] = self.GOODBYE
                        self.goodbye(addr, writer)
                    else:
                        raise Exception("Wild GOODBYE request sent")
                else:
                    raise Exception("Protocol error: Invalid command")
        except Exception as e:
            if e is asyncio.TimeoutError:
                print(f"Connection from {addr} timed out")
                error_message = 'Timeout! No data received.'.encode()
            else:
                print(e)
                error_message = 'Protocol Error'.encode()
            self.goodbye(addr, writer)
            writer.write(error_message)
            await writer.drain()

    async def send_data(self, command, session_id, writer):
        seq_num = self.sessionData[session_id]['seq']
        header = struct.pack(self.FORMAT, self.magic_num, self.version, command, seq_num, session_id, 0)

        # send header
        writer.write(header)
        await writer.drain()

    def goodbye(self, session_id, writer):
        self.send_data(3, session_id, writer)
        self.sessionData.pop(session_id)

    async def start(self):
        self.server = await asyncio.start_server(self.receive_data, self.host, self.port)
        addr = self.server.sockets[0].getsockname()
        print(f"Listening at {addr}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("Server closed")

if __name__ == "__main__":
    async def main(port):
        server = UAPAsyncServer(port=port)
        try:
            await server.start()
        except KeyboardInterrupt:
            await server.stop()

    asyncio.run(main(int(sys.argv[1])))
