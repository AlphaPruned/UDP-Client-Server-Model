#!/usr/bin/env python3

import asyncio
import struct
import time
import sys

class State:
    HELLO_SEND = 0
    HELLO_WAIT = 1
    DATA_SEND = 2
    ALIVE_WAIT = 3
    GOODBYE_SEND = 4
    CLOSED = 5

class UAPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop, server_address, port):
        self.loop = loop
        self.server_address = (server_address, port)
        self.magic_number = 0xC461
        self.version = 1
        self.client_sequence_number = 0
        self.session_id = self.generate_session_id()
        self.logical_clock = 0
        self.state = State.HELLO_SEND
        self.retries = 0
        self.max_retries = 1  # No retries, just wait for the first ALIVE response
        self.is_file_input = not sys.stdin.isatty()

    def generate_session_id(self):
        
        return struct.unpack("I", struct.pack("I", int(time.time())))[0]

    def connection_made(self, transport):
        
        self.transport = transport
        self.start_session()

    def start_session(self):
        
        self.send_message(command=0)  # HELLO command
        self.state = State.HELLO_WAIT
        self.loop.call_later(5, self.hello_timeout)

    def send_message(self, command, payload=b''):
        
        header = struct.pack(
            '!HBBIIQI',
            self.magic_number,
            self.version,
            command,
            self.client_sequence_number,
            self.session_id,
            self.logical_clock,
            len(payload)
        )
        message = header + payload
        self.transport.sendto(message, self.server_address)
        
        # Update sequence number and logical clock
        self.client_sequence_number += 1
        self.logical_clock += 1

        print(f"Sent message: Command={command}, Sequence={self.client_sequence_number - 1}, Logical Clock={self.logical_clock}")

    def datagram_received(self, data, addr):
        
        self.handle_server_response(data)

    def handle_server_response(self, data):
        
        header = data[:24]
        payload = data[24:]
        
        (magic, version, command, sequence_number, session_id, logical_clock, payload_len) = struct.unpack(
            '!HBBIIQI', header
        )

        if magic != self.magic_number or version != self.version or session_id != self.session_id:
            print("Invalid packet received")
            return

        # Update logical clock
        self.logical_clock = max(self.logical_clock, logical_clock) + 1
        print(f"Updated logical clock: {self.logical_clock}")

        if command == 0:  # HELLO response
            self.handle_hello_response()

        elif command == 2:  # ALIVE response
            self.handle_alive_response()

        elif command == 3:  # GOODBYE
            self.handle_goodbye_response()

    def handle_hello_response(self):
        
        if self.state == State.HELLO_WAIT:
            print("Received HELLO response, session established")
            self.state = State.DATA_SEND
            asyncio.create_task(self.send_data())

    def handle_alive_response(self):
        
        if self.state == State.ALIVE_WAIT:
            print("Server is alive, received ALIVE response")
            self.state = State.DATA_SEND
            self.retries = 0  # Reset retries

    def handle_goodbye_response(self):
        
        print("Server sent GOODBYE, closing session")
        self.state = State.CLOSED
        self.transport.close()
        self.loop.call_soon(self.loop.stop)  # Stop the loop after handling GOODBYE

    async def send_data(self):
        
        if self.is_file_input:
            for line in sys.stdin:
                if self.state == State.CLOSED:
                    break
                self.send_message(1, line.encode())  # Send DATA message
                self.state = State.ALIVE_WAIT
                await self.wait_for_alive_response()
        else:
            await self.send_data_interactive()


    async def send_data_interactive(self):
        
        while self.state != State.CLOSED:
            user_input = input("Enter data to send (or 'q' to quit): ")
            if user_input.lower() == 'q':
                print("Received 'q', sending GOODBYE and closing session")
                self.state = State.GOODBYE_SEND
                self.send_message(3)  # Send GOODBYE command
                break
            else:
                self.send_message(1, user_input.encode())  # Send DATA message
                self.state = State.ALIVE_WAIT
                await self.wait_for_alive_response()

    async def wait_for_alive_response(self):
        
        await asyncio.sleep(5)  # Wait for 5 seconds for the ALIVE response
        if self.state == State.ALIVE_WAIT:
            print("ALIVE response timeout, sending GOODBYE and closing session.")
            self.send_message(3)  # Send GOODBYE message
            self.state = State.CLOSED
            self.transport.close()  # Close the transport
            self.loop.call_soon(self.loop.stop)  # Stop the loop

    def hello_timeout(self):
        
        if self.state == State.HELLO_WAIT:
            self.retries += 1
            if self.retries > self.max_retries:
                print("HELLO response timeout, sending GOODBYE and terminating.")
                self.send_message(3)  # GOODBYE command
                self.state = State.CLOSED
            else:
                print("HELLO response timeout, resending HELLO.")
                self.send_message(0)  # Resend HELLO

async def main(server_ip, server_port):
    
    loop = asyncio.get_event_loop()
    try:
        # Create a datagram endpoint (UDP client) depending on the IP version
        if ':' in server_ip:  # IPv6 address
            connect = loop.create_datagram_endpoint(
                lambda: UAPClientProtocol(loop, server_ip, server_port),
                remote_addr=(server_ip, server_port, 0, 0)
            )
        else:  # IPv4 address
            connect = loop.create_datagram_endpoint(
                lambda: UAPClientProtocol(loop, server_ip, server_port),
                remote_addr=(server_ip, server_port)
            )
        
        transport, protocol = await connect
        
        # Track the main task to allow for cancellation
        sleep_task = loop.create_task(asyncio.sleep(3600))  # Long-running task to keep the client active

        # Wait for either the sleep to complete or the protocol to close the session
        await sleep_task

    except Exception as e:
        print(f"Error occurred: {e}")

    finally:
        # Ensure that all tasks are cancelled before stopping the loop
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        loop.stop()  # Ensure loop is stopped when done


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    asyncio.run(main(server_ip, server_port))
