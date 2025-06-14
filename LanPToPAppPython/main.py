# main.py - Fixed with UDP message fragmentation and proper signaling
import os
import json
import asyncio
import socket
import threading
import base64
import hashlib
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from typing import Dict, Set
import uuid
import concurrent.futures

# Configuration
NODE_ID = int(os.getenv('NODE_ID', '0'))
WEB_PORT = int(os.getenv('WEB_PORT', '8000'))
UDP_PORT = int(os.getenv('UDP_PORT', '9001'))
AUDIO_PORT = int(os.getenv('AUDIO_PORT', '5060'))
VIDEO_PORT = int(os.getenv('VIDEO_PORT', '5056'))

# Global state
active_connections: Dict[str, WebSocket] = {}
peer_nodes: Dict[str, Dict] = {}
udp_server_running = False
main_event_loop = None
message_fragments: Dict[str, Dict] = {}  # For large message reconstruction

# Constants
MAX_UDP_SIZE = 900  # Safe UDP packet size
FRAGMENT_TIMEOUT = 30  # seconds

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def fragment_large_message(message: str, msg_id: str = None) -> list:
    """Fragment large messages for UDP transmission"""
    if len(message) <= MAX_UDP_SIZE:
        return [message]
    
    if not msg_id:
        msg_id = hashlib.md5(message.encode()).hexdigest()[:8]
    
    fragments = []
    chunk_size = MAX_UDP_SIZE - 100  # Reserve space for headers
    total_chunks = (len(message) + chunk_size - 1) // chunk_size
    
    for i in range(total_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(message))
        chunk_data = message[start:end]
        
        fragment = {
            "type": "fragment",
            "msg_id": msg_id,
            "chunk": i,
            "total": total_chunks,
            "data": base64.b64encode(chunk_data.encode()).decode()
        }
        fragments.append(json.dumps(fragment))
    
    return fragments

def reconstruct_fragmented_message(fragment_data: dict) -> str:
    """Reconstruct fragmented messages"""
    global message_fragments
    
    msg_id = fragment_data["msg_id"]
    chunk_num = fragment_data["chunk"]
    total_chunks = fragment_data["total"]
    data = base64.b64decode(fragment_data["data"]).decode()
    
    # Initialize message storage
    if msg_id not in message_fragments:
        message_fragments[msg_id] = {
            "chunks": {},
            "total": total_chunks,
            "timestamp": datetime.now().timestamp()
        }
    
    # Store chunk
    message_fragments[msg_id]["chunks"][chunk_num] = data
    
    # Check if complete
    if len(message_fragments[msg_id]["chunks"]) == total_chunks:
        # Reconstruct message
        complete_message = ""
        for i in range(total_chunks):
            complete_message += message_fragments[msg_id]["chunks"][i]
        
        # Clean up
        del message_fragments[msg_id]
        return complete_message
    
    return None  # Still waiting for more fragments

def cleanup_old_fragments():
    """Clean up expired message fragments"""
    global message_fragments
    current_time = datetime.now().timestamp()
    expired_ids = []
    
    for msg_id, msg_data in message_fragments.items():
        if current_time - msg_data["timestamp"] > FRAGMENT_TIMEOUT:
            expired_ids.append(msg_id)
    
    for msg_id in expired_ids:
        del message_fragments[msg_id]

async def broadcast_to_websockets(message: Dict):
    """Broadcast message to all WebSocket connections on this node"""
    if not active_connections:
        return
        
    disconnected = []
    for conn_id, websocket in active_connections.items():
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"[WS] Failed to send to {conn_id}: {e}")
            disconnected.append(conn_id)
    
    # Clean up disconnected clients
    for conn_id in disconnected:
        del active_connections[conn_id]

def thread_safe_broadcast(message_dict: Dict):
    """Thread-safe wrapper to broadcast to WebSockets from UDP thread"""
    global main_event_loop
    if main_event_loop and not main_event_loop.is_closed():
        try:
            future = asyncio.run_coroutine_threadsafe(
                broadcast_to_websockets(message_dict), 
                main_event_loop
            )
            return True
        except Exception as e:
            print(f"[UDP] Thread-safe broadcast failed: {e}")
            return False
    else:
        print("[UDP] Main event loop not available")
        return False

def start_udp_listener():
    global udp_server_running
    udp_server_running = True
    
    def udp_listener():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        
        try:
            sock.bind(("0.0.0.0", UDP_PORT))
            print(f"[UDP] Node {NODE_ID} listening on port {UDP_PORT}")
            
            while udp_server_running:
                try:
                    data, addr = sock.recvfrom(2048)  # Increased buffer size
                    raw_message = data.decode('utf-8')
                    
                    # Skip our own messages
                    if addr[0] == get_local_ip():
                        continue
                    
                    try:
                        # Try to parse as JSON first
                        parsed = json.loads(raw_message)
                        
                        # Handle fragmented messages
                        if parsed.get("type") == "fragment":
                            complete_message = reconstruct_fragmented_message(parsed)
                            if complete_message:
                                # Process the complete message
                                process_complete_message(complete_message, addr[0])
                            # If not complete, just wait for more fragments
                            continue
                        else:
                            # Regular message
                            process_complete_message(raw_message, addr[0])
                            
                    except json.JSONDecodeError:
                        # Handle non-JSON messages (legacy chat)
                        if raw_message.startswith("CALL_REQUEST:"):
                            parts = raw_message.split(":")
                            if len(parts) >= 3:
                                caller_node = parts[1]
                                call_type = parts[2]
                                
                                call_message = {
                                    "type": "call_request",
                                    "call_type": call_type,
                                    "caller": caller_node,
                                    "caller_ip": addr[0],
                                    "timestamp": datetime.now().isoformat()
                                }
                                thread_safe_broadcast(call_message)
                        else:
                            # Regular chat message
                            thread_safe_broadcast({
                                "type": "udp_message",
                                "message": raw_message,
                                "sender": f"Network@{addr[0]}",
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    # Cleanup old fragments periodically
                    cleanup_old_fragments()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if udp_server_running:
                        print(f"[UDP] Listener error: {e}")
                        
        except Exception as e:
            print(f"[UDP] Failed to start listener: {e}")
        finally:
            sock.close()
            print(f"[UDP] Node {NODE_ID} UDP listener stopped")
    
    thread = threading.Thread(target=udp_listener, daemon=True)
    thread.start()

def process_complete_message(message: str, sender_ip: str):
    """Process a complete message (either direct or reconstructed)"""
    if message.startswith("WEBRTC_SIGNAL:"):
        try:
            signal_data = message[14:]  # Remove "WEBRTC_SIGNAL:" prefix
            signal_json = json.loads(signal_data)
            print(f"[UDP] Processing WebRTC signal from {sender_ip}: {signal_json.get('type', 'unknown')}")
            
            thread_safe_broadcast({
                "type": "webrtc_signal", 
                "signal": signal_json,
                "sender_ip": sender_ip,
                "timestamp": datetime.now().isoformat()
            })
        except json.JSONDecodeError as e:
            print(f"[UDP] Failed to parse WebRTC signal: {e}")
    elif message.startswith("CALL_REQUEST:"):
        # Handle call requests
        parts = message.split(":")
        if len(parts) >= 3:
            caller_node = parts[1]
            call_type = parts[2]
            
            call_message = {
                "type": "call_request",
                "call_type": call_type,
                "caller": caller_node,
                "caller_ip": sender_ip,
                "timestamp": datetime.now().isoformat()
            }
            thread_safe_broadcast(call_message)
    else:
        # Regular chat message
        thread_safe_broadcast({
            "type": "udp_message",
            "message": message,
            "sender": f"Network@{sender_ip}",
            "timestamp": datetime.now().isoformat()
        })

def broadcast_udp_message(message: str):
    try:
        udp_ports = [9001, 9002, 9003, 9004, 9005]
        fragments = fragment_large_message(message)
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2.0)
            
            sent_count = 0
            for port in udp_ports:
                if port != UDP_PORT:
                    try:
                        # Send all fragments
                        for fragment in fragments:
                            sock.sendto(fragment.encode('utf-8'), ("127.0.0.1", port))
                            sock.sendto(fragment.encode('utf-8'), (get_local_ip(), port))
                        sent_count += 1
                    except Exception:
                        pass
                        
        print(f"[UDP] Broadcast sent {len(fragments)} fragments to {sent_count} targets")
        return True
    except Exception as e:
        print(f"[UDP] Broadcast failed: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()
    
    print(f"[METAL-52] Node {NODE_ID} starting on {get_local_ip()}:{WEB_PORT}")
    print(f"[METAL-52] Ports: Web={WEB_PORT}, UDP={UDP_PORT}, Audio={AUDIO_PORT}, Video={VIDEO_PORT}")
    
    start_udp_listener()
    yield
    
    global udp_server_running
    udp_server_running = False
    print(f"[METAL-52] Node {NODE_ID} shutting down")

app = FastAPI(
    title=f"Metal-52 Node {NODE_ID}",
    description="Secure P2P Communication Platform",
    version="2.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
def get_root(request: Request):
    peer_nodes_list = []
    if NODE_ID > 0:
        for i in range(1, 4):
            if i != NODE_ID:
                peer_nodes_list.append({
                    "id": i,
                    "web_port": 8000 + i,
                    "audio_port": 5060 + i,
                    "video_port": 5056 + i,
                    "ip": "127.0.0.1"
                })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "node_id": NODE_ID,
        "local_ip": get_local_ip(),
        "peer_nodes": peer_nodes_list,
        "ports": {
            "web": WEB_PORT,
            "udp": UDP_PORT,
            "audio": AUDIO_PORT,
            "video": VIDEO_PORT
        }
    })

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    active_connections[connection_id] = websocket
    
    print(f"[WS] Client {connection_id} connected (Total: {len(active_connections)})")
    
    await websocket.send_text(json.dumps({
        "type": "system",
        "message": f"Connected to Metal-52 Node {NODE_ID} ({get_local_ip()}:{WEB_PORT})",
        "sender": "System",
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        while True:
            message = await websocket.receive_text()
            
            try:
                # Try to parse as JSON for WebRTC signaling
                data = json.loads(message)
                
                if data.get("type") == "webrtc_signal":
                    # Handle WebRTC signaling with fragmentation support
                    signal_json = json.dumps(data["signal"])
                    webrtc_message = f"WEBRTC_SIGNAL:{signal_json}"
                    success = broadcast_udp_message(webrtc_message)
                    
                    print(f"[WS] WebRTC signal broadcast: {data['signal'].get('type', 'unknown')}, success: {success}")
                    
                elif data.get("type") == "call_request":
                    # Handle outgoing call requests
                    call_type = data.get("call_type", "audio")
                    caller = data.get("caller", f"node-{NODE_ID}")
                    
                    call_message = f"CALL_REQUEST:{caller}:{call_type}"
                    success = broadcast_udp_message(call_message)
                    
                    print(f"[WS] Broadcasting call request: {call_message}, success: {success}")
                    
                else:
                    # Regular chat message
                    chat_message = f"Node-{NODE_ID}: {data.get('message', message)}"
                    broadcast_udp_message(chat_message)
                    
                    await broadcast_to_websockets({
                        "type": "chat",
                        "message": data.get("message", message),
                        "sender": f"Node-{NODE_ID} (You)",
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except json.JSONDecodeError:
                # Plain text message
                chat_message = f"Node-{NODE_ID}: {message}"
                broadcast_udp_message(chat_message)
                
                await broadcast_to_websockets({
                    "type": "chat",
                    "message": message,
                    "sender": f"Node-{NODE_ID} (You)",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        del active_connections[connection_id]
        print(f"[WS] Client {connection_id} disconnected (Remaining: {len(active_connections)})")

@app.get("/api/status")
def get_status():
    return {
        "node_id": NODE_ID,
        "ip": get_local_ip(),
        "port": WEB_PORT,
        "active_connections": len(active_connections),
        "peer_nodes": len(peer_nodes),
        "udp_server_running": udp_server_running,
        "message_fragments": len(message_fragments),
        "ports": {
            "web": WEB_PORT,
            "udp": UDP_PORT,
            "audio": AUDIO_PORT,
            "video": VIDEO_PORT
        }
    }

@app.post("/api/peer/add")
def add_peer(peer_ip: str = Form(...), peer_port: int = Form(8000)):
    peer_id = f"{peer_ip}:{peer_port}"
    peer_nodes[peer_id] = {
        "id": peer_id,
        "ip": peer_ip,
        "port": peer_port,
        "status": "connecting",
        "last_seen": datetime.now().isoformat()
    }
    return {"status": "peer_added", "peer": peer_nodes[peer_id]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=WEB_PORT, reload=True)
