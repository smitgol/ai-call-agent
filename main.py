from uuid import uuid4
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from services.twilio import twilio_handler  # assuming twilio_handler is async
from services.voice_assistant import voice_assistant_handler
import os
from twilio.twiml.voice_response import Connect, VoiceResponse
from fastapi.responses import HTMLResponse
from typing import Dict
from services.config import initial_message, TTS_VOICE_ID
from utils import get_twilio_client, check_and_set_initial_message
from dotenv import load_dotenv
from logger_config import logger 
import json
from services.pipecat_agent import run_pipecat_agent
from utils import getAudioContent
from services.config import initial_message
from utils import getDb


load_dotenv(override=True)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.websocket("/ws/handle_call")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await twilio_handler(websocket)
    except WebSocketDisconnect:
        print("Client disconnected")

@app.websocket("/ws/pipecat/{session_id}")
async def pipecat_websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
         # Read initial WebSocket messages
        start_data = websocket.iter_text()
        await start_data.__anext__()

        # Second message contains the call details
        call_data = json.loads(await start_data.__anext__())

        # Extract both StreamSid and CallSid
        stream_sid = call_data["start"]["streamSid"]
        call_sid = call_data["start"]["callSid"]
        get_twilio_client().calls(call_sid).recordings.create({"recordingChannels": "dual"})

        audio = getAudioContent(initial_message, 'string')
        payload = {
            "streamSid": stream_sid,
            "event": "media",
            "media": {
                "payload": audio
            }
        }
        #await websocket.send_json(payload)
        # Run your Pipecat bot
        await run_pipecat_agent(websocket, stream_sid, call_sid, session_id)
    except WebSocketDisconnect:
        print("Client disconnected")


@app.websocket("/ws/voice-assistant")
async def voice_assistant_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await voice_assistant_handler(websocket)
    except WebSocketDisconnect:
        print("Client disconnected")


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
    db = getDb()
    to_number = request.get("to_number")
    prompt = request.get("prompt", initial_message)
    language = request.get("language", "en")
    voice_id = request.get("voice_id", TTS_VOICE_ID)
    session_id = str(uuid4())
    service_url = f"https://{os.environ['SERVER']}/handle-call"
    print("Service URL: ", service_url)
    await check_and_set_initial_message(initial_message)
    ws_url = f"wss://{os.environ['SERVER']}/ws/pipecat/{session_id}"

    twiml = f'''<?xml version="1.0" encoding="UTF-8"?><Response><Connect><Stream url="{ws_url}" /></Connect></Response>'''
    try:
        await db.call_configs.insert_one({
            "session_id":session_id,
            "to_number": to_number,
            "prompt": prompt,
            "language": language,
            "voice_id": voice_id
        })
        twilio_client = get_twilio_client()
        call = twilio_client.calls.create(
            to=to_number,  # Person A
            from_=os.environ['FROM_NUMBER'],  # Your Twilio number
            #url=service_url
            twiml=twiml
        )
        logger.info(f"Call initiated to {to_number}")
        return {"status": "success", "message": "Call initiated"}
    except Exception as e:
        print("Error in start_call")
        print(e)
        logger.error(f"Error in start_call: {e}")
        return {"status": "failed", "message": e}

@app.get("/")
async def read_root():
    return {"Status": "Working"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, lifespan="on")