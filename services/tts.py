import requests
import websockets
from services.event_emmiter import EventEmitter
import base64
from io import BytesIO
import aiohttp
from .config import ELEVENLABS_API_KEY






class TTSService(EventEmitter):

    def __init__(self):
        super().__init__()
        self.voice_id = "JBFqnCBsd6RMkjVDRZzb"
        self.model_id = "eleven_turbo_v2_5"
        self.language_code = "hi"

    async def get_audio(self, text):
        try:
            output_format = "ulaw_8000"            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            headers = {
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/wav"
            }
            params = {
                "output_format": output_format,
                "optimize_streaming_latency": 4
            }
            data = {
                "model_id": self.model_id,
                "text": text,
                "language_code": self.language_code
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params, json=data) as response:
                    if response.status == 200:
                        audio_content = await response.read()
                        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                        await self.emit('audio', audio_base64)
        except Exception as e:
            print(f"Error getting audio: {e}")

    async def close(self):
        await self.tts_ws.__aexit__()

    async def handle_error(self, error):
        print(f"Error: {error}")

    async def handle_close(self, code, reason):
        print(f"Closed: {code} {reason}")

    async def handle_warning(self, warning):
        print(f"Warning: {warning}")

    async def handle_metadata(self, metadata):
        print(f"Metadata: {metadata}")



