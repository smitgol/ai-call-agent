import asyncio
import json
import base64
import time
from collections import deque
from services.stream import StreamService
from services.stt import STTService
from services.tts import TTSService 
from services.llm import LLMService
from fastapi import WebSocketDisconnect




async def twilio_handler(client_ws):
    outbox = asyncio.Queue()
    #streamsid_queue = asyncio.Queue()

    stt_start_time = 0.0  # Initialize here so both functions can access it
    llm_start_time = 0.0
    tts_start_time = 0.0

    stream_service = StreamService(client_ws)
    stt_service = STTService()
    await stt_service.connect()

    llm_service = LLMService()
    tts_service = TTSService()
    marks = deque()

    try:

        async def process_media(msg):
            nonlocal stt_start_time
            stt_start_time = time.time()
            await stt_service.send(base64.b64decode(msg['media']['payload']))


        async def handle_audio_sent(mark_label):
            marks.append(mark_label)

        async def handle_utterance(text, stream_sid):
            try:
                if len(marks) > 0 and text.strip():
                    payload = {
                        "streamSid": stream_sid,
                        "event": "clear",
                    }
                    await client_ws.send_json(payload)
                    
                    # reset states
                    stream_service.reset()
            except Exception as e:
                print(f"Error handling utterance: {e}")

        async def handle_llm(transcript):
            nonlocal llm_start_time
            stt_total_time = time.time() - stt_start_time
            print(f"STT processing time: {stt_total_time:.2f} seconds")
            print("STT to LLM")
            llm_start_time = time.time()
            await llm_service.completion(transcript)

        async def handle_tts(text):
            try:
                nonlocal tts_start_time
                llm_total_time = time.time() - llm_start_time
                print(f"LLM processing time: {llm_total_time:.2f} seconds")
                print("LLM to TTS")
                tts_start_time = time.time()
                print("TTS request sent")
                await tts_service.get_audio(text)
            except Exception as e:
                print(f"Error handling LLM response: {e}")
        
        async def send_audio_to_twilio(audio):
            tts_total_time = time.time() - tts_start_time
            print(f"TTS processing time: {tts_total_time:.2f} seconds")
            await stream_service.sent_audio(audio)

         # Queue for incoming WebSocket messages
        message_queue = asyncio.Queue()

        async def websocket_listener():
            try:
                while True:
                    data = await client_ws.receive_text()
                    await message_queue.put(json.loads(data))
            except WebSocketDisconnect:
                print("Client disconnected")
           

        async def message_processor():
            """Receives and processes messages from Twilio"""
            print("Client receiver connected")
            while True:
                message = await message_queue.get()
                try:
                    event_type = message.get("event")

                    if event_type == "start":
                        stream_service.set_streamsid(message["start"]["streamSid"])
                    elif event_type in ("connected", "start"):
                        print("Twilio connected or started")
                    elif event_type == "media":
                        asyncio.create_task(process_media(message))
                    elif event_type == "stop":
                        print("Twilio connection stopped")
                        break
                except Exception as e:
                    print(f"Client Receiver Error: {e}")
        
        stream_service.on('audiosent', handle_audio_sent)
        stt_service.on("transcription", handle_llm)
        stt_service.on('utterance', handle_utterance)
        llm_service.on("llm_response", handle_tts)
        tts_service.on("audio", send_audio_to_twilio)

        listener_task = asyncio.create_task(websocket_listener())
        processor_task = asyncio.create_task(message_processor())

        await asyncio.gather(listener_task, processor_task)

    except Exception as e:
        print(f"WebSocket Handler Error: {e}")
    finally:
        await client_ws.close()
        print("Closed WebSocket connection")
