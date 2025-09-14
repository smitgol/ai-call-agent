
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.frames.frames import (
    TTSSpeakFrame
)
import logging
from utils import getDb
import os
from services.config import TTS_VOICE_ID, PROMPT, initial_message, GEMMINI_API_KEY, GROQ_API_KEY, LLM_MODEL, ELEVENLABS_API_KEY
logger = logging.getLogger(__name__)


async def run_voice_assistant_bot(websocket_client, session_id):
    db = getDb()

    ## gettimg prompt and language from database
    call_config = await db.call_configs.find_one({"session_id": session_id})
    prompt = call_config.get("prompt", PROMPT)
    language = call_config.get("language", "en")
    voice_id = call_config.get("voice_id", TTS_VOICE_ID)
    initial_message_var = call_config.get("initial_message", initial_message)


    ws_transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=ProtobufFrameSerializer(),
        ),
    )
    
    stt = GroqSTTService(api_key=GROQ_API_KEY, model="whisper-large-v3", language=language,prompt="")

    llm = GroqLLMService(api_key=GROQ_API_KEY, model=LLM_MODEL)
    messages=[
        {
            "role": "system", 
            "content": PROMPT
        },
        {
            "role": "assistant",
            "content": initial_message_var
        }
    ]
    context = OpenAILLMContext(messages=messages)
    context_aggregator = llm.create_context_aggregator(context)

    tts = ElevenLabsTTSService(
        api_key=ELEVENLABS_API_KEY,
        voice_id=voice_id,
        sample_rate=8000,
        params=ElevenLabsTTSService.InputParams(
            language=language,
        ),
    )


    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            ws_transport.input(),
            stt,
            context_aggregator.user(),
            rtvi,
            llm,
            tts,
            ws_transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        # Kick off the conversation.
        await task.queue_frame(TTSSpeakFrame(text=initial_message_var))

    @ws_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        pass
        #await task.queue_frames([context_aggregator.user().get_context_frame()])

    @ws_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)