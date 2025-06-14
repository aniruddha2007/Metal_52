import cv2
import socket
import threading
import numpy as np

UDP_PORT = 5056
MAX_DGRAM = 65507  # Maximum UDP datagram size
FRAME_WIDTH = 320
FRAME_HEIGHT = 240

is_video_sending = False
is_video_receiving = False

def start_video_sender(remote_ip, port=UDP_PORT):
    global is_video_sending
    is_video_sending = True

    def sender():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cap = cv2.VideoCapture(0)

        while is_video_sending:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            encoded, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            if encoded:
                sock.sendto(buffer.tobytes(), (remote_ip, port))

        cap.release()
        sock.close()

    threading.Thread(target=sender, daemon=True).start()


def start_video_receiver(port=UDP_PORT):
    global is_video_receiving
    is_video_receiving = True

    def receiver():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', port))

        while is_video_receiving:
            try:
                data, _ = sock.recvfrom(MAX_DGRAM)
                npdata = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)
                if frame is not None:
                    cv2.imshow("LAN Video Call", frame)
                    if cv2.waitKey(1) == 27:  # ESC to quit
                        break
            except Exception as e:
                print("[VIDEO ERROR]", e)
                break

        sock.close()
        cv2.destroyAllWindows()

    threading.Thread(target=receiver, daemon=True).start()


def stop_video():
    global is_video_sending, is_video_receiving
    is_video_sending = False
    is_video_receiving = False