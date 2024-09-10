import socket
import struct
from uuid import uuid4


class UAPNonThreadedServer:
    RECEIVE, DONE = 0, 1
    FORMAT = '!HBBIIQI'

    def __init__(self, host, port):
        self.state = self.RECEIVE
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.logical_clock = 0
        self.received_state = -1

    def receive_data(self):
        message = self.socket.recv(1024)

        # receive message
        header = struct.unpack(self.FORMAT, message)

        # get type of request
        self.received_state = header[2]

        # collect data
        data_length = message[6]
        self.received_message = message[1]
        # increment logical clock


