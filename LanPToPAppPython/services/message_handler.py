# services/message_handler.py
import asyncio
import socket
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

class MessageHandler:
    def __init__(self, port: int):
        self.port = port
        self.connections: Set[WebSocket] = set()
        self.socket = None
        self.running = False
    
    async def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("0.0.0.0", self.port))
        self.running = True
        
        asyncio.create_task(self._listen_udp())
    
    async def _listen_udp(self):
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                data, addr = await loop.sock_recvfrom(self.socket, 1024)
                message = f"{addr[0]}: {data.decode()}"
                await self._broadcast(message)
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    print(f"UDP error: {e}")
    
    async def handle_websocket(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        try:
            while True:
                message = await websocket.receive_text()
                await self._send_udp(message)
        except WebSocketDisconnect:
            self.connections.remove(websocket)
    
    async def _broadcast(self, message: str):
        for ws in self.connections.copy():
            try:
                await ws.send_text(message)
            except:
                self.connections.discard(ws)
    
    async def _send_udp(self, message: str):
        # Broadcast to local network
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(message.encode(), ("255.255.255.255", self.port))
    
    async def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
