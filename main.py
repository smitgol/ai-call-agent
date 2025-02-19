from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from services.twilio import twilio_handler  # assuming twilio_handler is async

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await twilio_handler(websocket)
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
