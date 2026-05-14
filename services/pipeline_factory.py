"""Factory for creating audio processing pipelines."""

from typing import Optional, Dict, Any
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.filters.koala_filter import KoalaFilter
from pipecat.transcriptions.language import Language
from pipecat.processors.metrics.sentry import SentryMetrics
from pipecat.frames.frames import EndFrame, TTSSpeakFrame

from services.call_transcription import TranscriptionLogger
from services.config import (
    GROQ_API_KEY, ELEVENLABS_API_KEY, CARTESIA_API_KEY, 
    LLM_MODEL, TTS_VOICE_ID, KOALA_ACCESS_KEY
)
from logger_config import logger
from exceptions import ConfigurationError


class PipelineConfig:
    """Configuration for pipeline creation."""
    
    def __init__(
        self,
        session_id: str,
        call_sid: str,
        prompt: str,
        language: str = "en",
        voice_id: Optional[str] = None,
        initial_message: Optional[str] = None,
        tts_provider: str = "elevenlabs",
        enable_metrics: bool = True,
        enable_transcription: bool = True,
        allow_interruptions: bool = True,
        audio_sample_rate: int = 8000
    ):
        self.session_id = session_id
        self.call_sid = call_sid
        self.prompt = prompt
        self.language = language
        self.voice_id = voice_id or TTS_VOICE_ID
        self.initial_message = initial_message
        self.tts_provider = tts_provider
        self.enable_metrics = enable_metrics
        self.enable_transcription = enable_transcription
        self.allow_interruptions = allow_interruptions
        self.audio_sample_rate = audio_sample_rate


class PipelineFactory:
    """Factory for creating standardized audio processing pipelines."""
    
    @staticmethod
    def create_stt_service(language: str = "en") -> GroqSTTService:
        """Create STT service."""
        try:
            # Map language codes to Language enum
            lang_map = {
                "en": Language.EN,
                "es": Language.ES,
                "fr": Language.FR,
                "de": Language.DE,
                "it": Language.IT,
                "pt": Language.PT,
                "hi": Language.HI,
                "ja": Language.JA,
                "ko": Language.KO,
                "zh": Language.ZH
            }
            
            lang_enum = lang_map.get(language, Language.EN)
            
            return GroqSTTService(
                api_key=GROQ_API_KEY,
                model="whisper-large-v3-turbo",
                language=lang_enum,
                prompt=""
            )
        except Exception as e:
            logger.error(f"Failed to create STT service: {str(e)}")
            raise ConfigurationError("Failed to initialize STT service", details=str(e))
    
    @staticmethod
    def create_llm_service() -> GroqLLMService:
        """Create LLM service."""
        try:
            return GroqLLMService(
                api_key=GROQ_API_KEY,
                model=LLM_MODEL
            )
        except Exception as e:
            logger.error(f"Failed to create LLM service: {str(e)}")
            raise ConfigurationError("Failed to initialize LLM service", details=str(e))
    
    @staticmethod
    def create_tts_service(
        provider: str = "elevenlabs",
        voice_id: str = TTS_VOICE_ID,
        language: str = "en",
        sample_rate: int = 8000,
        enable_metrics: bool = True
    ):
        """Create TTS service based on provider."""
        try:
            if provider == "elevenlabs":
                return ElevenLabsTTSService(
                    api_key=ELEVENLABS_API_KEY,
                    voice_id=voice_id,
                    sample_rate=sample_rate,
                    params=ElevenLabsTTSService.InputParams(language=language),
                    metrics=SentryMetrics() if enable_metrics else None
                )
            elif provider == "cartesia":
                return CartesiaTTSService(
                    api_key=CARTESIA_API_KEY,
                    voice_id=voice_id,
                    model="sonic-2",
                    params=CartesiaTTSService.InputParams(
                        language=language,
                        speed="normal"
                    )
                )
            else:
                raise ValueError(f"Unsupported TTS provider: {provider}")
                
        except Exception as e:
            logger.error(f"Failed to create TTS service ({provider}): {str(e)}")
            raise ConfigurationError(f"Failed to initialize TTS service: {provider}", details=str(e))
    
    @staticmethod
    def create_context_and_aggregator(prompt: str, initial_message: Optional[str] = None):
        """Create LLM context and aggregator."""
        try:
            messages = [{"role": "system", "content": prompt}]
            
            if initial_message:
                messages.append({"role": "assistant", "content": initial_message})
            
            context = OpenAILLMContext(messages=messages)
            return context, None  # Aggregator will be created by LLM service
            
        except Exception as e:
            logger.error(f"Failed to create context: {str(e)}")
            raise ConfigurationError("Failed to initialize LLM context", details=str(e))
    
    @staticmethod
    def create_pipeline_components(config: PipelineConfig, transport):
        """Create all pipeline components."""
        try:
            # Create services
            stt = PipelineFactory.create_stt_service(config.language)
            llm = PipelineFactory.create_llm_service()
            tts = PipelineFactory.create_tts_service(
                provider=config.tts_provider,
                voice_id=config.voice_id,
                language=config.language,
                sample_rate=config.audio_sample_rate,
                enable_metrics=config.enable_metrics
            )
            
            # Create context
            context, _ = PipelineFactory.create_context_and_aggregator(
                config.prompt, 
                config.initial_message
            )
            context_aggregator = llm.create_context_aggregator(context)
            
            # Create additional processors
            components = {
                "stt": stt,
                "llm": llm,
                "tts": tts,
                "context_aggregator": context_aggregator,
                "transport": transport
            }
            
            # Optional components
            if config.enable_transcription:
                components["transcript"] = TranscriptProcessor()
                components["transcript_logger"] = TranscriptionLogger(config.call_sid)
            
            return components
            
        except Exception as e:
            logger.error(f"Failed to create pipeline components: {str(e)}")
            raise ConfigurationError("Failed to create pipeline components", details=str(e))
    
    @staticmethod
    def create_standard_pipeline(config: PipelineConfig, transport) -> PipelineTask:
        """Create a standard audio processing pipeline."""
        try:
            components = PipelineFactory.create_pipeline_components(config, transport)
            
            # Build pipeline stages
            pipeline_stages = [
                transport.input(),  # WebSocket input
                components["stt"],  # Speech-to-text
            ]
            
            # Add transcription if enabled
            if config.enable_transcription:
                pipeline_stages.extend([
                    components["transcript"].user(),
                    components["context_aggregator"].user(),
                ])
            else:
                pipeline_stages.append(components["context_aggregator"].user())
            
            pipeline_stages.extend([
                components["llm"],  # Language model
                components["tts"],  # Text-to-speech
                transport.output(),  # WebSocket output
            ])
            
            # Add assistant transcription if enabled
            if config.enable_transcription:
                pipeline_stages.extend([
                    components["transcript"].assistant(),
                    components["context_aggregator"].assistant(),
                ])
            else:
                pipeline_stages.append(components["context_aggregator"].assistant())
            
            # Create pipeline
            pipeline = Pipeline(pipeline_stages)
            
            # Create task with parameters
            task = PipelineTask(
                pipeline,
                params=PipelineParams(
                    audio_in_sample_rate=config.audio_sample_rate,
                    audio_out_sample_rate=config.audio_sample_rate,
                    allow_interruptions=config.allow_interruptions,
                    enable_metrics=config.enable_metrics,
                    enable_usage_metrics=config.enable_metrics,
                )
            )
            
            # Register end call function
            async def end_call(args):
                await task.queue_frame(EndFrame())
            components["llm"].register_function("end_call", end_call)
            
            # Store components for event handling
            task._components = components
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to create pipeline: {str(e)}")
            raise ConfigurationError("Failed to create audio pipeline", details=str(e))
    
    @staticmethod
    def setup_event_handlers(task: PipelineTask, transport, config: PipelineConfig):
        """Setup standard event handlers for the pipeline."""
        try:
            components = task._components
            
            @transport.event_handler("on_client_connected")
            async def on_client_connected(transport, client):
                """Handle client connection."""
                logger.info(f"Client connected to session: {config.session_id}")
                if config.initial_message:
                    await task.queue_frame(TTSSpeakFrame(text=config.initial_message))
            
            @transport.event_handler("on_client_disconnected")
            async def on_client_disconnected(transport, client):
                """Handle client disconnection."""
                logger.info(f"Client disconnected from session: {config.session_id}")
                await task.cancel()
                
                # Save transcription if enabled
                if config.enable_transcription and "transcript_logger" in components:
                    await components["transcript_logger"].save_to_mongodb()
            
            # Setup transcription event handler if enabled
            if config.enable_transcription and "transcript" in components:
                @components["transcript"].event_handler("on_transcript_update")
                async def on_transcript_update(processor, frame):
                    """Handle transcript updates."""
                    if "transcript_logger" in components:
                        source = "user" if hasattr(frame, 'user_id') else "assistant"
                        components["transcript_logger"].add_entry(source, frame.text)
            
            logger.info(f"Event handlers setup completed for session: {config.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            raise ConfigurationError("Failed to setup pipeline event handlers", details=str(e))
