"""Test API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
import json


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"Status": "Working"}


class TestCallEndpoints:
    """Test call-related endpoints."""
    
    @patch('main.uuid4')
    def test_start_call_success(self, mock_uuid, client, mock_db, mock_twilio_client, sample_call_request):
        """Test successful call initiation."""
        mock_uuid.return_value = "test-session-id"
        mock_db.call_configs.insert_one.return_value = AsyncMock()
        
        response = client.post("/start_call", json=sample_call_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Call initiated"
        
        # Verify database call
        mock_db.call_configs.insert_one.assert_called_once()
        
        # Verify Twilio call
        mock_twilio_client.calls.create.assert_called_once()
    
    def test_start_call_missing_number(self, client):
        """Test call initiation with missing phone number."""
        request_data = {
            "prompt": "Test prompt",
            "language": "en"
        }
        
        response = client.post("/start_call", json=request_data)
        # Should handle gracefully - current implementation doesn't validate
        # This test documents current behavior
        assert response.status_code in [200, 400, 422]
    
    @patch('main.uuid4')
    def test_start_call_exotel_success(self, mock_uuid, client, mock_db, sample_call_request):
        """Test successful Exotel call initiation."""
        mock_uuid.return_value = "test-session-id"
        mock_db.call_configs.insert_one.return_value = AsyncMock()
        
        with patch('utils.call_exotel_api', return_value=200):
            response = client.post("/start_call_exotel", json=sample_call_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    @patch('main.uuid4')
    def test_create_voice_assistant_session(self, mock_uuid, client, mock_db, sample_call_request):
        """Test voice assistant session creation."""
        mock_uuid.return_value = "test-session-id"
        mock_db.call_configs.insert_one.return_value = AsyncMock()
        
        response = client.post("/create_voice_assistant_session", json=sample_call_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "ws_url" in data
        assert "test-session-id" in data["ws_url"]


class TestErrorHandling:
    """Test error handling in endpoints."""
    
    @patch('main.uuid4')
    def test_start_call_database_error(self, mock_uuid, client, mock_db, sample_call_request):
        """Test handling of database errors."""
        mock_uuid.return_value = "test-session-id"
        mock_db.call_configs.insert_one.side_effect = Exception("Database error")
        
        response = client.post("/start_call", json=sample_call_request)
        
        assert response.status_code == 200  # Current implementation returns 200 even on error
        data = response.json()
        assert data["status"] == "failed"
    
    @patch('main.uuid4')
    def test_start_call_twilio_error(self, mock_uuid, client, mock_db, mock_twilio_client, sample_call_request):
        """Test handling of Twilio API errors."""
        mock_uuid.return_value = "test-session-id"
        mock_db.call_configs.insert_one.return_value = AsyncMock()
        mock_twilio_client.calls.create.side_effect = Exception("Twilio API error")
        
        response = client.post("/start_call", json=sample_call_request)
        
        assert response.status_code == 200  # Current implementation
        data = response.json()
        assert data["status"] == "failed"
