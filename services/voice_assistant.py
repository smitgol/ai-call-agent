import asyncio
import json
import time
from fastapi import WebSocketDisconnect
from services.stt import STTService
from services.tts import TTSService 
from services.llm import LLMService




async def voice_assistant_handler(ws):
    try:
        stt_service = STTService("assistant")
        llm_service = LLMService()
        tts_service = TTSService("assistant")

        stt_start_time = 0.0  # Initialize here so both functions can access it
        llm_start_time = 0.0
        tts_start_time = 0.0

         # Queue for incoming WebSocket messages
        message_queue = asyncio.Queue()

        async def websocket_listener():
            try:
                while True:
                    data = await ws.receive()
                    if 'text' in data:
                        message = json.loads(data['text'])
                        if message.get('action') == 'start':
                            await stt_service.connect()
                    if 'bytes' in data:
                        await message_queue.put(data)
            except WebSocketDisconnect:
                print("WebSocket disconnected")
                await ws.close()
                print("Client disconnected")

        async def message_processor():
            """Receives and processes messages from client"""
            while True:
                message = await message_queue.get()
                try:
                    audio = message['bytes']
                    nonlocal stt_start_time
                    stt_start_time = time.time()
                    await stt_service.send(audio)
                except Exception as e:
                    print(f"Error processing message: {e}")

        async def handle_llm(transcript):
            nonlocal llm_start_time
            stt_total_time = time.time() - stt_start_time
            llm_start_time = time.time()
            print(f"STT processing time: {stt_total_time:.2f} seconds")
            await llm_service.completion(transcript)
            await ws.send_text(json.dumps({'transcription': transcript}))
        
        async def handle_tts(text):
            nonlocal tts_start_time
            llm_total_time = time.time() - llm_start_time
            tts_start_time = time.time()
            print(f"LLM processing time: {llm_total_time:.2f} seconds")
            await tts_service.get_audio(text)

        async def send_audio_to_client(audio):
            tts_total_time = time.time() - tts_start_time
            print(f"TTS processing time: {tts_total_time:.2f} seconds")
            await ws.send_bytes(audio)
        
        stt_service.on("transcription", handle_llm)
        llm_service.on("llm_response", handle_tts)
        tts_service.on("audio", send_audio_to_client)

        listener_task = asyncio.create_task(websocket_listener())
        processor_task = asyncio.create_task(message_processor())

        await asyncio.gather(listener_task, processor_task)
    
    except WebSocketDisconnect:
        print("Client disconnected")
        await ws.close()
