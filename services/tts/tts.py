import websockets
from services.event_emmiter import EventEmitter
import base64
from io import BytesIO
import aiohttp
from services.config import ELEVENLABS_API_KEY, CARTESIA_API_KEY
import json
import logging
from typing import AsyncGenerator, Optional





class TTSService(EventEmitter):

    def __init__(self, type):
        super().__init__()
        self.voice_id = "MF4J4IDTRo0AxOO4dpFR"
        self.model_id = "eleven_turbo_v2_5"
        self.language_code = "hi"
        self.type = type
        self.output_format = "mp3_44100_128" if self.type == "assistant" else "ulaw_8000"
        self.tts_ws = None
        self.timeout = 360
        self.cartesia_voice_id = "hi-IN-Standard-A"  # Default Hindi voice for Cartesia
        self.cartesia_endpoint = "https://api.cartesia.ai/tts/bytes"
        self.logger = logging.getLogger(__name__)

    async def get_audio(self, text):
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            headers = {
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/wav"
            }
            params = {
                "output_format": self.output_format,
                "optimize_streaming_latency": 4
            }
            data = {
                "model_id": self.model_id,
                "text": text,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, json=data) as response:
                    if response.status == 200:
                        audio_content = await response.read()
                        if self.type != "assistant":
                            audio_content_encoded = base64.b64encode(audio_content)
                            decoded_audio_content = base64.b64encode(audio_content).decode('utf-8')
                        await self.emit('audio', decoded_audio_content)
                        return audio_content_encoded
                    else:
                        error_text = await response.text()
                        self.logger.error(f"TTS API error: {response.status} - {error_text}")
                        return None
                        print(f"Error getting audio: {response}")
        except Exception as e:
            self.logger.error(f"Error in get_audio: {str(e)}", exc_info=True)
            return None


    async def stream_cartesia_tts(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS audio from Cartesia API in chunks.
        Yields audio chunks as they are received.
        """
        headers = {
            "X-API-Key": CARTESIA_API_KEY,
            "Content-Type": "application/json",
            "Cartesia-Version": "2025-04-16"
        }

        payload = {
            "transcript": text,
            "voice": {
                "id": "56e35e2d-6eb6-4226-ab8b-9776515a7094",
                "mode": "id"
            },
            "output_format": {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 8000,
            },
            "language": self.language_code,
            "model_id": "sonic-2",
        }
        TARGET_CHUNK_SIZE = 50 * 1024 

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.cartesia_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    print(response.status)
                    if response.status != 200:
                        error_text = await response.text()
                        print(error_text)
                        #self.logger.error(f"Cartesia API error: {response.status} - {error_text}")
                        return
                    accumulated_chunk = b""

                    # Stream the audio in chunks
                    async for chunk in response.content.iter_chunked(1024):  # 1KB chunks
                        if chunk:
                            accumulated_chunk += chunk
                            if len(accumulated_chunk) >= TARGET_CHUNK_SIZE:
                                accumulated_chunk = accumulated_chunk[TARGET_CHUNK_SIZE:]
                                b64_audio_chunk = base64.b64encode(accumulated_chunk).decode('utf-8')
                                await self.emit('audio', b64_audio_chunk)
                    b64_audio_chunk = base64.b64encode(accumulated_chunk).decode('utf-8')
                    await self.emit('audio', b64_audio_chunk)

        except asyncio.TimeoutError:
            print("Cartesia TTS request timed out")
        except Exception as e:
            print(f"Error in stream_cartesia_tts: {str(e)}", exc_info=True)

    async def connect_tts(self):
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}&output_format={self.output_format}&inactivity_timeout={self.timeout}"
        tts_ws = await websockets.connect(uri)
        self.tts_ws = tts_ws
        await tts_ws.send(json.dumps({
            "text": " ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            "xi_api_key": ELEVENLABS_API_KEY,
        }))

    async def close(self):
        await self.tts_ws.close()

    async def handle_error(self, error):
        print(f"Error: {error}")

    async def handle_close(self, code, reason):
        print(f"Closed: {code} {reason}")

    async def handle_warning(self, warning):
        print(f"Warning: {warning}")

    async def handle_metadata(self, metadata):
        print(f"Metadata: {metadata}")
    
    async def end_tts_streaming(self, tts_ws):
        try:
            await tts_ws.send(json.dumps({"text": ""}))
        except Exception as e:
            print(f"Error ending TTS streaming: {e}")

    
    async def disconnect(self):
        if self.tts_ws is None:
            return
        await self.tts_ws.close()
        self.tts_ws = None
