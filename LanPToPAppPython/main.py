# main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio

from services import udp_helper, audio_call
from services.websocket_manager import register, unregister

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