import websockets
from services.event_emmiter import EventEmitter
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents, DeepgramClientOptions
from services.config import DEEPGRAM_API_KEY, ASSEMBLY_API_KEY, OPENAI_API_KEY, GROQ_API_KEY
import logging
from groq import Groq
logger = logging.getLogger(__name__)

import requests
#import torch
#import numpy as np
import wave
import tempfile
import os

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
 deepgram_ws = await websockets.connect('wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&channels=1&endpointing=true&interim_results=true&model=nova-3&language=multi&smart_format=true&vad_events=true', extra_headers = extra_headers)
 return deepgram_ws

# Initialize Silero VAD model
def initialize_silero_vad():
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        verbose=False
    )
    return model




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
            },
            "input_audio_noise_reduction": {
                "type": "near_field"
            },
        }
    }
   return session_update

def get_ws_gadia():
  url = "https://api.gladia.io/v2/live"
  payload = {
    "encoding": "wav/ulaw",
    "bit_depth": 16,
    "sample_rate": 8000,
    "channels": 1,
    "custom_metadata": {"user": "John Doe"},
    "model": "solaria-1",
    "endpointing": 0.05,
    "maximum_duration_without_endpointing": 5,
    "language_config": {
        "languages": ["en", "hi"],
        "code_switching": False
        },
    "pre_processing": {
        "audio_enhancer": False,
        "speech_threshold": 0.6
        },
    "realtime_processing": {
        "words_accurate_timestamps": False,
        "custom_vocabulary": False,
        "custom_vocabulary_config": {
            "default_intensity": 0.5
            },
        "custom_spelling": False,
        "named_entity_recognition": False,
        "sentiment_analysis": False
        },
    "post_processing": {
        "summarization": False,
        "summarization_config": {"type": "general"},
        "chapterization": False
        },
    "messages_config": {
        "receive_final_transcripts": True,
        "receive_speech_events": True,
        "receive_pre_processing_events": True,
        "receive_realtime_processing_events": True,
        "receive_post_processing_events": True,
        "receive_acknowledgments": True,
        "receive_errors": True,
        "receive_lifecycle_events": False
        },
    "callback": False,
    "callback_config": {
        "url": "https://callback.example",
        "receive_final_transcripts": True,
        "receive_speech_events": False,
        "receive_pre_processing_events": True,
        "receive_realtime_processing_events": True,
        "receive_post_processing_events": True,
        "receive_acknowledgments": False,
        "receive_errors": False,
        "receive_lifecycle_events": True
        }
    }
  headers = {
    "x-gladia-key": "",
    "Content-Type": "application/json"
    }
  response = requests.request("POST", url, json=payload, headers=headers)
  print(response.text)
  return response.json()['url']


async def connect_to_gadia(ws_url):
  ws = await websockets.connect(ws_url)
  return ws