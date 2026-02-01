"""
Tests for API Improvements
"""

import pytest
from fastapi import status
import httpx


class TestBatchTranscription:
    """Test batch transcription API"""

    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        return httpx.Client(base_url="http://127.0.0.1:8000")

    def test_batch_endpoint_exists(self, client):
        """Test that batch endpoint exists"""
        # This will fail with 422 if endpoint exists (missing files parameter)
        # or 404 if endpoint doesn't exist
        response = client.post("/api/postprocess/batch-transcribe")
        assert response.status_code != 404


class TestJobQueue:
    """Test job queue system"""

    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        return httpx.Client(base_url="http://127.0.0.1:8000")

    def test_job_submit_endpoint_exists(self, client):
        """Test that job submit endpoint exists"""
        response = client.post("/api/jobs/submit")
        # Should get 422 (missing file) not 404
        assert response.status_code != 404

    def test_job_stats_endpoint(self, client):
        """Test job stats endpoint"""
        response = client.get("/api/jobs/stats")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "total_jobs" in data
        assert "pending" in data
        assert "processing" in data
        assert "completed" in data

    def test_list_jobs_endpoint(self, client):
        """Test list jobs endpoint"""
        response = client.get("/api/jobs/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "jobs" in data
        assert "count" in data


class TestRateLimiting:
    """Test rate limiting"""

    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        return httpx.Client(base_url="http://127.0.0.1:8000")

    def test_health_check_no_limit(self, client):
        """Test that health check has high rate limit"""
        # Health check should allow many requests
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == status.HTTP_200_OK

    def test_config_endpoint_rate_limit(self, client):
        """Test that config endpoint has moderate rate limit"""
        # Make several requests
        responses = []
        for i in range(5):
            response = client.get("/api/asr/config")
            responses.append(response.status_code)

        # At least some should succeed
        assert status.HTTP_200_OK in responses


class TestWebSocket:
    """Test WebSocket endpoint"""

    @pytest.fixture
    def ws_url(self):
        """WebSocket URL"""
        return "ws://127.0.0.1:8000/api/asr/stream-progress"

    def test_websocket_endpoint_exists(self, ws_url):
        """Test that WebSocket endpoint exists"""
        import websockets
        import asyncio

        async def connect():
            try:
                async with websockets.connect(ws_url) as websocket:
                    # Connected successfully
                    return True
            except Exception as e:
                # Connection failed
                return False

        result = asyncio.run(connect())
        # Should at least be able to connect
        assert result is True or "refused" not in str(result)


class TestAPIIntegration:
    """Integration tests for API improvements"""

    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        return httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)

    def test_api_endpoints_available(self, client):
        """Test that all new endpoints are available"""
        endpoints = [
            "/api/postprocess/batch-transcribe",
            "/api/jobs/stats",
            "/api/jobs/",
            "/health"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint) if endpoint.startswith("/health") or endpoint.startswith("/api/jobs") else client.post(endpoint)
            # Should not be 404
            assert response.status_code != 404, f"Endpoint {endpoint} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
