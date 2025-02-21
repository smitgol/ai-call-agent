import websockets
from services.event_emmiter import EventEmitter
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents, DeepgramClientOptions
from .config import DEEPGRAM_API_KEY

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
        self.language = "hi"
        self.model = "nova-2"
        self.encoding = "mulaw"
        self._for = TYPE

    async def connect(self):
        self.deepgram_live = self.client.listen.asyncwebsocket.v("1")
        if self._for == "twilio":
            
            await self.deepgram_live.start(LiveOptions(
                language=self.language, 
                encoding=self.encoding,
                sample_rate=8000,
                channels=1,
                punctuate=True,
                interim_results=True,
                endpointing=200,
                utterance_end_ms=1000
            ))
            
        else:
            await self.deepgram_live.start(LiveOptions(
                language=self.language,
                model=self.model,
            ))

        self.deepgram_live.on(LiveTranscriptionEvents.Transcript, self.handle_transcription)
        self.deepgram_live.on(LiveTranscriptionEvents.Error, self.handle_error)
        self.deepgram_live.on(LiveTranscriptionEvents.Close, self.handle_close)
        self.deepgram_live.on(LiveTranscriptionEvents.Warning, self.handle_warning)
        self.deepgram_live.on(LiveTranscriptionEvents.Metadata, self.handle_metadata)
        self.deepgram_live.on(LiveTranscriptionEvents.UtteranceEnd, self.handle_utterance_end)

    async def handle_utterance_end(self, self_obj, utterance_end):
        try:
            if not self.speech_final:
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
                    stream_sid = self.stream_sid
                    await self.emit('utterance', text, stream_sid)
        except Exception as e:
            print("Error in handle_transcription")
            e.print_stack()

            
    async def handle_error(self, self_obj, error):
        self.is_connected = False
    
    async def handle_warning(self, self_obj, warning):
        pass

    async def handle_metadata(self, self_obj, metadata):
        pass

    async def handle_close(self, self_obj, close):
        pass

    async def send(self, payload: bytes):
        if self.deepgram_live:            
            await self.deepgram_live.send(payload)
    
    async def disconnect(self):
        if self.deepgram_live:
            await self.deepgram_live.finish()
            self.deepgram_live = None
        self.is_connected = False
        pass

