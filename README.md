
# 🧠 UDP Client-Server Communication Models (CN Lab)

This project showcases two implementations of a **UDP-based Client-Server model** in Python. Developed as part of our *Computer Networks Lab* at IIT Palakkad, it explores:

- **Thread-based architecture**: Concurrent handling of clients using `threading`
- **Asyncio-based architecture**: Event-driven concurrency using `asyncio` without manual threading

---

## 📁 Project Structure

```
Networks-Client-Server-Model/
├── thread-based/          # Uses socket + threading
│   ├── server.py          # Threaded UDP server with session management
│   └── client.py          # Simple command-driven client
│
├── no-thread-based/       # Uses asyncio for concurrency
│   ├── server.py          # Async UDP server with protocol state handling
│   └── client.py          # Interactive and file-based client with ALIVE/GOODBYE flow
```

---

## How to Run

### Thread-Based Version

```bash
cd thread-based

# Terminal 1
python3 server.py <port_number>

# Terminal 2
python3 client.py <server_ip> <port_number>
```

### No-Thread (Asyncio) Version

```bash
cd no-thread-based

# Terminal 1
python3 server.py <port_number>

# Terminal 2
python3 client.py <server_ip> <port_number>
```

---

## Features Implemented

✅ Custom binary protocol with headers  
✅ HELLO, DATA, ALIVE, and GOODBYE message types  
✅ Session ID, logical clock, and sequence number tracking  
✅ Timeout handling for inactive clients  
✅ Duplicate and out-of-order packet detection  
✅ Clean shutdown using GOODBYE messages  

---

## Contributors

- [Arnav Kadu](https://github.com/AlphaPruned)
- [Pranav Rao](https://github.com/PranavRao25)


<!-- 
This is Computer Networks Assignmnt 3 done by
1. Pranav Rao - 112101038
2. Arnav Kadu - 112101022 -->