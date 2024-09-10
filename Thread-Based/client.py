import _socket
import threading
from uuid import uuid4
import struct


class UAPThreadedClient:
    _HELLO_WAIT, _READY, _READY_WAIT, _CLOSING, _CLOSED = 0, 1, 2, 3, 4
    _FORMAT = '!HBBIIQI'

    def __init__(self, serverAddress: tuple, default_timer = 100):
        self._is_alive = True  # client is now working
        self._DEFAULT_TIMER = default_timer  # default timeout
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)  # UDP
        self._socket.connect(serverAddress)
        self._timer = 0
        self._sequence_num = 0
        self._magic_num = hex(50273)  # for header
        self._version = 1  # for header
        self._session_id = uuid4()
        self._logical_clock = 0
        self._state = self._HELLO_WAIT
        self._received_state = -1
        self._message = ""

    def _header_prep(self, command: int, data_length=0):
        return struct.pack(self._FORMAT, self._magic_num, self._version, command, self._sequence_num, self._session_id, self._logical_clock, data_length)

    def _send_hello(self):
        # send hello _message
        header = self._header_prep(0)
        self._socket.send(header)

        # set _timer
        self._logical_clock += 1

    def _send_goodbye(self):
        # send goodbye
        header = self._header_prep(3)
        self._socket.send(header)

        self._logical_clock += 1

    def _close(self): # to change
        self._is_alive = False
        self._logical_clock += 1
        self._socket.close()

    def _send_data(self, data: str):
        # send data
        _message = data.encode('ascii')
        header = self._header_prep(1, len(_message))
        self._socket.send(header+_message)

        # increment sequence
        self._sequence_num += 1

        # set _timer
        self._logical_clock += 1

    def _receive_data(self):
        _message = struct.unpack(self._FORMAT, self._socket.recv(1024))
        self._received_state = _message[2]  # extract command
        if self._received_state not in range(0,4):
            raise Exception('Protocol Error: Command Invalid')
        self._logical_clock += 1

    def _wait(self):
        while self._timer>=0:
            if self._timer == -1:  # _timer has been cancelled
                break
            self._timer-=1

    def _client_message(self):
        self._message = input()

    def connect(self):
        _receiving_thread = threading.Thread(target = self._receive_data)
        _receiving_thread.start()

        _input_thread = threading.Thread(target = self._client_message)
        _input_thread.start()

        while True:
            if self._state == self._HELLO_WAIT: # HELLO WAIT
                self._send_hello()
                self._timer = self._DEFAULT_TIMER
                self._wait()

                if self._received_state == 0: # got hello _message
                    self._timer = -1 # cancel _timer
                    self._state = self._READY # move to ready
                if self._timer == 0:  # timeout
                    self._send_goodbye()
                    self._state = self._CLOSING # move to closing
            elif self._state == self._READY: # _READY
                if self._message!='q' or self._message!='':  # q or EOF
                    self._send_data(self._message)
                    self._timer = self._DEFAULT_TIMER
                    self._state = self._READY_WAIT # move to ready _timer
                else:
                    self._send_goodbye()
                    self._state = self._CLOSING # move to closing
                if self._received_state == 2: # got alive _message
                    pass
            elif self._state == self._READY_WAIT: # _READY TIMER
                if self._message!='q' or self._message!='':
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
                if self._received_state == 2: # got alive _message
                    pass
                else:
                    self._state = self._CLOSED
                if self._timer == 0: # timeout
                    self._state = self._CLOSED
            elif self._state == self._CLOSED:
                self._close()
                break
            else:
                break
        _receiving_thread.join()


if __name__ == '__main__':
    client = UAPThreadedClient(("", 12345))
    client.connect()
