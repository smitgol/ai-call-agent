import websockets
from services.event_emmiter import EventEmitter
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents, DeepgramClientOptions
from services.config import DEEPGRAM_API_KEY, ASSEMBLY_API_KEY, OPENAI_API_KEY
import logging
logger = logging.getLogger(__name__)




'''
class STTService(EventEmitter):

    def __init__(self, TYPE):
        super().__init__()
        config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
        self.client = DeepgramClient(DEEPGRAM_API_KEY, config)
        self.deepgram_live = None
        self.final_result = ""
        self.speech_final = False
        self.stream_sid = None
        self.language = "multi"
        self.model = "nova-3"
        self.encoding = "mulaw"
        self._for = TYPE

    async def connect(self):
        try:
            self.deepgram_live = self.client.listen.asyncwebsocket.v("1")
        except Exception as e:
            logger.error(f"Error connecting to Deepgram: {e}")
        if self._for == "twilio":
            try:
                await self.deepgram_live.start(LiveOptions(
                    language=self.language, 
                    encoding=self.encoding,
                    sample_rate=8000,
                    channels=1,
                    punctuate=True,
                    interim_results=True,
                    endpointing=400,
                    utterance_end_ms=1000,
                    model=self.model,
                    vad_events=True,
                    smart_format=True,
                ))
            except Exception as e:
                logger.error(f"Error starting Deepgram live: {e}")
            
        else:
            await self.deepgram_live.start(LiveOptions(
                language=self.language,
                model=self.model,
            ))

        self.deepgram_live.on(LiveTranscriptionEvents.Transcript, self.handle_transcription)
        self.deepgram_live.on(LiveTranscriptionEvents.SpeechStarted, self.handle_speech_started)
        self.deepgram_live.on(LiveTranscriptionEvents.Error, self.handle_error)
        self.deepgram_live.on(LiveTranscriptionEvents.Close, self.handle_close)
        self.deepgram_live.on(LiveTranscriptionEvents.Warning, self.handle_warning)
        self.deepgram_live.on(LiveTranscriptionEvents.Metadata, self.handle_metadata)
        self.deepgram_live.on(LiveTranscriptionEvents.UtteranceEnd, self.handle_utterance_end)

    async def handle_speech_started(self, self_obj, speech_started):
        logger.info("speech started")
        pass
    
    async def handle_utterance_end(self, self_obj, utterance_end):
        try:
            if not self.speech_final:
                logger.info("utterance in handle utterance end")
                await self.emit('utterance', self.final_result)
                self.final_result = ''
                self.speech_final = True
                return
            else:
                return
        except Exception as e:
            e.print_stack()

    async def handle_transcription(self, self_obj, result):
        try:
            alternatives = result.channel.alternatives if hasattr(result, 'channel') else []
            text = alternatives[0].transcript if alternatives else ""

            if result.is_final and text.strip():
                self.final_result += f" {text}"
                if result.speech_final:
                    self.speech_final = True
                    await self.emit('transcription', self.final_result)
                    self.final_result = ''
                else:
                    self.speech_final = False
            else:
                if text.strip():
                    logger.info(f"interim result: {text}")
                    stream_sid = self.stream_sid
                   # await self.emit('utterance', text, stream_sid)
        except Exception as e:
            e.print_stack()

            
    async def handle_error(self, self_obj, error):
        self.is_connected = False
    
    async def handle_warning(self, self_obj, warning):
        pass

    async def handle_metadata(self, self_obj, metadata):
        pass

    async def handle_close(self, self_obj, close):
        pass

    async def stream(self, payload: bytes):
        if self.deepgram_live:            
            await self.deepgram_live.send(payload)
    
    async def close(self):
        if self.deepgram_live:
            await self.deepgram_live.finish()
            self.deepgram_live = None
        self.is_connected = False
        pass
'''

async def deepgram_connect():
 extra_headers = {
  'Authorization': 'Token ' + DEEPGRAM_API_KEY,
 }
 deepgram_ws = await websockets.connect('wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1&endpointing=200&utterance_end_ms=1000&interim_results=true&model=nova-3&language=multi&smart_format=true', extra_headers = extra_headers)

 return deepgram_ws




async def openai_stt_connect():
 OPENAI_WS_URL   = (
    "wss://api.openai.com/v1/realtime"
    "?intent=transcription"
    )
 API_KEY_HEADER  = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }
 openai_ws = await websockets.connect(OPENAI_WS_URL, extra_headers=API_KEY_HEADER)
 return openai_ws

def openai_ws_config():
   session_update = {
        "type": "transcription_session.update",
        "session": {
            "input_audio_format": "g711_ulaw",
            "input_audio_transcription": {"model": "gpt-4o-transcribe", "language": "hi"},
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500,
            },
        }
    }
   return session_update