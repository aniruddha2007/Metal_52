# main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
from services import video_call
from services import udp_helper, audio_call
from services.websocket_manager import register, unregister
from fastapi.responses import StreamingResponse
import cv2

camera = None

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")


@app.on_event("startup")
async def startup_event():
    udp_helper.event_loop = asyncio.get_event_loop()
    udp_helper.start_server()  # <-- auto-start UDP server


@app.get("/chat", response_class=HTMLResponse)
def get_chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await register(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            udp_helper.send_data(msg)
    except WebSocketDisconnect:
        unregister(websocket)


# Audio control endpoints
@app.get("/audio/start")
def audio_start(ip: str = Query(...)):
    try:
        audio_call.start_sending(ip)
        return {"message": f"Started audio → {ip}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/audio/receive")
def audio_receive():
    try:
        audio_call.start_receiving()
        return {"message": "Started receiving audio"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/audio/stop")
def audio_stop():
    try:
        audio_call.stop_audio()
        return {"message": "Audio stopped"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/video/start")
def start_video(ip: str):
    try:
        video_call.start_video_sender(ip)
        return {"message": f"Started sending video to {ip}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/video/receive")
def receive_video():
    try:
        video_call.start_video_receiver()
        return {"message": "Started video receiving"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/video/stop")
def stop_video():
    global camera
    if camera:
        camera.release()
        camera = None
    return {"message": "Video streaming stopped"}

def generate_video_stream():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError("Could not open webcam.")

    while True:
        success, frame = camera.read()
        if not success:
            continue

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
        )

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(generate_video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")