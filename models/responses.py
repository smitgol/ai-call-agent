"""Response models for API responses."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class ResponseStatus(str, Enum):
    """Response status enumeration."""
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class BaseResponse(BaseModel):
    """Base response model."""
    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Response message")


class CallResponse(BaseResponse):
    """Response model for call initiation."""
    call_id: Optional[str] = Field(None, description="Unique call identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")


class VoiceAssistantResponse(BaseModel):
    """Response model for voice assistant session creation."""
    ws_url: str = Field(..., description="WebSocket URL for the voice assistant session")
    session_id: str = Field(..., description="Session identifier")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field("Working", description="Service status")
    version: Optional[str] = Field(None, description="API version")
    timestamp: Optional[str] = Field(None, description="Current timestamp")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="Error status")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Any] = Field(None, description="Additional error details")
