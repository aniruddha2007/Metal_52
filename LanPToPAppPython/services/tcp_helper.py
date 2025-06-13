# services/tcp_helper.py

import socket
import threading
import asyncio

from .websocket_manager import broadcast

server_thread = None
is_server_running = False
event_loop = None  # Will be set in main.py during startup


def start_server():
    global server_thread, is_server_running

    if is_server_running:
        return {"status": "TCP server already running"}

    def handle_client(conn, addr):
        print(f"[TCP] Connection from {addr}")
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                message = f"[TCP] {addr[0]}: {data.decode()}"
                print(message)

                # Broadcast to WebSocket clients using thread-safe method
                if event_loop and event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(broadcast(message), event_loop)

                conn.sendall(b"ACK")  # Optional: echo or ACK
        finally:
            conn.close()

    def server_loop():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 9000))
            s.listen()
            print("[TCP] Server started on port 9000")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    server_thread = threading.Thread(target=server_loop, daemon=True)
    server_thread.start()
    is_server_running = True

    return {"status": "TCP server started"}


def send_data(data: str, host="192.168.1.14", port=9000):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(data.encode())
            response = s.recv(1024)
            return {"status": "Data sent", "response": response.decode()}
    except Exception as e:
        return {"status": "Error", "detail": str(e)}