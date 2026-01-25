"""
Tests for ASR service
Following TDD principles - write tests first
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_server_starts(client):
    """Test that the server starts and responds"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["status"] == "running"


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
