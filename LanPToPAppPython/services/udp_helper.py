# services/udp_helper.py
import socket
import threading
import asyncio
import time
from .websocket_manager import broadcast

server_thread = None
is_server_running = False
event_loop = None
UDP_PORT = 9001

def get_broadcast_ip():
    """Dynamically determine broadcast IP for current network"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            # Convert to broadcast (e.g., 192.168.1.100 -> 192.168.1.255)
            ip_parts = local_ip.split('.')
            ip_parts[-1] = '255'
            return '.'.join(ip_parts)
    except Exception:
        return "255.255.255.255"  # Fallback to global broadcast

def start_server():
    global server_thread, is_server_running
    if is_server_running:
        return {"status": "UDP server already running"}
    
    def listen_udp():
        global is_server_running
        sock = None
        retry_count = 0
        
        while is_server_running:
            try:
                if sock is None:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.settimeout(1.0)  # Add timeout to prevent blocking
                    sock.bind(("0.0.0.0", UDP_PORT))
                    print(f"[UDP] Listening on port {UDP_PORT}")
                    retry_count = 0  # Reset retry count on successful bind
                
                try:
                    data, addr = sock.recvfrom(1024)
                    message = f"[UDP] {addr[0]}: {data.decode('utf-8', errors='ignore')}"
                    print(message)
                    
                    if event_loop and event_loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast(message), event_loop)
                        
                except socket.timeout:
                    continue  # Normal timeout, continue listening
                except UnicodeDecodeError:
                    print("[UDP] Received non-UTF8 data, ignoring")
                    continue
                    
            except OSError as e:
                if sock:
                    sock.close()
                    sock = None
                
                retry_count += 1
                if retry_count <= 5:
                    print(f"[UDP] Bind error (attempt {retry_count}/5): {e}")
                    time.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    print(f"[UDP] Failed to bind after 5 attempts, stopping server")
                    is_server_running = False
                    break
                    
            except Exception as e:
                print(f"[UDP] Unexpected error: {e}")
                time.sleep(1)  # Brief pause before retry
        
        if sock:
            sock.close()
        print("[UDP] Server stopped")
    
    is_server_running = True
    server_thread = threading.Thread(target=listen_udp, daemon=True)
    server_thread.start()
    return {"status": "UDP listener started"}

def send_data(message: str, port=UDP_PORT):
    """Send UDP broadcast message"""
    try:
        broadcast_ip = get_broadcast_ip()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(2.0)  # Add send timeout
            s.sendto(message.encode('utf-8'), (broadcast_ip, port))
        return {"status": "Message broadcasted", "ip": broadcast_ip}
    except Exception as e:
        print(f"[UDP Send Error] {e}")
        return {"status": "Error", "detail": str(e)}

def stop_server():
    """Gracefully stop UDP server"""
    global is_server_running
    is_server_running = False
    if server_thread:
        server_thread.join(timeout=3.0)
