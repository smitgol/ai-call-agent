"""Application settings and configuration management."""

from pydantic import BaseSettings, Field, validator
from typing import List, Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # API Configuration
    api_title: str = "AI Call Agent API"
    api_version: str = "1.0.0"
    api_description: str = "A sophisticated AI-powered voice call agent platform"
    
    # Server Configuration
    server_host: str = Field("0.0.0.0", env="HOST")
    server_port: int = Field(5000, env="PORT")
    server_domain: str = Field(..., env="SERVER")
    prod_server_domain: str = Field(..., env="PROD_SERVER")
    
    # Security
    allowed_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"], 
        env="ALLOWED_ORIGINS"
    )
    api_key_header: str = Field("X-API-Key", env="API_KEY_HEADER")
    
    # Database
    mongo_db_url: str = Field(..., env="MONGO_DB_URL")
    database_name: str = Field("ai_call_agent", env="DATABASE_NAME")
    
    # AI Service API Keys
    deepgram_api_key: str = Field(..., env="DEEPGRAM_API_KEY")
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    elevenlabs_api_key: str = Field(..., env="ELEVENLABS_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    assembly_api_key: str = Field(..., env="ASSEMBLY_API_KEY")
    gladia_api_key: str = Field(..., env="GLADIA_API_KEY")
    cartesia_api_key: Optional[str] = Field(None, env="CARTESIA_API_KEY")
    gemini_api_key: Optional[str] = Field(None, env="GEMMINI_API_KEY")
    
    # Telephony
    twilio_account_sid: str = Field(..., env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., env="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(..., env="FROM_NUMBER")
    
    # Exotel (Optional)
    exotel_account_sid: Optional[str] = Field(None, env="EXOTEL_ACCOUNT_SID")
    exotel_auth_key: Optional[str] = Field(None, env="EXOTEL_AUTH_KEY")
    exotel_auth_token: Optional[str] = Field(None, env="EXOTEL_AUTH_TOKEN")
    exotel_from_number: Optional[str] = Field(None, env="EXOTEL_FROM_NUMBER")
    exotel_app_id: Optional[str] = Field(None, env="EXOTEL_APP_ID")
    
    # Monitoring
    sentry_dsn: str = Field(..., env="SENTRY_SDK_URL")
    koala_access_key: str = Field(..., env="KOALA_ACCESS_KEY")
    
    # AI Configuration
    llm_model: str = Field("meta-llama/llama-4-scout-17b-16e-instruct", env="LLM_MODEL")
    tts_voice_id: str = Field("c6SfcYrb2t09NHXiT80T", env="TTS_VOICE_ID")
    default_language: str = Field("en", env="DEFAULT_LANGUAGE")
    
    # Rate Limiting
    rate_limit_calls_per_minute: int = Field(60, env="RATE_LIMIT_CALLS_PER_MINUTE")
    rate_limit_calls_per_hour: int = Field(1000, env="RATE_LIMIT_CALLS_PER_HOUR")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("app.log", env="LOG_FILE")
    
    @validator('allowed_origins', pre=True)
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ['development', 'staging', 'production', 'test']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
