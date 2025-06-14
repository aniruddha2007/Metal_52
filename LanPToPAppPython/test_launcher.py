# test_launcher.py
import subprocess
import sys
import time
import os

def start_test_node(node_id: int):
    """Start a test node with specific ports"""
    env = os.environ.copy()
    env.update({
        'NODE_ID': str(node_id),
        'WEB_PORT': str(8000 + node_id),
        'UDP_PORT': str(9001 + node_id),
        'AUDIO_PORT': str(5060 + node_id),
        'VIDEO_PORT': str(5056 + node_id)
    })
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--host", "127.0.0.1", 
        "--port", str(8000 + node_id),
        "--reload"
    ]
    
    print(f"Starting Node {node_id} on ports: Web={8000+node_id}, UDP={9001+node_id}, Audio={5060+node_id}, Video={5056+node_id}")
    return subprocess.Popen(cmd, env=env)

def main():
    processes = []
    try:
        for node_id in [1, 2, 3]:
            proc = start_test_node(node_id)
            processes.append(proc)
            time.sleep(2)  # Stagger startup
        
        print("\n=== Test Nodes Started ===")
        print("Node 1: http://localhost:8001")
        print("Node 2: http://localhost:8002") 
        print("Node 3: http://localhost:8003")
        print("\nPress Ctrl+C to stop all nodes")
        
        # Wait for all processes
        for proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        print("\nStopping all nodes...")
        for proc in processes:
            proc.terminate()

if __name__ == "__main__":
    main()
