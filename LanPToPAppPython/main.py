# main.py - Complete working version with WebRTC signaling
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
message_fragments: Dict[str, Dict] = {}

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

async def broadcast_to_websockets(message: Dict):
    if not active_connections:
        return
        
    disconnected = []
    for conn_id, websocket in active_connections.items():
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"[WS] Failed to send to {conn_id}: {e}")
            disconnected.append(conn_id)
    
    for conn_id in disconnected:
        del active_connections[conn_id]

def thread_safe_broadcast(message_dict: Dict):
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
                    data, addr = sock.recvfrom(4096)  # Increased buffer for WebRTC messages
                    raw_message = data.decode('utf-8')
                    
                    if addr[0] == get_local_ip():
                        continue
                    
                    try:
                        parsed = json.loads(raw_message)
                        
                        if parsed.get("type") == "webrtc_signal":
                            signal = parsed.get("signal", {})
                            signal_type = signal.get("type", "unknown")
                            from_node = parsed.get("from_node", "unknown")
                            
                            print(f"[UDP] WebRTC signal received: {signal_type} from Node {from_node}")
                            
                            # CRITICAL: Forward to WebSocket clients immediately
                            thread_safe_broadcast({
                                "type": "webrtc_signal",
                                "signal": signal,
                                "from_node": from_node,
                                "sender_ip": addr[0],
                                "timestamp": datetime.now().isoformat()
                            })
                            
                        elif parsed.get("type") == "call_request":
                            call_type = parsed.get("call_type", "audio")
                            caller = parsed.get("caller", "unknown")
                            from_node = parsed.get("from_node", "unknown")
                            
                            print(f"[UDP] Call request: {call_type} from {caller} (Node {from_node})")
                            
                            thread_safe_broadcast({
                                "type": "call_request",
                                "call_type": call_type,
                                "caller": caller,
                                "from_node": from_node,
                                "caller_ip": addr[0],
                                "timestamp": datetime.now().isoformat()
                            })
                            
                        else:
                            # Regular message
                            thread_safe_broadcast({
                                "type": "udp_message",
                                "message": raw_message,
                                "sender": f"Network@{addr[0]}",
                                "timestamp": datetime.now().isoformat()
                            })
                            
                    except json.JSONDecodeError:
                        # Legacy format handling
                        if raw_message.startswith("CALL_REQUEST:"):
                            parts = raw_message.split(":")
                            if len(parts) >= 3:
                                caller_node = parts[1]
                                call_type = parts[2]
                                thread_safe_broadcast({
                                    "type": "call_request",
                                    "call_type": call_type,
                                    "caller": caller_node,
                                    "caller_ip": addr[0],
                                    "timestamp": datetime.now().isoformat()
                                })
                        else:
                            thread_safe_broadcast({
                                "type": "udp_message",
                                "message": raw_message,
                                "sender": f"Network@{addr[0]}",
                                "timestamp": datetime.now().isoformat()
                            })
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if udp_server_running:
                        print(f"[UDP] Listener error: {e}")
                        
        except Exception as e:
            print(f"[UDP] Failed to start listener: {e}")
        finally:
            sock.close()
    
    thread = threading.Thread(target=udp_listener, daemon=True)
    thread.start()
    
def broadcast_udp_message(message: str):
    try:
        udp_ports = [9001, 9002, 9003, 9004, 9005]
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(2.0)
            
            sent_count = 0
            for port in udp_ports:
                if port != UDP_PORT:
                    try:
                        sock.sendto(message.encode('utf-8'), ("127.0.0.1", port))
                        sent_count += 1
                    except Exception:
                        pass
                        
        print(f"[UDP] Broadcast sent to {sent_count} targets")
        return True
    except Exception as e:
        print(f"[UDP] Broadcast failed: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()
    
    print(f"[METAL-52] Node {NODE_ID} starting on {get_local_ip()}:{WEB_PORT}")
    start_udp_listener()
    yield
    
    global udp_server_running
    udp_server_running = False

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
        "message": f"Connected to Metal-52 Node {NODE_ID}",
        "timestamp": datetime.now().isoformat()
    }))
    
    try:
        while True:
            message = await websocket.receive_text()
            
            try:
                data = json.loads(message)
                
                if data.get("type") == "webrtc_signal":
                    # CRITICAL: Enhanced WebRTC signaling
                    signal_type = data["signal"].get("type", "unknown")
                    print(f"[WS] WebRTC Signal: {signal_type} from Node {NODE_ID}")
                    
                    # Broadcast to UDP with enhanced format
                    webrtc_message = {
                        "type": "webrtc_signal",
                        "signal": data["signal"],
                        "from_node": NODE_ID,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    success = broadcast_udp_message(json.dumps(webrtc_message))
                    print(f"[WS] WebRTC signal broadcast success: {success}")
                    
                    # Also broadcast locally for debugging
                    await broadcast_to_websockets({
                        "type": "webrtc_signal_sent",
                        "signal_type": signal_type,
                        "success": success,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                elif data.get("type") == "call_request":
                    # Enhanced call request handling
                    call_type = data.get("call_type", "audio")
                    caller = data.get("caller", f"node-{NODE_ID}")
                    
                    call_message = {
                        "type": "call_request",
                        "call_type": call_type,
                        "caller": caller,
                        "from_node": NODE_ID,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    success = broadcast_udp_message(json.dumps(call_message))
                    print(f"[WS] Call request broadcast: {call_type}, success: {success}")
                    
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
        print(f"[WS] Client {connection_id} disconnected")
        
@app.get("/api/status")
def get_status():
    return {
        "node_id": NODE_ID,
        "active_connections": len(active_connections),
        "udp_server_running": udp_server_running,
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
