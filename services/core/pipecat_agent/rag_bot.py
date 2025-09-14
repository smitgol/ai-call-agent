import asyncio
import os
import sys
import time

import aiohttp
from pipecat.services.groq.llm import GroqLLMService
import requests
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from loguru import logger
from pipecat.frames.frames import EndFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.serializers.protobuf import ProtobufFrameSerializer

from .llm.langchain_rag_processor import RAGProcessor
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from services.config import ( ELEVENLABS_API_KEY, GROQ_API_KEY, initial_message, LLM_MODEL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, SENTRY_SDK_URL, TTS_VOICE_ID, PROMPT, KOALA_ACCESS_KEY, CARTESIA_API_KEY )
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.groq.stt import GroqSTTService
from pipecat.processors.metrics.sentry import SentryMetrics
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.aggregators.llm_response import (
    LLMAssistantResponseAggregator,
    LLMUserResponseAggregator,
)
from pipecat.audio.filters.koala_filter import KoalaFilter
from pipecat.services.cartesia.tts import CartesiaTTSService


import logging

logger = logging.getLogger(__name__)

language = "hi"
index_name  = "god-ai"

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in message_store:
        message_store[session_id] = ChatMessageHistory()
    return message_store[session_id]


async def rag_bot(websocket_client, session_id):
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=ProtobufFrameSerializer(),
            audio_in_filter=KoalaFilter(access_key=KOALA_ACCESS_KEY)
        ),
    )

    stt = GroqSTTService(api_key=GROQ_API_KEY, model="whisper-large-v3", language=language,prompt="")

    #tts = ElevenLabsTTSService(
    ##    api_key=ELEVENLABS_API_KEY,
    #  voice_id=TTS_VOICE_ID,
    #    sample_rate=8000,
    #    params=ElevenLabsTTSService.InputParams(
    #        language=language,
    #    ),
    #    metrics  = SentryMetrics(),
    #)
    tts = CartesiaTTSService(
        api_key=CARTESIA_API_KEY, 
        voice_id="9b953e7b-86a8-42f0-b625-1434fb15392b",  
        model="sonic-2",
        params=CartesiaTTSService.InputParams(
            language="hi",
            speed="normal"
        )
    )
    llm = GroqLLMService(api_key=GROQ_API_KEY, model=LLM_MODEL)
    messages=[{"role": "system", "content": PROMPT}]
    context = OpenAILLMContext(messages=messages)
    context_aggregator = llm.create_context_aggregator(context)


    rag_processor = RAGProcessor()
    tma_in = LLMUserResponseAggregator()
    tma_out = LLMAssistantResponseAggregator()

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            stt,  # Speech-to-text
            context_aggregator.user(),
            rtvi,
            rag_processor,  # RAG Processor
            llm,
            tts,  # TTS
            transport.output(),
            context_aggregator.assistant(),
            # Transport bot output
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
        print("Pipecat client ready.")
        await rtvi.set_bot_ready()

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        print("Pipecat client connected.")
        #await task.queue_frames([TTSSpeakFrame(text=initial_message)])


    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        print("Pipecat Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)
    return True