#!/usr/bin/env python3

import asyncio
import struct
import sys

class UAPAsyncUDPServer(asyncio.DatagramProtocol):
    FORMAT = '!HBBIIQI'
    HELLO, DATA, ALIVE, GOODBYE = 0, 1, 2, 3  # Command definitions

    def __init__(self, port, timer=10):
        self.magic_num = 0xC461
        self.version = 1
        self.port = port
        self.DEFAULT_TIMER = timer
        self.sessionData = {}
        self.received_message = ""

    def connection_made(self, transport):
        self.transport = transport
        print(f"UDP server is up and listening on port {self.port}...")

    def datagram_received(self, data, addr):
        try:
            header = struct.unpack(self.FORMAT, data[:24])
            if header[0] != self.magic_num or header[1] != self.version:
                raise ValueError(f"Protocol error: Magic Number or version mismatch. Got {header[0]} and {header[1]}")

            command = header[2]
            session_id = header[4]

            print(f"Received command {command} with session ID {session_id}")
            print(f"Current Session Data: {self.sessionData}")

            if command == self.HELLO:  # HELLO from client
                print(f"HELLO from {addr} received")
                if session_id in self.sessionData:
                    raise ValueError(f"Protocol Error: Session already initiated for session ID {session_id}")
                else:
                    self.sessionData[session_id] = {
                        "seq": header[3],
                        "addr": addr,
                        "log_clk": header[5],
                        "state": self.HELLO
                    }
                    self.send_data(self.HELLO, session_id, addr)  # send HELLO response to client

            elif command == self.DATA:  # DATA from client
                print(f"DATA from {addr} received")
                if session_id in self.sessionData:
                    expected_seq_num = self.sessionData[session_id]['seq'] + 1
                    if header[3] > expected_seq_num:
                        raise ValueError(f"Lost Packet. Expected Sequence Number {expected_seq_num}, received {header[3]}")
                    elif header[3] < expected_seq_num:
                        print(f"Duplicate Packet")
                    else:
                        self.sessionData[session_id]['seq'] = header[3]

                    self.received_message = data[24:].decode() if header[6] != 0 else ""
                    print(f"Data received from client addr {addr}: {self.received_message}")
                    
                    # Send ALIVE message after receiving DATA
                    self.send_data(self.DATA, session_id, addr)  # Respond to DATA
                    self.send_data(self.ALIVE, session_id, addr)  # Send ALIVE response
                    
                else:
                    raise ValueError(f"Wild DATA request sent for session {session_id}")

            elif command == self.GOODBYE:  # GOODBYE from client
                print(f"GOODBYE from {addr} received")
                if session_id in self.sessionData:
                    # Send GOODBYE response before closing the session
                    self.send_data(self.GOODBYE, session_id, addr)
                    # Remove session data
                    self.sessionData.pop(session_id)
                else:
                    raise ValueError(f"Wild GOODBYE request sent for session {session_id}")

            else:
                raise ValueError(f"Protocol error: Invalid command {command}")

        except ValueError as e:
            print(f"Value Error: {str(e)}")
            print(f"Received data: {data}")
            print(f"Header: {header}")
            print(f"Session Data: {self.sessionData}")
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            print(f"Received data: {data}")
            print(f"Header: {header}")
            print(f"Session Data: {self.sessionData}")

    def send_data(self, command, session_id, addr):
        if session_id in self.sessionData:
            seq_num = self.sessionData[session_id]['seq']
            header = struct.pack(self.FORMAT, self.magic_num, self.version, command, seq_num, session_id, 0, 0)
            self.transport.sendto(header, addr)
        else:
            print(f"Warning: Attempt to send data for non-existent session ID {session_id}")

async def main(port):
    print(f"Starting UDP server on port {port}")
    loop = asyncio.get_event_loop()
    _, protocol = await loop.create_datagram_endpoint(
        lambda: UAPAsyncUDPServer(port),
        local_addr=('0.0.0.0', port)
    )

    try:
        await asyncio.sleep(360)  # Keep the server running for 1 hour
    finally:
        protocol.transport.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    asyncio.run(main(port))
