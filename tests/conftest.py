"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Set test environment variables
os.environ.update({
    "DEEPGRAM_API_KEY": "test_key",
    "GROQ_API_KEY": "test_key", 
    "ELEVENLABS_API_KEY": "test_key",
    "TWILIO_ACCOUNT_SID": "test_sid",
    "TWILIO_AUTH_TOKEN": "test_token",
    "FROM_NUMBER": "+1234567890",
    "SERVER": "test.example.com",
    "MONGO_DB_URL": "mongodb://test:27017",
    "SENTRY_SDK_URL": "https://test@sentry.io/123",
    "KOALA_ACCESS_KEY": "test_key"
})

@pytest.fixture
def client():
    """Create test client."""
    from main import app
    return TestClient(app)

@pytest.fixture
async def mock_db():
    """Mock database for testing."""
    mock_db = MagicMock()
    mock_db.call_configs = AsyncMock()
    mock_db.call_transcriptions = AsyncMock()
    
    with patch('utils.getDb', return_value=mock_db):
        yield mock_db

@pytest.fixture
def mock_twilio_client():
    """Mock Twilio client."""
    mock_client = MagicMock()
    mock_client.calls.create.return_value = MagicMock(sid="test_call_sid")
    
    with patch('utils.get_twilio_client', return_value=mock_client):
        yield mock_client

@pytest.fixture
def sample_call_request():
    """Sample call request data."""
    return {
        "to_number": "+1234567890",
        "prompt": "Test prompt",
        "language": "en",
        "voice_id": "test_voice_id",
        "initial_message": "Hello, this is a test"
    }
