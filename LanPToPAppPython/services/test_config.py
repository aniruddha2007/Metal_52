# services/test_config.py
class TestNode:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.web_port = 8000 + node_id
        self.udp_port = 9001 + node_id
        self.audio_port = 5060 + node_id
        self.video_port = 5056 + node_id
        self.ip = "127.0.0.1"
    
    def get_peer_config(self, peer_id: int):
        """Get configuration to connect to another test node"""
        return {
            "ip": "127.0.0.1",
            "udp_port": 9001 + peer_id,
            "audio_port": 5060 + peer_id,
            "video_port": 5056 + peer_id
        }

# Create multiple test configurations
TEST_NODES = {
    1: TestNode(1),  # Web: 8001, UDP: 9002, Audio: 5061, Video: 5057
    2: TestNode(2),  # Web: 8002, UDP: 9003, Audio: 5062, Video: 5058
    3: TestNode(3),  # Web: 8003, UDP: 9004, Audio: 5063, Video: 5059
}
