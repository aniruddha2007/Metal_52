# services/websocket_manager.py

from fastapi import WebSocket, WebSocketDisconnect

connected_websockets = set()

async def broadcast(message: str):
    for ws in connected_websockets.copy():
        try:
            await ws.send_text(message)
        except:
            connected_websockets.discard(ws)

async def register(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.add(websocket)

def unregister(websocket: WebSocket):
    connected_websockets.discard(websocket)