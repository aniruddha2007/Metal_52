from fastapi import APIRouter
from services import tcp_helper

router = APIRouter()

@router.get("/start-server")
def start_tcp_server():
    return tcp_helper.start_server()

@router.post("/send-data")
def send_data(data: str):
    return tcp_helper.send_data(data)