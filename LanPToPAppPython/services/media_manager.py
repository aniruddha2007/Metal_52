# services/media_manager.py
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any
import cv2
import sounddevice as sd
import socket
import threading
import numpy as np

@dataclass
class MediaConfig:
    audio_rate: int = 16000  # Increased from 8kHz for better quality
    video_width: int = 640   # Increased resolution
    video_height: int = 480
    audio_port: int = 5060
    video_port: int = 5056
    quality: int = 70        # JPEG quality

class MediaManager:
    def __init__(self, config: MediaConfig):
        self.config = config
        self.audio_stream = None
        self.video_capture = None
        self.sockets: Dict[str, socket.socket] = {}
        self.active_sessions: Dict[str, bool] = {
            'audio_send': False,
            'audio_recv': False,
            'video_send': False,
            'video_recv': False
        }
        
    async def start_audio_call(self, remote_ip: str) -> Dict[str, Any]:
        if self.active_sessions['audio_send']:
            return {"error": "Audio already active"}
            
        try:
            self._start_audio_sender(remote_ip)
            self.active_sessions['audio_send'] = True
            return {"status": "success", "message": f"Audio started to {remote_ip}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _start_audio_sender(self, remote_ip: str):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockets['audio_send'] = sock
        
        def audio_callback(indata, frames, time, status):
            if self.active_sessions['audio_send']:
                try:
                    sock.sendto(indata.tobytes(), (remote_ip, self.config.audio_port))
                except Exception as e:
                    print(f"Audio send error: {e}")
        
        self.audio_stream = sd.InputStream(
            samplerate=self.config.audio_rate,
            channels=1,
            dtype='int16',
            callback=audio_callback,
            blocksize=1024
        )
        self.audio_stream.start()
    
    async def stop_all_media(self):
        # Clean shutdown of all media streams
        for session in self.active_sessions:
            self.active_sessions[session] = False
            
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            
        if self.video_capture:
            self.video_capture.release()
            
        for sock in self.sockets.values():
            sock.close()
        self.sockets.clear()
