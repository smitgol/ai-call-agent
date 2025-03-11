import json
from services.event_emmiter import EventEmitter
import uuid


class StreamService(EventEmitter):
    def __init__(self, websocket):
        super().__init__()
        self.stream_sid = None
        self.ws = websocket
        self.sending_audio = False

    def set_streamsid(self, streamsid):
        self.stream_sid = streamsid
    
    def get_streamsid(self):
        return self.stream_sid
    
    def set_send_audio(self, status):
        self.sending_audio = status
    
    def get_send_audio(self):
        return self.sending_audio

    async def sent_audio(self, audio):
        payload = {
            "streamSid": self.stream_sid,
            "event": "media",
            "media": {
                "payload": audio
            }
        }
        await self.ws.send_json(payload)
        mark_label = str(uuid.uuid4())
        await self.emit('audiosent', mark_label)
    
    def reset(self):
        self.expected_audio_index = 0
        self.audio_buffer = {}