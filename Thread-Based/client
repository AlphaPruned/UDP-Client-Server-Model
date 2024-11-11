#!/usr/bin/env python3

import socket
import struct
import time
import threading
import sys

class State:
    HELLO_SEND = 0
    HELLO_WAIT = 1
    DATA_SEND = 2
    ALIVE_WAIT = 3
    GOODBYE_SEND = 4
    CLOSED = 5

class UAPClient:
    def __init__(self, server_address, port):
        self.server_address = (server_address, port)
        self.magic_number = 0xC461
        self.version = 1
        self.client_sequence_number = 0
        self.session_id = self.generate_session_id()
        self.logical_clock = 0
        self.state = State.HELLO_SEND
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(5.0)
        self.lock = threading.Lock()
        self.retries = 0
        self.max_retries = 3
        self.is_file_input = not sys.stdin.isatty()

    def generate_session_id(self):
        return struct.unpack("I", struct.pack("I", int(time.time())))[0]

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
        self.socket.sendto(message, self.server_address)
        self.client_sequence_number += 1
        self.logical_clock += 1
        print(f"Sent message: Command={command}, Sequence={self.client_sequence_number - 1}, Logical Clock={self.logical_clock}")

    def receive_message(self):
        try:
            data, _ = self.socket.recvfrom(1024)
            return data
        except socket.timeout:
            return None

    def handle_server_response(self, data):
        header = data[:24]
        payload = data[24:]
        (magic, version, command, sequence_number, session_id, logical_clock, payload_len) = struct.unpack(
            '!HBBIIQI', header
        )

        if magic != self.magic_number or version != self.version or session_id != self.session_id:
            print("Invalid packet received")
            return

        self.logical_clock = max(self.logical_clock, logical_clock) + 1
        print(f"Updated logical clock: {self.logical_clock}")

        if command == 0:  # HELLO response
            if self.state == State.HELLO_WAIT:
                print("Received HELLO response, session established")
                self.state = State.DATA_SEND
        elif command == 2:  # ALIVE response
            if self.state == State.ALIVE_WAIT:
                print("Server is alive, received ALIVE response")
                self.state = State.DATA_SEND
                self.retries = 0  # Reset retries
        elif command == 3:  # GOODBYE
            print("Server sent GOODBYE, closing session")
            self.state = State.CLOSED

    def hello_timeout(self):
        with self.lock:
            if self.state == State.HELLO_WAIT:
                self.retries += 1
                if self.retries > self.max_retries:
                    print("HELLO response timeout, sending GOODBYE and terminating.")
                    self.send_message(3)  # Send GOODBYE
                    self.state = State.CLOSED
                else:
                    print("HELLO response timeout, resending HELLO.")
                    self.send_message(0)  # Resend HELLO

    def alive_timeout(self):
        with self.lock:
            if self.state == State.ALIVE_WAIT:
                self.retries += 1
                if self.retries > self.max_retries:
                    print("ALIVE response timeout, sending GOODBYE and terminating.")
                    self.send_message(3)  # Send GOODBYE
                    self.state = State.CLOSED
                else:
                    print("ALIVE response timeout, resending DATA.")
                    self.send_message(1, b"Some data...")  # Resend DATA

    def start(self):
        print("Client started. Waiting for messages...")

        if self.is_file_input:
            # Handle input from file
            while self.state != State.CLOSED:
                if self.state == State.HELLO_SEND:
                    print("Sending HELLO message to start session")
                    self.send_message(0)  # Send HELLO
                    self.state = State.HELLO_WAIT

                elif self.state == State.HELLO_WAIT:
                    data = self.receive_message()
                    if data:
                        self.handle_server_response(data)
                    else:
                        self.hello_timeout()

                elif self.state == State.DATA_SEND:
                    # Read from stdin and send data
                    for line in sys.stdin:
                        if self.state == State.CLOSED:
                            break
                        self.send_message(1, line.encode())  # Send DATA message with file input
                        self.state = State.ALIVE_WAIT

                        # Wait for ALIVE response
                        while self.state == State.ALIVE_WAIT:
                            data = self.receive_message()
                            if data:
                                self.handle_server_response(data)
                            else:
                                self.alive_timeout()
                    # After file input is complete
                    if self.state != State.CLOSED:
                        self.state = State.GOODBYE_SEND

                elif self.state == State.ALIVE_WAIT:
                    data = self.receive_message()
                    if data:
                        self.handle_server_response(data)
                    else:
                        self.alive_timeout()

                elif self.state == State.GOODBYE_SEND:
                    print("Sending GOODBYE to end session")
                    self.send_message(3)  # Send GOODBYE
                    self.state = State.CLOSED

        else:
            # Handle interactive user input
            while self.state != State.CLOSED:
                if self.state == State.HELLO_SEND:
                    print("Sending HELLO message to start session")
                    self.send_message(0)  # Send HELLO
                    self.state = State.HELLO_WAIT

                elif self.state == State.HELLO_WAIT:
                    data = self.receive_message()
                    if data:
                        self.handle_server_response(data)
                    else:
                        self.hello_timeout()

                elif self.state == State.DATA_SEND:
                    # Wait for user input from the console
                    try:
                        user_input = input("Enter data to send (or 'q' to quit): ")
                        if user_input.lower() == 'q':
                            print("Received 'q', sending GOODBYE and closing session")
                            self.state = State.GOODBYE_SEND
                        else:
                            self.send_message(1, user_input.encode())  # Send DATA message with user input
                            self.state = State.ALIVE_WAIT

                            # Wait for ALIVE response
                            while self.state == State.ALIVE_WAIT:
                                data = self.receive_message()
                                if data:
                                    self.handle_server_response(data)
                                else:
                                    self.alive_timeout()

                    except EOFError:
                        print("EOF detected on stdin, sending GOODBYE and closing session")
                        self.state = State.GOODBYE_SEND

                elif self.state == State.ALIVE_WAIT:
                    data = self.receive_message()
                    if data:
                        self.handle_server_response(data)
                    else:
                        self.alive_timeout()

                elif self.state == State.GOODBYE_SEND:
                    print("Sending GOODBYE to end session")
                    self.send_message(3)  # Send GOODBYE
                    self.state = State.CLOSED

        print("Client session closed.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    client = UAPClient(server_ip, server_port)
    client.start()
