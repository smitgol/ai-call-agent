import asyncio
import json
import base64
import time
from collections import deque
from services.stream import StreamService
from services.stt import deepgram_connect, openai_stt_connect, openai_ws_config
from services.tts import TTSService 
from services.llm import LLMService
from fastapi import WebSocketDisconnect
from utils import text_chunker, getAudioContent, get_twilio_client
import websockets
from services.config import initial_message, repeat_message
import audioop
import webrtcvad
import logging
import uuid
import torch
import numpy as np
from .call_transcription import TranscriptionLogger
from pydub import AudioSegment

# Load the Silero VAD model and its utility functions.
# This will download the model if it isn't already cached.
model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=False)
(get_speech_ts, _, _, _, _) = utils


SAMPLING_RATE = 8000

logger = logging.getLogger(__name__)

async def twilio_handler(client_ws):
    outbox = asyncio.Queue()
    audio_queue = asyncio.Queue()
    #streamsid_queue = asyncio.Queue()

    stt_start_time = 0.0  # Initialize here so both functions can access it
    llm_start_time = 0.0
    tts_start_time = 0.0

    stream_service = StreamService(client_ws)
    #stt_service = STTService("twilio")
    stt_service = await openai_stt_connect()
    await stt_service.send(json.dumps(openai_ws_config()))
    #await stt_service.connect()

    llm_service = LLMService()
    tts_service = TTSService("twilio")
    await tts_service.connect_tts()
    marks = deque()
    tts_task = None
    end_call_after_this_mark = None
    audio_buffer = np.array([], dtype=np.float32)
    audio_cursor = 0.

    #var for log
    transcription_logger = None
    try:

        ## Region STT 
        async def stt_sender(deepgram_ws):
            print('started deepgram sender')
            while True:
                chunk = await outbox.get()
                await deepgram_ws.send(chunk)
                print('sent audio to deepgram')

        async def stt_receiver(deepgram_ws):
            nonlocal audio_cursor
            async for message in deepgram_ws:
                try:
                    dg_json = json.loads(message)
                    print(dg_json)
                    # print the results from deepgram!
                    if dg_json['type'] == "conversation.item.input_audio_transcription.completed":
                        transcription = dg_json['transcript']
                        if transcription.strip():
                            if transcription_logger:
                                transcription_logger.add_entry("STT", transcription)
                            await llm_service.complete_with_chunks(transcription)
                    elif dg_json['type'] == "input_audio_buffer.speech_started":
                        print('speech started')
                        await stop_speaking()
                    '''
                    if dg_json["is_final"] == True:
                        transcript = dg_json["channel"]["alternatives"][0]["transcript"]
                        if transcript.strip():
                            if transcription_logger:
                                transcription_logger.add_entry("STT", transcript)
                                #logger.info("stt transcript: ", transcript)
                            print('final transcript: ' + transcript)
                            await llm_service.complete_with_chunks(transcript)
                    '''
                except:
                    print('was not able to parse deepgram response as json')
                    continue
            print('finished deepgram receiver')
        async def process_media(msg):
            nonlocal audio_buffer
            raw_data = base64.b64decode(msg['media']['payload'])
            #stt_service.stream(raw_data)
            pcm_data = audioop.ulaw2lin(raw_data, 2)
    
            # Convert and normalize
            chunk_np = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_buffer = np.concatenate((audio_buffer, chunk_np))
            # Process every 500ms (adjust based on your needs)
            if len(audio_buffer) >= SAMPLING_RATE * 0.5:  # 500ms of audio
                try:
                    speech_segments = get_speech_ts(
                        audio_buffer,
                        model,
                        sampling_rate=SAMPLING_RATE,
                        threshold=0.4,  # Lowered threshold
                        min_speech_duration_ms=300  # Adjust as needed
                    )
                    if speech_segments:
                        logger.info("Speech detected")
                        await stop_speaking()
                    # Reset buffer after processing
                    audio_buffer = np.array([], dtype=np.float32)
                except Exception as e:
                    logger.error(f"VAD error: {e}")



        async def handle_audio_sent(mark_label):
            marks.append(mark_label)

        async def handle_utterance(text):
            try:
                await speak_default_text()
                #await stop_speaking()
            except Exception as e:
                logger.error(f"Error handling utterance: {e}")
        
        async def stop_speaking():
            try:
                streamId = stream_service.get_streamsid()
                sending_audio = stream_service.get_send_audio()

                if (sending_audio):
                    if (streamId):
                        payload = {
                            "streamSid": streamId,
                            "event": "clear",
                        }
                        await client_ws.send_json(payload)
                        stream_service.set_send_audio(False)
                        stream_service.reset()
                        marks.clear()
                        if tts_service.tts_ws:
                            await tts_service.disconnect()
                            await tts_service.connect_tts()
                
            except Exception as e:
                logger.error(f"Error stopping speaking: {e}")

        async def speak_default_text():
            if transcription_logger:
                    transcription_logger.add_entry("LLM", "Speaking default text")
            await tts_service.get_audio(repeat_message)

        # END STT Region

        async def handle_llm(transcript):
            nonlocal llm_start_time
            stt_total_time = time.time() - stt_start_time
            logger.info(f"STT processing time: {stt_total_time:.2f} seconds")
            llm_start_time = time.time()
            #await llm_service.completion(transcript)
            nonlocal transcription_logger
            if transcription_logger:
                transcription_logger.add_entry("STT", transcript)
            await llm_service.complete_with_chunks(transcript)

        async def handle_tool_call(tool_name):
            try:
                if tool_name == "end_call":
                    nonlocal end_call_after_this_mark
                    end_call_after_this_mark = str(uuid.uuid4())
            except Exception as e:
                logger.error(f"Error handling tool call: {e}")
        
        # TO BE USED WHEN USING TTS BY API
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
                nonlocal llm_start_time
                nonlocal tts_start_time
                if tts_task:
                    tts_task.cancel()

                await tts_service.disconnect()
                await tts_service.connect_tts()
                tts_task = asyncio.create_task(send_audio_chunks_to_twilio(tts_listener()))
                complete_sentence = ""
                async for text in text_chunker(text_iterator, llm_service):
                    complete_sentence += text
                    if text:  # Skip empty strings
                        try:
                            await tts_service.tts_ws.send(json.dumps({"text": text}))
                            logger.info(f"Sent text to TTS: {text}")
                        except Exception as e:
                            logger.error(f"Error sending text to TTS: {e} {text}")
                            logger.error("TTS WebSocket closed, reconnecting...")
                            tts_task.cancel()
                            await tts_service.connect_tts()
                            await tts_service.tts_ws.send(json.dumps({"text": text}))
                llm_service.user_context.append({"role": "assistant", "content": complete_sentence}) #pushing the complete sentence to user context
                logger.info(f"Complete sentence from llm: {complete_sentence}")
                if transcription_logger:
                    transcription_logger.add_entry("LLM", complete_sentence)
                    logger.info("added to transcription log")
                total_llm_time = time.time() - llm_start_time
                logger.info(f"LLM processing time: {total_llm_time:.2f} seconds")
                if tts_service.tts_ws:
                    await tts_service.end_tts_streaming(tts_service.tts_ws)
                await tts_task
                tts_start_time = time.time()
            except Exception as e:
                logger.error(f"Error sending chunks to TTS: {e}")

        async def send_audio_chunks_to_twilio(tts_listener):
            nonlocal tts_start_time
            async for audio_chunk in tts_listener:
                stream_service.set_send_audio(True)
                await send_audio_to_twilio(audio_chunk)
            # If this is the final message and we're ending the call, send a mark
            if end_call_after_this_mark:
                mark_label = end_call_after_this_mark
                payload = {
                    "event": "mark",
                    "streamSid": stream_service.get_streamsid(),
                    "mark": {"name": mark_label}
                }
                await client_ws.send_json(payload)
            total_tts_time = time.time() - tts_start_time
            logger.info(f"TTS processing time: {total_tts_time:.2f} seconds")


        
        async def tts_listener():
            ws = tts_service.tts_ws
            nonlocal tts_task
            try:
                while True:
                    try:
                        message = await ws.recv()
                        data = json.loads(message)
                        if data.get("audio"):
                            yield data["audio"]
                            pass
                        elif data.get('isFinal'):
                            #send_audio_to_twilio("")
                            stream_service.set_send_audio(True)
                            break
                    except websockets.exceptions.ConnectionClosed:
                            logger.error("error from tts listener")
                            break
            except Exception as e:
                logger.error(f"Error listening to TTS: {e}")
        
        async def send_audio_to_twilio(audio):
            tts_total_time = time.time() - tts_start_time
            await stream_service.sent_audio(audio)
        
        async def end_call():
            call_sid = stream_service.get_callsid()
            if call_sid:
                if transcription_logger:
                            await transcription_logger.save_to_file()
                get_twilio_client().calls(call_sid).update(status="completed")
                logger.info("Call ended by tool call")
                # Close connections
                await client_ws.close()
                #stt_service.close()
                await tts_service.disconnect()

         # Queue for incoming WebSocket messages
        message_queue = asyncio.Queue()

        async def websocket_listener():
            try:
                while True:
                    data = await client_ws.receive_text()
                    await message_queue.put(json.loads(data))
            except WebSocketDisconnect:
                logger.info("Client disconnected")
           

        async def message_processor():
            """Receives and processes messages from Twilio"""
            logger.info("Client receiver connected")
            nonlocal transcription_logger
            nonlocal audio_cursor
            BUFFER_SIZE = 20 * 160
            buffer = bytearray(b'')
            empty_byte_received = False
            while True:
                message = await message_queue.get()
                try:
                    event_type = message.get("event")

                    if event_type == "start":
                        stream_sid = message['start']['streamSid']
                        call_sid = message['start']['callSid']
                        stream_service.set_streamsid(stream_sid)
                        stream_service.set_callsid(call_sid)
                        get_twilio_client().calls(call_sid).recordings.create({"recordingChannels": "dual"})
                        transcription_logger = TranscriptionLogger(call_sid)
                        # Set connection ID in context
                        audio_content = getAudioContent(initial_message)
                        await stream_service.sent_audio(audio_content)
                    elif event_type == "media":
                        media = message['media']
                        chunk = base64.b64decode(media['payload'])
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": message['media']['payload']
                        }
                        if stt_service:
                            await stt_service.send(json.dumps(audio_append))
                        #asyncio.create_task(process_media(message))                    
                        #time_increment = len(chunk) / 8000.0
                        #audio_cursor += time_increment
                        #buffer.extend(chunk)
                        #if chunk == b'':
                        #    empty_byte_received = True
                    elif event_type == "mark":
                        mark_label = message['mark']['name']
                        if end_call_after_this_mark and mark_label == end_call_after_this_mark:
                            await end_call()
                    elif event_type == "stop":
                        logger.info("Twilio connection stopped")
                        if transcription_logger:
                            await transcription_logger.save_to_file()
                        await client_ws.close()
                        #stt_service.close()
                        await tts_service.disconnect()
                        break
                    if len(buffer) >= BUFFER_SIZE or empty_byte_received:
                        outbox.put_nowait(buffer)
                        buffer = bytearray(b'')
                except Exception as e:
                    logger.error(f"Client Receiver Error: {e}")
        
        #stt_service.on("transcription", handle_llm)
        #stt_service.on('utterance', handle_utterance)
        #llm_service.on("llm_response", handle_tts) #only use when we using llm by api
        llm_service.on("llm_stream", send_chunks_to_tts)
        llm_service.on("tool_triggered", handle_tool_call)
        tts_service.on("audio", send_audio_to_twilio) #only when we using tts by api
        stream_service.on('audiosent', handle_audio_sent)


        listener_task = asyncio.create_task(websocket_listener())
        processor_task = asyncio.create_task(message_processor())
        #deepgram_task = asyncio.create_task(stt_sender(stt_service))
        deepgram_receiver_task = asyncio.create_task(stt_receiver(stt_service))

        await asyncio.gather(listener_task, processor_task, deepgram_receiver_task)

    except Exception as e:
        logger.error(f"WebSocket Handler Error: {e}")
    finally:
        #await client_ws.close()
        logger.info("closed websocket connection")
