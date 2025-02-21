from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.twilio import twilio_handler  # assuming twilio_handler is async
from services.config import DEEPGRAM_API_KEY
from services.voice_assistant import voice_assistant_handler
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, lifespan="on")