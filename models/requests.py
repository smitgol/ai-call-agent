"""Request models for API validation."""

from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class CallRequest(BaseModel):
    """Model for call initiation requests."""
    
    to_number: str = Field(..., description="Phone number to call in E.164 format")
    prompt: Optional[str] = Field(None, description="Custom system prompt for the AI agent")
    language: str = Field("en", description="Language code for the conversation")
    voice_id: Optional[str] = Field(None, description="Voice ID for text-to-speech")
    initial_message: Optional[str] = Field(None, description="Initial message to speak when call connects")
    
    @validator('to_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        if not v:
            raise ValueError("Phone number is required")
        
        # Basic E.164 format validation
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError("Phone number must be in E.164 format (e.g., +1234567890)")
        
        return v
    
    @validator('language')
    def validate_language(cls, v):
        """Validate language code."""
        supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'hi', 'ja', 'ko', 'zh']
        if v not in supported_languages:
            raise ValueError(f"Language must be one of: {', '.join(supported_languages)}")
        return v
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt length."""
        if v and len(v) > 2000:
            raise ValueError("Prompt must be less than 2000 characters")
        return v
    
    @validator('initial_message')
    def validate_initial_message(cls, v):
        """Validate initial message length."""
        if v and len(v) > 500:
            raise ValueError("Initial message must be less than 500 characters")
        return v


class VoiceAssistantRequest(BaseModel):
    """Model for voice assistant session requests."""
    
    prompt: Optional[str] = Field(None, description="Custom system prompt for the AI agent")
    language: str = Field("en", description="Language code for the conversation")
    voice_id: Optional[str] = Field(None, description="Voice ID for text-to-speech")
    initial_message: Optional[str] = Field(None, description="Initial message to speak when session starts")
    
    @validator('language')
    def validate_language(cls, v):
        """Validate language code."""
        supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'hi', 'ja', 'ko', 'zh']
        if v not in supported_languages:
            raise ValueError(f"Language must be one of: {', '.join(supported_languages)}")
        return v
