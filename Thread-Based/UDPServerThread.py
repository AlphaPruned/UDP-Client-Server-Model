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
        # self.commandNumber = 
        # self.sequenceNumber = 
        # self.sessionID = 
        # self.logicalClock = 
        self.portNumber = port
        self.sessionLock = threading.Lock()
        self.inactivityTimeout = 10

    def startServer(self):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSocket.bind(('localhost',self.portNumber))
        print(f"UDP Server listening on Port: {self.portNumber}")

        while True:
            data, clientAddress = self.serverSocket.recvfrom(1024)
            clientHandler = threading.Thread(target=self.handleClientPackets, args=(data, clientAddress))
            clientHandler.start()

    def handleClientPackets(self, data, clientAddress):
        try:
            magic, version, command, sequenceNumber, sessionID, logicalClock, payloadLength = struct.unpack('!HBBIIQI', data[: 24])
        except struct.error:
            print(f"Invalid packet format received from {clientAddress}, Ignored")
            return

        if magic != self.magicNumber or version != self.versionNumber:
            print(f"Magic number & version issue: Invalid packet received from {clientAddress}, Ignored")
            return
        
        with self.sessionLock:
            session = self.sessionStorage.get(sessionID)

            if command == 0:
                if session and session['seq_num'] > 0:
                    print(f"Protocol Error: HELLO received during Receive State for Session ID: {sessionID}, Closing session.")
                    self.SendGoodbye(sessionID, clientAddress)
                    self.CloseSession(sessionID)
                    return 

                session = self.CreateSession(sessionID, clientAddress)
                self.SendHello(session, clientAddress) 
                return
            
            if not session:
                print(f"No active Session {sessionID}, Ignored")
                return
            
            if command == 1:
                payload = data[24: ]

                self.handleClientData(sessionID, sequenceNumber, logicalClock, payload, clientAddress)
            
            if command == 3:
                print(f"GOODBYE received from {clientAddress}, Closing Session {sessionID}")
                self.SendGoodbye(sessionID, clientAddress)
                self.CloseSession(sessionID)
                return
            
    def handleClientData(self, sessionID, sequenceNumber, logicalClock, payload, clientAddress):
        with self.sessionLock:
            session = self.sessionStorage.get(sessionID, None)
        if not session:
            return
        
        xpectedSequenceNumber = session['seq_num'] + 1

        if sequenceNumber > xpectedSequenceNumber:
            print(f"For Session {sessionID}: Lost packet(s).\n Expected {xpectedSequenceNumber}, received {sequenceNumber}")
        elif sequenceNumber == xpectedSequenceNumber:
            print(f"For Session {sessionID}: Sequence Number {sequenceNumber}\n{payload.decode()}")
            session['seq_num'] = sequenceNumber
        elif sequenceNumber == (xpectedSequenceNumber - 1):
            print(f"For Session {sessionID}: Sequence Number {sequenceNumber}, Duplicate packet.")
        else:
            print(f"Protocol Error: For Session {sessionID}: Out-of-order packet, Ignored.")
            return
        
        session['logicalClock'] = max(session['logicalClock'], logicalClock) + 1
        self.ResetTimer(sessionID)
        
        self.SendAlive(sessionID, clientAddress)

    def CreateSession(self, sessionID, clientAddress):
        session = {'seq_num': 0, 'address': clientAddress, 'logicalClock': 0}

        with self.sessionLock:
            self.sessionStorage[sessionID] = session
            print(f"Session ID: {sessionID} created in response to incoming HELLO")
        
        self.ResetTimer(sessionID)
        
        return session
    
    def ResetTimer(self, sessionID):
        session = self.sessionStorage.get(sessionID)
        if session and 'timer' in session:
            session['timer'].cancel()

        session['timer'] = threading.Timer(self.inactivityTimeout, self.InactiveSessionCleanup, [sessionID])
        session['timer'].start()

    def InactiveSessionCleanup(self, sessionID):
        with self.sessionLock:
            session = self.sessionStorage.get(sessionID, None)
            if session:
                clientAddress = session['address']
                print(f"Session {sessionID} timed out due to inactivity. Sending GOODBYE.")
                self.SendGoodbye(sessionID, clientAddress)
                self.CloseSession(sessionID)
            
    def CloseSession(self, sessionID):
        with self.sessionLock:
            if sessionID in self.sessionStorage:
                print(f"Removing Session {sessionID}:\n{self.sessionStorage[sessionID]}")
                del self.sessionStorage[sessionID]
                print(f"Session {sessionID} closed and removed from storage.")

    def SendHello(self, sessionID, clientAddress):
        with self.sessionLock:
            session = self.sessionStorage.get(sessionID)
            if session:
                session['logicalClock'] += 1
                helloMessage = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, 0, session['seq_num'], sessionID, session['logicalClock'], 0)
                self.serverSocket.sendto(helloMessage, clientAddress)
                print(f"HELLO message sent to client {clientAddress}.")

    def SendGoodbye(self, sessionID, clientAddress):
        with self.sessionLock:
            session = self.sessionStorage.get(sessionID)
            if session:
                session['logicalClock'] += 1
                goodbyeMessage = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, 3, self.sequenceNumber, sessionID, session['logicalClock'], 0)
                self.serverSocket.sendto(goodbyeMessage, clientAddress)
                print(f"GOODBYE message sent to client {clientAddress}.")
    

    def SendAlive(self, sessionID, clientAddress):
        with self.sessionLock:
            session = self.sessionStorage.get(sessionID)
            if session:
                session['logicalClock'] += 1
                aliveMessage = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, 2, self.sequenceNumber, sessionID, session['logicalClock'], 0)
                self.serverSocket.sendto(aliveMessage, clientAddress)
                print(f"ALIVE message sent to client {clientAddress}.")

    # def SendClientMessage(self, command, sessionID, clientAddress):
    #     with self.sessionLock:
    #         session = self.sessionStorage.get(sessionID)
    #         if session:
    #             message = struct.pack('!HBBIIQI', self.magicNumber, self.versionNumber, command, self.sequenceNumber, sessionID, session['logicalClock'], 0)
    #             self.serverSocket.sendto(message, clientAddress)
    #             if command == 0:
    #                 print(f"HELLO message sent to client {clientAddress}.")
    #             elif command == 2:
    #                 print(f"ALIVE message sent to client {clientAddress}.")
    #             elif command == 3:
    #                 print(f"GOODBYE message sent to client {clientAddress}")

if __name__ == "__main__":
    portNumber = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    server = UDPServerThread(portNumber)
    server.startServer()
