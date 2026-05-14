"""Custom exceptions for the application."""

from typing import Optional, Any


class AICallAgentException(Exception):
    """Base exception for AI Call Agent application."""
    
    def __init__(self, message: str, error_code: str = None, details: Any = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details
        super().__init__(self.message)


class ValidationError(AICallAgentException):
    """Raised when input validation fails."""
    pass


class TwilioAPIError(AICallAgentException):
    """Raised when Twilio API calls fail."""
    pass


class ExotelAPIError(AICallAgentException):
    """Raised when Exotel API calls fail."""
    pass


class DatabaseError(AICallAgentException):
    """Raised when database operations fail."""
    pass


class LLMServiceError(AICallAgentException):
    """Raised when LLM service operations fail."""
    pass


class TTSServiceError(AICallAgentException):
    """Raised when TTS service operations fail."""
    pass


class STTServiceError(AICallAgentException):
    """Raised when STT service operations fail."""
    pass


class ConfigurationError(AICallAgentException):
    """Raised when configuration is invalid."""
    pass


class RateLimitError(AICallAgentException):
    """Raised when rate limits are exceeded."""
    pass


class AuthenticationError(AICallAgentException):
    """Raised when authentication fails."""
    pass
