import sounddevice as sd
import socket
import threading
import numpy as np

AUDIO_RATE = 8000  # 8kHz
CHANNELS = 1
DTYPE = 'int16'
UDP_PORT = 5060

is_sending = False
is_receiving = False

def start_sending(remote_ip, port=UDP_PORT):
    global is_sending
    if is_sending:
        print("Already sending")
        return

    def callback(indata, frames, time, status):
        if status:
            print(f"⚠️ Recording error: {status}")
        try:
            data_bytes = indata.tobytes()
            sender.sendto(data_bytes, (remote_ip, port))
        except Exception as e:
            print(f"[ERROR] Failed to send audio data: {e}")

    try:
        print("🎤 Starting audio send...")
        is_sending = True
        global sender
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        stream = sd.InputStream(
            samplerate=AUDIO_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=callback,
            blocksize=1024
        )
        stream.start()
    except Exception as e:
        print(f"[ERROR] Sending failed: {e}")

def start_receiving(port=UDP_PORT):
    global is_receiving
    if is_receiving:
        print("Already receiving")
        return

    is_receiving = True  # <-- move this before starting the thread

    def receive():
        print(f"🔊 Listening for audio on UDP port {port}...")
        global receiver
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.bind(('', port))

        stream = sd.OutputStream(
            samplerate=AUDIO_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=1024
        )
        stream.start()

        while is_receiving:
            try:
                data, _ = receiver.recvfrom(2048)
                audio_array = np.frombuffer(data, dtype=DTYPE)
                stream.write(audio_array)
            except Exception as e:
                print(f"[ERROR] Receiving failed: {e}")
                break

    threading.Thread(target=receive, daemon=True).start()
def stop_audio():
    global is_sending, is_receiving, sender, receiver
    is_sending = False
    is_receiving = False

    if 'sender' in globals():
        sender.close()
    if 'receiver' in globals():
        receiver.close()

    print("🛑 Audio streaming stopped.")