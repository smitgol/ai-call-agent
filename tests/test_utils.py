"""Test utility functions."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from utils import get_twilio_client, text_chunker


class TestTwilioClient:
    """Test Twilio client utilities."""
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token'
    })
    @patch('utils.Client')
    def test_get_twilio_client(self, mock_client):
        """Test Twilio client creation."""
        client = get_twilio_client()
        
        mock_client.assert_called_once_with('test_sid', 'test_token')


class TestTextChunker:
    """Test text chunking utility."""
    
    @pytest.mark.asyncio
    async def test_text_chunker_basic(self):
        """Test basic text chunking functionality."""
        # Mock LLM service
        mock_llm_service = MagicMock()
        mock_llm_service.trigger_tool = AsyncMock()
        
        # Mock chunks generator
        async def mock_chunks():
            mock_choice = MagicMock()
            mock_choice.delta.content = "Hello, "
            mock_choice.delta.tool_calls = None
            yield MagicMock(choices=[mock_choice])
            
            mock_choice.delta.content = "world!"
            yield MagicMock(choices=[mock_choice])
        
        chunks = []
        async for chunk in text_chunker(mock_chunks(), mock_llm_service):
            chunks.append(chunk)
        
        assert len(chunks) >= 1
        assert any("Hello" in chunk for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_text_chunker_with_tool_calls(self):
        """Test text chunker with tool calls."""
        mock_llm_service = MagicMock()
        mock_llm_service.trigger_tool = AsyncMock()
        
        # Mock chunks with tool calls
        async def mock_chunks():
            mock_choice = MagicMock()
            mock_choice.delta.content = "Hello"
            
            # Mock tool call
            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "end_call"
            mock_choice.delta.tool_calls = [mock_tool_call]
            
            yield MagicMock(choices=[mock_choice])
        
        chunks = []
        async for chunk in text_chunker(mock_chunks(), mock_llm_service):
            chunks.append(chunk)
        
        # Verify tool was triggered
        mock_llm_service.trigger_tool.assert_called_once_with("end_call")
