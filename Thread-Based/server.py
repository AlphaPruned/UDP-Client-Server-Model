#!/usr/bin/env python3

import socket
import threading
import struct
import sys

class UDPServerThread:

    def __init__(self, port):
        self.sessionStorage = {}
        self.magicNumber = 0xc461
        self.versionNumber = 1
        self.portNumber = port
        self.inactivityTimeout = 150

    def startServer(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSocket.bind(('localhost', self.portNumber))
        print(f"Waiting on port {self.portNumber}...")

        try:
            while True:
                data, clientAddress = self.serverSocket.recvfrom(1024)
                clientHandler = threading.Thread(target=self.handleClientPackets, args=(data, clientAddress))
                clientHandler.start()
        except KeyboardInterrupt:
            print("Server interrupted by user. Shutting down...")
        finally:
            self.serverSocket.close()
            print("Server socket closed.")

    def handleClientPackets(self, data, clientAddress):
        try:
            magic, version, command, sequenceNumber, sessionID, logicalClock, payloadLength = struct.unpack('!HBBIIQI', data[:24])
        except struct.error:
            print(f"Invalid packet format received from {clientAddress}, Ignored")
            return

        if magic != self.magicNumber or version != self.versionNumber:
            print(f"Magic number & version issue: Invalid packet received from {clientAddress}, Ignored")
            return
        
        session = self.sessionStorage.get(sessionID)

        if command == 0:  # HELLO
            if session and session['seq_num'] > 0:
                print(f"Protocol Error: HELLO received during Receive State for Session ID: {sessionID}, Closing session.")
                self.SendGoodbye(sessionID, clientAddress)
                self.CloseSession(sessionID)
                return 

            session = self.CreateSession(sessionID, clientAddress)
            self.SendHello(sessionID, clientAddress)
            return
        
        if not session:
            print(f"No active Session {sessionID}, Ignored")
            return
        
        if command == 1:  # DATA
            payload = data[24:]
            self.handleClientData(sessionID, sequenceNumber, logicalClock, payload, clientAddress)
        
        elif command == 3:  # GOODBYE
            print(f"0x{sessionID:08x} [{sequenceNumber}] GOODBYE from client.")
            self.SendGoodbye(sessionID, clientAddress)
            self.CloseSession(sessionID)
            return

    def handleClientData(self, sessionID, sequenceNumber, logicalClock, payload, clientAddress):
        session = self.sessionStorage.get(sessionID)
        if not session:
            return
        
        expectedSequenceNumber = session['seq_num'] + 1

        if sequenceNumber > expectedSequenceNumber:
            print("Lost Packet!")
        elif sequenceNumber == expectedSequenceNumber:
            print(f"0x{sessionID:08x} [{sequenceNumber}] {payload.decode()}")
            session['seq_num'] = sequenceNumber
        elif sequenceNumber == (expectedSequenceNumber - 1):
            print("Duplicate Packet!!")
            pass
        else:
            print(f"Protocol Error: Out-of-order packet received for Session ID: 0x{sessionID:08x}. Closing session.")
            self.SendGoodbye(sessionID, clientAddress)
            self.CloseSession(sessionID)
        
        session['logicalClock'] = max(session['logicalClock'], logicalClock) + 1
        self.ResetTimer(sessionID)
        self.SendAlive(sessionID, clientAddress)

    def CreateSession(self, sessionID, clientAddress):
        session = {'seq_num': 0, 'address': clientAddress, 'logicalClock': 0}
        self.sessionStorage[sessionID] = session
        print(f"0x{sessionID:08x} [0] Session created")
        self.ResetTimer(sessionID)
        return session
    
    def ResetTimer(self, sessionID):
        session = self.sessionStorage.get(sessionID)
        if session and 'timer' in session:
            session['timer'].cancel()

        session['timer'] = threading.Timer(self.inactivityTimeout, self.InactiveSessionCleanup, [sessionID])
        session['timer'].start()

    def InactiveSessionCleanup(self, sessionID):
        session = self.sessionStorage.get(sessionID, None)
        if session:
            clientAddress = session['address']
            print(f"Session {sessionID} timed out due to inactivity. Sending GOODBYE.")
            self.SendGoodbye(sessionID, clientAddress)
            self.CloseSession(sessionID)
            
    def CloseSession(self, sessionID):
        if sessionID in self.sessionStorage:
            print(f"0x{sessionID:08x} Session closed")
            del self.sessionStorage[sessionID]

    def SendHello(self, sessionID, clientAddress):
        session = self.sessionStorage.get(sessionID)
        if session:
            session['logicalClock'] += 1
            helloMessage = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, 0, session['seq_num'], sessionID, session['logicalClock'], 0)
            self.serverSocket.sendto(helloMessage, clientAddress)

    def SendGoodbye(self, sessionID, clientAddress):
        session = self.sessionStorage.get(sessionID)
        if session:
            session['logicalClock'] += 1
            goodbyeMessage = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, 3, session['seq_num'], sessionID, session['logicalClock'], 0)
            self.serverSocket.sendto(goodbyeMessage, clientAddress)

    def SendAlive(self, sessionID, clientAddress):
        session = self.sessionStorage.get(sessionID)
        if session:
            session['logicalClock'] += 1
            aliveMessage = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, 2, session['seq_num'], sessionID, session['logicalClock'], 0)
            self.serverSocket.sendto(aliveMessage, clientAddress)

if __name__ == "__main__":
    portNumber = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    server = UDPServerThread(portNumber)
    server.startServer()
