# services/config.py
from dataclasses import dataclass
from typing import Optional
import json
import os

@dataclass
class AppConfig:
    udp_port: int = 9001
    broadcast_ip: str = "192.168.1.8"
    audio_port: int = 5060
    video_port: int = 5056
    
    @classmethod
    def load(cls, config_file: str = "config.json") -> "AppConfig":
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
                return cls(**data)
        else:
            # Create default config
            config = cls()
            config.save(config_file)
            return config
    
    def save(self, config_file: str = "config.json"):
        with open(config_file, 'w') as f:
            json.dump(self.__dict__, f, indent=2)
