import sockets
import threading
from uuid import uuid4
import struct

DEFAULT_TIMER = 100
FORMAT = '!HBBIIQI'
EOF = ''

class UAPThreadedClient:
	HELLO_WAIT, READY, READY_WAIT, CLOSING, CLOSED = 0, 1, 2, 3, 4

	def UAPThreadedClient(self, serverAddress):
		self.is_alive = True
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.connect(serverAddress)
		self.timer = 0
		self.sequence_num = 0
		self.magic_num = hex(50273)
		self.version = 1
		self.session_id = uuid4()
		self.logical_clock = 0
		self.state = 0
		self.received_state

	def header_prep(self, command, data_length):
		return struct.pack(FORMAT, self.magic_num, self.version, command, self.sequence_num, self.session_id, self.logical_clock, data_length)

	def send_hello(self):
		# send hello message
		header = self.header_prep(0, 0)
		self.socket.send(header)

		# set timer
		self.logical_clock += 1

	def send_goodbye(self):
		# send goodbye
		header = self.header_prep(3, 0)
		self.socket.send(header)

		self.logical_clock += 1
	
	def close(self): # to change
		self.is_alive = False
		self.logical_clock += 1
		self.socket.close()

	def send_data(self, data):
		# send data
		message = data.encode('ascii')
		header = self.header_prep(1, len(message))
		self.socket.send(header+message)

		# increment sequence
		self.sequence_num += 1

		# set timer
		self.logical_clock += 1

	def receive_data(self):
		message = struct.unpack(FORMAT, self.socket.recv(1024))
		self.received_state = message[2]
		if self.received_state not in range(0,4):
			raise Exception('Protocol Error: Command Invalid')
		
	def wait(self):
		while(self.timer>=0):
			if self.timer == -1:
				break
			self.timer-=1

	def connect(self):
		receivingThread = threading.Thread(target = self.receive_data)
		receivingThread.start()
		
		inputThread = threading.Thread(target = input())
		inputThread.start()

		while(True):
			if self.state == HELLO_WAIT: # HELLO WAIT
				self.send_hello()
				self.timer = DEFAULT_TIMER
				self.wait()

				if self.received_state == 0: # got hello message
					self.timer = -1 # cancel timer
					self.state = READY # move to ready
				if self.timer == 0:
					self.send_goodbye()
					self.state = CLOSING # move to closing
			elif self.state == READY: # READY
				if self.message!='q' or self.message!='':
					self.send_data(self.message)
					self.timer = DEFAULT_TIMER
					self.state = READY_WAIT # move to ready timer
				else:
					self.send_goodbye()
					self.state = CLOSING # move to closing
				if self.received_state == 2: # got alive message
					pass
			elif self.state == READY_WAIT: # READY TIMER
				if self.message!='q' or self.message!='':
					self.send_data(self.message)
					self.wait()
				else:
					self.send_goodbye()
					self.state = CLOSING # move to closing
				if self.received_state == 2: # got alive message
					self.timer = -1 # cancel timer
					self.state = READY # move to ready
				if self.timer == 0: # timeout
					self.send_goodbye()
					self.state = CLOSING # move to closing
			elif state == CLOSING:
				if self.received_state == 2: # got alive message
					pass
				else:
					self.state = CLOSED
				if self.timer == 0: # timeout
					self.state = CLOSED
			elif state == CLOSED:
				self.close()
				break
			else:
				break
		receivingThread.join()
