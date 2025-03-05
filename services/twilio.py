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
from utils import text_chunker, getAudioContent
import websockets
from services.config import initial_message

async def twilio_handler(client_ws):
    outbox = asyncio.Queue()
    #streamsid_queue = asyncio.Queue()

    stt_start_time = 0.0  # Initialize here so both functions can access it
    llm_start_time = 0.0
    tts_start_time = 0.0

    stream_service = StreamService(client_ws)
    stt_service = STTService("twilio")
    await stt_service.connect()

    llm_service = LLMService()
    tts_service = TTSService("twilio")
    await tts_service.connect_tts()
    marks = deque()
    tts_task = None

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
        
        async def stop_speaking():
            try:
                streamId = stream_service.get_streamsid()
                
                if (streamId):
                    payload = {
                        "streamSid": streamId,
                        "event": "clear",
                    }
                    await client_ws.send_json(payload)
                    stream_service.reset()
                    #if tts_service.tts_ws:
                    #    await tts_service.disconnect()
                
            except Exception as e:
                print(f"Error stopping speaking: {e}")

        async def handle_llm(transcript):
            nonlocal llm_start_time
            stt_total_time = time.time() - stt_start_time
            print(f"STT processing time: {stt_total_time:.2f} seconds")
            llm_start_time = time.time()
            print("STT to LLM")
            #await llm_service.completion(transcript)
            await llm_service.complete_with_chunks(transcript)

        # async def handle_tts(text):
        #     try:
        #         nonlocal tts_start_time
        #         llm_total_time = time.time() - llm_start_time
        #         print(f"LLM processing time: {llm_total_time:.2f} seconds")
        #         print("LLM to TTS")
        #         tts_start_time = time.time()
        #         await tts_service.get_audio(text)
        #     except Exception as e:
        #         print(f"Error handling LLM response: {e}")
        
        # TTS PART
        async def send_chunks_to_tts(text_iterator):
            try:
                nonlocal tts_task
                if tts_task:
                    tts_task.cancel()
                tts_task = asyncio.create_task(send_audio_chunks_to_twilio(tts_listener()))
                complete_sentence = ""
                nonlocal tts_start_time
                async for text in text_chunker(text_iterator):
                    complete_sentence += text
                    try:
                        await tts_service.tts_ws.send(json.dumps({"text": text}))
                    except websockets.exceptions.ConnectionClosedOK:
                        print(f"Error sending text to TTS: {e}")
                await tts_service.end_tts_streaming(tts_service.tts_ws)
                print("LLM processing time: ", time.time() - llm_start_time)
                await tts_task
                tts_start_time = time.time()
                llm_service.user_context.append({"role": "assistant", "content": complete_sentence}) #pushing the complete sentence to user context
            except Exception as e:
                print(f"Error sending chunks to TTS: {e}")


        async def send_audio_chunks_to_twilio(tts_listener):
            print("TTS to Twilio")
            async for audio_chunk in tts_listener:
                await send_audio_to_twilio(audio_chunk)
            print('TTS processing time: ', time.time() - tts_start_time)
            await tts_service.disconnect()
            await tts_service.connect_tts()


        
        async def tts_listener():
            ws = tts_service.tts_ws
            nonlocal tts_task
            try:
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    if data.get("audio"):
                        yield data["audio"]
                        pass
                    elif data.get('isFinal'):
                        #send_audio_to_twilio("")
                        if tts_task:
                            tts_task.cancel()
                            tts_task = None
                        break
            except Exception as e:
                print(f"Error listening to TTS: {e}")
        
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
                        audio_content = getAudioContent(initial_message)
                        await stream_service.sent_audio(audio_content)
                    elif event_type in ("connected", "start"):
                        print("Twilio connected or started")
                    elif event_type == "media":
                        asyncio.create_task(process_media(message))
                        #await stop_speaking()
                    elif event_type == "stop":
                        print("Twilio connection stopped")
                        await client_ws.close()
                        break
                except Exception as e:
                    print(f"Client Receiver Error: {e}")
        
        stt_service.on("transcription", handle_llm)
        stt_service.on('utterance', handle_utterance)
        #llm_service.on("llm_response", handle_tts) #only use when we using llm by api
        llm_service.on("llm_stream", send_chunks_to_tts)
        #tts_service.on("audio", send_audio_to_twilio) #only when we using tts by api
        stream_service.on('audiosent', handle_audio_sent)


        listener_task = asyncio.create_task(websocket_listener())
        processor_task = asyncio.create_task(message_processor())

        await asyncio.gather(listener_task, processor_task)

    except Exception as e:
        print(f"WebSocket Handler Error: {e}")
    finally:
        await client_ws.close()
        print("Closed WebSocket connection")
