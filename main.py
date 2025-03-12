from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.twilio import twilio_handler  # assuming twilio_handler is async
from services.voice_assistant import voice_assistant_handler
import os
from twilio.twiml.voice_response import Connect, VoiceResponse
from fastapi.responses import HTMLResponse
from typing import Dict
from services.config import initial_message
from utils import get_twilio_client, check_and_set_initial_message
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI()


app.mount("/static", StaticFiles(directory="voice_assistant/static"), name="static")
templates = Jinja2Templates(directory="voice_assistant")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await twilio_handler(websocket)
    except WebSocketDisconnect:
        print("Client disconnected")

@app.websocket("/ws/voice-assistant")
async def voice_assistant_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await voice_assistant_handler(websocket)
    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/voice-assistant")
async def get_assistant(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/handle-call")
async def handle_call():
    server = os.environ["SERVER"]
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f"wss://{server}/ws")
    response.append(connect)
    return HTMLResponse(content=str(response), status_code=200)

@app.post("/start_call")
async def start_call(request: Dict[str, str]):
    to_number = request.get("to_number")
    service_url = f"https://{os.environ['SERVER']}/handle-call"
    print("Service URL: ", service_url)
    await check_and_set_initial_message(initial_message)
    try:
        twilio_client = get_twilio_client()
        call = twilio_client.calls.create(
            to=to_number,  # Person A
            from_=os.environ['FROM_NUMBER'],  # Your Twilio number
            url=service_url
        )
        return {"status": "success", "message": "Call initiated"}
    except Exception as e:
        print("Error in start_call")
        print(e)
        return {"status": "failed", "message": e}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, lifespan="on")