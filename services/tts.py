import websockets
from services.event_emmiter import EventEmitter
import base64
from io import BytesIO
import aiohttp
from services.config import ELEVENLABS_API_KEY
import json





class TTSService(EventEmitter):

    def __init__(self, type):
        super().__init__()
        self.voice_id = "MF4J4IDTRo0AxOO4dpFR"
        self.model_id = "eleven_turbo_v2_5"
        self.language_code = "hi"
        self.type = type
        self.output_format =  "mp3_44100_128" if self.type == "assistant" else "ulaw_8000"
        self.tts_ws = None
        self.timeout = 360

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
                "language_code": self.language_code
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
                        print(f"Error getting audio: {response}")
        except Exception as e:
            print(f"Error getting audio: {e}")
    
    async def connect_tts(self):
        uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}&output_format={self.output_format}&optimize_streaming_latency=4&language_code={self.language_code}&inactivity_timeout={self.timeout}"
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
