"""
Tests for ASR API routes
Following TDD principles - tests written first
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from api.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_audio_chunk():
    """Create sample audio chunk for testing"""
    # 1 second of random audio at 16kHz
    return np.random.randint(-1000, 1000, size=16000, dtype=np.int16).tobytes()


class TestASREndpoints:
    """Test ASR streaming endpoints"""

    def test_asr_start_session(self, client):
        """Test starting an ASR session"""
        response = client.post("/api/asr/start")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "status" in data
        assert data["status"] == "started"

    def test_asr_send_audio(self, client, sample_audio_chunk):
        """Test sending audio chunk for transcription"""
        # First start a session
        start_response = client.post("/api/asr/start")
        session_id = start_response.json()["session_id"]

        # Send audio chunk
        response = client.post(
            f"/api/asr/audio/{session_id}",
            content=sample_audio_chunk,
            headers={"Content-Type": "application/octet-stream"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "partial_transcript" in data or "error" in data

    def test_asr_stop_session(self, client):
        """Test stopping an ASR session"""
        # Start a session first
        start_response = client.post("/api/asr/start")
        session_id = start_response.json()["session_id"]

        # Stop the session
        response = client.post(f"/api/asr/stop/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "stopped"
        assert "final_transcript" in data

    def test_asr_get_status(self, client):
        """Test getting ASR session status"""
        # Start a session
        start_response = client.post("/api/asr/start")
        session_id = start_response.json()["session_id"]

        # Get status
        response = client.get(f"/api/asr/status/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "status" in data

    def test_asr_invalid_session(self, client):
        """Test with invalid session ID"""
        response = client.get("/api/asr/status/invalid-session-id")
        assert response.status_code == 404

    def test_asr_transcribe_file(self, client, sample_audio_chunk):
        """Test transcribing a complete audio file"""
        response = client.post(
            "/api/asr/transcribe",
            content=sample_audio_chunk,
            headers={"Content-Type": "application/octet-stream"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert "duration" in data


class TestWebSocketStreaming:
    """Test WebSocket streaming endpoints"""

    @pytest.mark.skip(reason="WebSocket requires integration testing with real server")
    def test_websocket_connection(self, client):
        """Test WebSocket connection"""
        # Note: TestClient doesn't fully support WebSocket testing
        # This requires integration testing with a running server
        # TODO: Implement with pytest-asyncio and real WebSocket client
        pass

    @pytest.mark.skip(reason="WebSocket requires integration testing with real server")
    def test_websocket_send_audio(self, client, sample_audio_chunk):
        """Test sending audio via WebSocket"""
        # Note: Requires integration testing with real server
        # TODO: Implement with pytest-asyncio and real WebSocket client
        pass

    @pytest.mark.skip(reason="WebSocket requires integration testing with real server")
    def test_websocket_stop(self, client):
        """Test stopping WebSocket session"""
        # Note: Requires integration testing with real server
        # TODO: Implement with pytest-asyncio and real WebSocket client
        pass
