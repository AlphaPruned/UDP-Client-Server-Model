#!/usr/bin/env python3

import socket
import sys
import threading
from random import random
import struct


class UAPThreadedClient:
    _HELLO_WAIT, _READY, _READY_WAIT, _CLOSING, _CLOSED = 0, 1, 2, 3, 4
    _FORMAT = '!HBBIIQI'

    def __init__(self, serverAddress: tuple, default_timer = 10000000):
        self._is_alive = True  # client is now working
        self._DEFAULT_TIMER = default_timer  # default timeout
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self._socket.connect(serverAddress)
        self._timer = 0
        self._sequence_num = 0
        self.server_address = serverAddress
        self._magic_num, self._version, self._session_id = 0xC461, 1, int(random()*100)
        self._logical_clock = 0
        self._state = self._HELLO_WAIT
        self._received_state = -1
        self._message = ""

    def _header_prep(self, command: int, data_length=0):
        return struct.pack(self._FORMAT, self._magic_num, self._version, command, self._sequence_num, self._session_id, self._logical_clock, data_length)

    def _send_hello(self):
        # send hello
        header = self._header_prep(0)
        self._socket.sendto(header, self.server_address)

        # set timer
        self._logical_clock += 1

        print(f"HELLO sent to {self.server_address}")

    def _send_goodbye(self):
        # send goodbye
        header = self._header_prep(3)
        self._socket.sendto(header, self.server_address)

        # update timer
        self._logical_clock += 1

        print(f"GOODBYE sent to {self.server_address}")

    def _close(self): # to change
        self._is_alive = False
        self._logical_clock += 1
        self._socket.close()
        print("Socket closed")

    def _send_data(self, data: str):
        # send data
        _message = data.encode('ascii')
        header = self._header_prep(1, len(_message))
        self._socket.sendto(header + _message, self.server_address)

        # update sequence
        self._sequence_num += 1

        # update timer
        self._logical_clock += 1

        print(f"DATA sent: {data}")

    def _receive_data(self):
        while self._is_alive:
            try:
                data, _ = self._socket.recvfrom(1024)
                print(f"Data received: {data}")

                # get the response from server
                command = struct.unpack(self._FORMAT, data[:24])[2]
                self._received_state = command
            except socket.error as e:
                print(f"Response Error: {e}")
                break

    def _client_message(self):
        while self._is_alive:
            try:
                self._message = input("Enter message: ")
            except EOFError:
                print("\nEOF received, closing connection.")
                self._send_goodbye()
                break
        # receive_data
        # if command == 3:
                #     print("Received GOODBYE from server")
                #     self._close()
                # elif command == 0:
                #     self._session_id = session_id
                #     print(f"Session ID established: {self._session_id}")
                # elif command == 2:
                #     print("Received ALIVE")
                # elif command == 1:
                #     payload = data[24:]
                #     print(f"Received DATA: {payload.decode()}")


        # _message = struct.unpack(self._FORMAT, self._socket.recv(1024))
        # self._received_state = _message[2]  # extract command
        # if self._received_state not in range(0,4):
        #     raise Exception('Protocol Error: Command Invalid')
        # self._logical_clock = max(_message[5], self._logical_clock)+1

    def _wait(self):
        while self._timer>0:
            if self._timer == -1:  # timer has been cancelled
                break
            self._timer-=1

    # def _client_message(self):
    #     self._message = input()

    def connect(self):
        threading.Thread(target=self._receive_data, daemon=True).start()
        threading.Thread(target=self._client_message, daemon=True).start()

        while self._is_alive:
            if self._state == self._HELLO_WAIT: # HELLO WAIT
                print('HELLO WAIT')
                self._send_hello()
                self._timer = self._DEFAULT_TIMER
                self._wait()
                print(f'Timeout {self._timer}')
                if self._received_state == 0: # got hello _message
                    self._timer = -1 # cancel _timer
                    self._state = self._READY # move to ready
                if self._timer == 0:  # timeout
                    print("timer is 0")
                    self._send_goodbye()
                    self._state = self._CLOSING # move to closing
            elif self._state == self._READY: # _READY
                print('READY')
                if self._message!='q':  # not quitting
                    self._send_data(self._message)
                    self._timer = self._DEFAULT_TIMER
                    self._state = self._READY_WAIT # move to ready _timer
                else:
                    self._send_goodbye()
                    self._state = self._CLOSING # move to closing
                if self._received_state == 2: # got alive _message
                    pass
            elif self._state == self._READY_WAIT: # _READY TIMER
                print('READY WAIT')
                if self._message!='q': # not quitting
                    self._send_data(self._message)
                    self._wait()
                else:
                    self._send_goodbye()
                    self._state = self._CLOSING # move to closing
                if self._received_state == 2: # got alive _message
                    self._timer = -1 # cancel _timer
                    self._state = self._READY # move to ready
                if self._timer == 0: # timeout
                    self._send_goodbye()
                    self._state = self._CLOSING # move to closing
            elif self._state == self._CLOSING:
                print('CLOSING')
                if self._received_state == 2: # got alive _message
                    pass
                else:
                    self._state = self._CLOSED
                if self._timer == 0: # timeout
                    self._state = self._CLOSED
            elif self._state == self._CLOSED:
                print('CLOSED')
                self._close()
                break
            else:
                break
        print('closing; bye bye')


if __name__ == '__main__':
    server_address = (sys.argv[1], int(sys.argv[2]))
    client = UAPThreadedClient(server_address)
    client.connect()
