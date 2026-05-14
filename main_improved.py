"""Improved main.py with proper error handling, validation, and security."""

from uuid import uuid4
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import asyncio
import os
import json
import time
from datetime import datetime
from typing import Dict

from services.core.twilio.twilio import twilio_handler
from twilio.twiml.voice_response import Connect, VoiceResponse
from services.config import initial_message, TTS_VOICE_ID, PROMPT
from utils import get_twilio_client, check_and_set_initial_message, call_exotel_api, getDb
from dotenv import load_dotenv
from logger_config import logger
from services.core.pipecat_agent.twilio_bot import run_twilio_bot
from services.core.pipecat_agent.exotel_bot import run_exotel_agent
from services.core.pipecat_agent.websocket_bot import run_voice_assistant_bot
from services.core.pipecat_agent.rag_bot import rag_bot

# Import our new models and exceptions
from models.requests import CallRequest, VoiceAssistantRequest
from models.responses import (
    CallResponse, VoiceAssistantResponse, HealthResponse, 
    ErrorResponse, ResponseStatus
)
from exceptions import (
    AICallAgentException, TwilioAPIError, ExotelAPIError, 
    DatabaseError, ValidationError
)

load_dotenv(override=True)

# Initialize FastAPI with proper metadata
app = FastAPI(
    title="AI Call Agent API",
    description="A sophisticated AI-powered voice call agent platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Improved CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restrict to specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict to needed methods
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Request {request.url} took {process_time:.4f}s")
    return response

# Global exception handler
@app.exception_handler(AICallAgentException)
async def ai_call_agent_exception_handler(request: Request, exc: AICallAgentException):
    """Handle custom application exceptions."""
    logger.error(f"Application error: {exc.error_code} - {exc.message}", extra={"details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=exc.error_code,
            message=exc.message,
            details=exc.details
        ).dict()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details=exc.errors()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred"
        ).dict()
    )

# WebSocket endpoints (keeping original structure but with better error handling)
@app.websocket("/ws/handle_call")
async def websocket_endpoint(websocket: WebSocket):
    """Handle Twilio WebSocket connections."""
    await websocket.accept()
    try:
        await twilio_handler(websocket)
    except WebSocketDisconnect:
        logger.info("Client disconnected from handle_call websocket")
    except Exception as e:
        logger.error(f"Error in handle_call websocket: {str(e)}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@app.websocket("/ws/pipecat/{session_id}")
async def pipecat_websocket_endpoint(websocket: WebSocket, session_id: str):
    """Handle Pipecat WebSocket connections."""
    await websocket.accept()
    try:
        # Read initial WebSocket messages
        start_data = websocket.iter_text()
        await start_data.__anext__()

        # Second message contains the call details
        call_data = json.loads(await start_data.__anext__())

        # Extract both StreamSid and CallSid
        stream_sid = call_data["start"]["streamSid"]
        call_sid = call_data["start"]["callSid"]
        
        # Start recording
        twilio_client = get_twilio_client()
        twilio_client.calls(call_sid).recordings.create({"recordingChannels": "dual"})

        # Run your Pipecat bot
        await run_twilio_bot(websocket, stream_sid, call_sid, session_id)
        
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from pipecat websocket: {session_id}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in websocket data: {str(e)}")
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
    except Exception as e:
        logger.error(f"Error in pipecat websocket {session_id}: {str(e)}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@app.websocket("/ws/voice-assistant/{session_id}")
async def voice_assistant_endpoint(websocket: WebSocket, session_id: str):
    """Handle voice assistant WebSocket connections."""
    await websocket.accept()
    try:
        logger.info(f"Voice assistant session started: {session_id}")
        await run_voice_assistant_bot(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from voice assistant: {session_id}")
    except Exception as e:
        logger.error(f"Error in voice assistant {session_id}: {str(e)}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@app.websocket("/ws/telecmi")
async def telecmi_websocket_endpoint(websocket: WebSocket):
    """Handle Exotel/TeleCMI WebSocket connections."""
    await websocket.accept()
    try:
        start_data = websocket.iter_text()
        await start_data.__anext__()

        # Second message contains the call details
        call_data = json.loads(await start_data.__anext__())
        logger.info(f"Exotel call data received: {call_data}")
        
        # Extract call information
        stream_sid = call_data["start"]["stream_sid"]
        call_sid = call_data["start"]["call_sid"]
        session_id = call_data["start"]["custom_parameters"]["session_id"]
        
        await run_exotel_agent(websocket, stream_sid, call_sid, session_id=session_id)
        
    except WebSocketDisconnect:
        logger.info("Client disconnected from telecmi websocket")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in telecmi websocket: {str(e)}")
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
    except Exception as e:
        logger.error(f"Error in telecmi websocket: {str(e)}", exc_info=True)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@app.websocket("/rag_bot")
async def rag_bot_api(websocket: WebSocket):
    """Handle RAG bot WebSocket connections."""
    try:
        session_id = str(uuid4())
        await rag_bot(websocket, session_id)
    except Exception as e:
        logger.error(f"Error in rag_bot: {str(e)}", exc_info=True)
        raise AICallAgentException("Failed to initialize RAG bot", details=str(e))

# REST API endpoints with proper validation and error handling
@app.post("/handle-call")
async def handle_call():
    """Handle Twilio webhook for call setup."""
    try:
        server = os.environ.get("SERVER")
        if not server:
            raise ValidationError("SERVER environment variable not configured")
            
        response = VoiceResponse()
        connect = Connect()
        connect.stream(url=f"wss://{server}/ws")
        response.append(connect)
        
        return HTMLResponse(content=str(response), status_code=200)
        
    except Exception as e:
        logger.error(f"Error in handle-call webhook: {str(e)}", exc_info=True)
        raise AICallAgentException("Failed to handle call webhook", details=str(e))

@app.post("/start_call", response_model=CallResponse)
async def start_call(request: CallRequest):
    """Initiate a Twilio voice call with AI agent."""
    session_id = str(uuid4())
    
    try:
        db = getDb()
        
        # Use validated request data
        prompt = request.prompt or PROMPT
        voice_id = request.voice_id or TTS_VOICE_ID
        initial_msg = request.initial_message or initial_message
        
        # Prepare WebSocket URL
        server = os.environ.get("SERVER")
        if not server:
            raise ValidationError("SERVER environment variable not configured")
            
        await check_and_set_initial_message(initial_msg)
        ws_url = f"wss://{server}/ws/pipecat/{session_id}"
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?><Response><Connect><Stream url="{ws_url}" /></Connect></Response>'''
        
        # Store call configuration
        call_config = {
            "session_id": session_id,
            "to_number": request.to_number,
            "prompt": prompt,
            "language": request.language,
            "voice_id": voice_id,
            "initial_message": initial_msg,
            "created_at": datetime.utcnow()
        }
        
        await db.call_configs.insert_one(call_config)
        
        # Initiate Twilio call
        twilio_client = get_twilio_client()
        call = twilio_client.calls.create(
            to=request.to_number,
            from_=os.environ.get('FROM_NUMBER'),
            twiml=twiml
        )
        
        logger.info(f"Call initiated successfully: {session_id} -> {request.to_number}")
        
        return CallResponse(
            status=ResponseStatus.SUCCESS,
            message="Call initiated successfully",
            call_id=call.sid,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}", exc_info=True)
        
        if "twilio" in str(e).lower():
            raise TwilioAPIError("Failed to initiate Twilio call", details=str(e))
        elif "database" in str(e).lower() or "mongo" in str(e).lower():
            raise DatabaseError("Failed to store call configuration", details=str(e))
        else:
            raise AICallAgentException("Failed to start call", details=str(e))

@app.post("/start_call_exotel", response_model=CallResponse)
async def start_call_exotel(request: CallRequest):
    """Initiate an Exotel voice call with AI agent."""
    session_id = str(uuid4())
    
    try:
        db = getDb()
        
        # Store call configuration
        call_config = {
            "session_id": session_id,
            "to_number": request.to_number,
            "prompt": request.prompt or PROMPT,
            "language": request.language,
            "voice_id": request.voice_id or TTS_VOICE_ID,
            "initial_message": request.initial_message or initial_message,
            "created_at": datetime.utcnow()
        }
        
        await db.call_configs.insert_one(call_config)
        
        # Make Exotel API call
        response_code = call_exotel_api(request.to_number, session_id)
        
        if response_code != 200:
            raise ExotelAPIError(f"Exotel API returned status code: {response_code}")
        
        logger.info(f"Exotel call initiated successfully: {session_id} -> {request.to_number}")
        
        return CallResponse(
            status=ResponseStatus.SUCCESS,
            message="Exotel call initiated successfully",
            session_id=session_id
        )
        
    except ExotelAPIError:
        raise
    except Exception as e:
        logger.error(f"Error initiating Exotel call: {str(e)}", exc_info=True)
        
        if "database" in str(e).lower() or "mongo" in str(e).lower():
            raise DatabaseError("Failed to store call configuration", details=str(e))
        else:
            raise AICallAgentException("Failed to start Exotel call", details=str(e))

@app.post("/create_voice_assistant_session", response_model=VoiceAssistantResponse)
async def create_voice_assistant_session(request: VoiceAssistantRequest):
    """Create a WebSocket voice assistant session."""
    session_id = str(uuid4())
    
    try:
        db = getDb()
        
        # Store session configuration
        session_config = {
            "session_id": session_id,
            "prompt": request.prompt or PROMPT,
            "language": request.language,
            "voice_id": request.voice_id or TTS_VOICE_ID,
            "initial_message": request.initial_message or initial_message,
            "created_at": datetime.utcnow()
        }
        
        await db.call_configs.insert_one(session_config)
        
        server = os.environ.get("SERVER")
        if not server:
            raise ValidationError("SERVER environment variable not configured")
            
        ws_url = f"wss://{server}/ws/voice-assistant/{session_id}"
        
        logger.info(f"Voice assistant session created: {session_id}")
        
        return VoiceAssistantResponse(
            ws_url=ws_url,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error creating voice assistant session: {str(e)}", exc_info=True)
        
        if "database" in str(e).lower() or "mongo" in str(e).lower():
            raise DatabaseError("Failed to store session configuration", details=str(e))
        else:
            raise AICallAgentException("Failed to create voice assistant session", details=str(e))

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with detailed information."""
    return HealthResponse(
        status="Working",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/health", response_model=HealthResponse)
async def detailed_health_check():
    """Detailed health check with service status."""
    try:
        # Test database connection
        db = getDb()
        await db.command("ping")
        
        return HealthResponse(
            status="Healthy",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_improved:app", host="0.0.0.0", port=5000, reload=True)
