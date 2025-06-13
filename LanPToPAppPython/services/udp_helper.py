# services/udp_helper.py

import socket
import threading
import asyncio
from .websocket_manager import broadcast

server_thread = None
is_server_running = False
event_loop = None

UDP_PORT = 9001
BROADCAST_IP = '192.168.1.14'  # Replace with subnet if needed, e.g., '192.168.1.255'

def start_server():
    global server_thread, is_server_running

    if is_server_running:
        return {"status": "UDP server already running"}

    def listen_udp():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", UDP_PORT))
            print(f"[UDP] Listening on port {UDP_PORT}")
            while True:
                try:
                    data, addr = s.recvfrom(1024)
                    message = f"[UDP] {addr[0]}: {data.decode()}"
                    print(message)
                    if event_loop and event_loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast(message), event_loop)
                except Exception as e:
                    print(f"[UDP Error] {e}")

    server_thread = threading.Thread(target=listen_udp, daemon=True)
    server_thread.start()
    is_server_running = True
    return {"status": "UDP listener started"}

def send_data(message: str, port=UDP_PORT):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(message.encode(), (BROADCAST_IP, port))
        return {"status": "Message broadcasted"}
    except Exception as e:
        return {"status": "Error", "detail": str(e)}