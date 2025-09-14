from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.groq.llm import GroqLLMService
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService, ElevenLabsHttpTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport
)
from pipecat.transcriptions.language import Language
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from services.config import ( ELEVENLABS_API_KEY, GROQ_API_KEY, initial_message, LLM_MODEL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, SENTRY_SDK_URL, TTS_VOICE_ID, PROMPT )
from services.llm.llm import tool_list
import sentry_sdk
from pipecat.observers.base_observer import BaseObserver
from services.call_transcription import TranscriptionLogger
from pipecat.processors.metrics.sentry import SentryMetrics
from pipecat.processors.transcript_processor import TranscriptProcessor
import logging
from pipecat.services.stt_service import STTService
from pipecat.frames.frames import (
    TranscriptionFrame,
    EndFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMMessagesFrame,
    LLMTextFrame,
    BotSpeakingFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    TTSAudioRawFrame,
    AudioRawFrame,
    OutputAudioRawFrame
)
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.cartesia.tts import CartesiaHttpTTSService
#from pipecat.audio.filters.noisereduce_filter import NoisereduceFilter
#from pipecat.audio.turn.smart_turn.local_smart_turn import LocalSmartTurnAnalyzer
#from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
#from pipecat.audio.vad.vad_analyzer import VADParams
from utils import getDb,getAudioContent
import aiohttp

logger = logging.getLogger(__name__)


sentry_sdk.init(
    dsn=SENTRY_SDK_URL,
    traces_sample_rate=1.0,
)


        
        

class CustomObserver(BaseObserver):
    async def on_push_frame(
        self,
        data
    ):
        src = data.source
        frame = data.frame
        timestamp = data.timestamp
        dst = data.destination

        if isinstance(frame, UserStartedSpeakingFrame):
            logger.info(f"👤 {src} -> USER STARTED SPEAKING")
        elif isinstance(frame, UserStoppedSpeakingFrame):
            logger.info(f"👤 {src} -> USER STOPPED SPEAKING")
        elif isinstance(frame, TranscriptionFrame):
             logger.info(f"💬 {src} -> TRANSCRIPTION: {frame.text!r} from {frame.user_id!r}")
        
        elif isinstance(frame, (LLMFullResponseStartFrame, LLMFullResponseEndFrame)):
            event = "START" if isinstance(frame, LLMFullResponseStartFrame) else "END"
            logger.info(f"🧠 {src} -> LLM {event} RESPONSE")
        elif isinstance(frame, LLMTextFrame):
            logger.info(f"🧠 {src} -> LLM GENERATING: {frame.text!r}")
        elif isinstance(frame, ElevenLabsTTSService):
            logger.info(f"🤖 {src} -> BOT SPEAKING: {frame}")




async def run_twilio_bot(websocket_client, stream_sid, call_sid, session_id):
    db = getDb()

    ## gettimg prompt and language from database
    call_config = await db.call_configs.find_one({"session_id": session_id})
    prompt = call_config.get("prompt", PROMPT)
    language = call_config.get("language", Language.HI)
    voice_id = call_config.get("voice_id", TTS_VOICE_ID)
    initial_message_var = call_config.get("initial_message", initial_message)

    audio = getAudioContent(initial_message_var, 'string')
    payload = {
        "streamSid": stream_sid,
        "event": "media",
        "media": {
            "payload": audio
            }
        }
    #await websocket_client.send_json(payload)

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=TWILIO_ACCOUNT_SID,
        auth_token=TWILIO_AUTH_TOKEN,
    )

    # Create the WebSocket transport
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
            transcription_enabled=True,
            #turn_analyzer=LocalSmartTurnAnalyzer(
            #params=SmartTurnParams(
            #    stop_secs=1.0,
            #    pre_speech_ms=0.0,
            #    max_duration_secs=8.0
            #),
            #smart_turn_model_path = "pipecat-ai/smart-turn"
        #),        
        ),
    )
    stt = GroqSTTService(api_key=GROQ_API_KEY, model="whisper-large-v3", language=language,prompt="")

    llm = GroqLLMService(api_key=GROQ_API_KEY, model=LLM_MODEL)

    tts = ElevenLabsTTSService(
        api_key=ELEVENLABS_API_KEY,
        voice_id=voice_id,
        sample_rate=8000,
        params=ElevenLabsTTSService.InputParams(
            language=language,
        ),
        metrics  = SentryMetrics(),
    )


    # Create the initial conversation prompt
    messages = [
        {
            "role": "system",
            "content": prompt
        },
        {
            "role": "assistant",
            "content": initial_message_var
        }
    ]


    # Setup the context aggregator
    context = OpenAILLMContext(messages=messages)
    context_aggregator = llm.create_context_aggregator(context)
    transcript = TranscriptProcessor()
    transcript_logger = TranscriptionLogger(call_sid)
    # Build the pipeline
    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            transcript.user(),
            context_aggregator.user(),
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            transcript.assistant(),
            context_aggregator.assistant(),
        ]
    )

    # Create a pipeline task with appropriate parameters
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,  # Twilio uses 8kHz audio
            audio_out_sample_rate=8000,
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            observers=[CustomObserver()],
        ),
    )

    async def end_call(args):
        await task.queue_frame(EndFrame())
    llm.register_function("end_call", end_call)


    # Setup event handlers
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        pass
        #await task.queue_frame(TTSSpeakFrame(text=initial_message_var))

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()
        await transcript_logger.save_to_mongodb()

    @transcript.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        for msg in frame.messages:
            timestamp = f"[{msg.timestamp}] " if msg.timestamp else ""
            transcript_logger.add_entry(msg.role, msg.content)


    # Run the pipeline
    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)