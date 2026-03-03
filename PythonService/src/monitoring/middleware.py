"""
Monitoring middleware for FastAPI
Integrates metrics collection with API requests
"""

import time
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from src.monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics"""
        start_time = time.time()

        try:
            response = await call_next(request)

            # Record successful request latency
            latency_ms = (time.time() - start_time) * 1000
            path = request.url.path

            # Track specific endpoints
            if "/api/asr/audio/" in path:
                # Audio chunk endpoint - track session timing
                session_id = path.split("/")[-1]
                metrics_collector.record_first_audio(session_id)
            elif path.endswith("/stop"):
                # Stop endpoint
                session_id = path.split("/")[-1]
                metrics_collector.record_session_stop(session_id)

            return response

        except Exception as e:
            # Record failed request
            logger.error(f"Request failed: {e}")
            raise


def start_session_monitoring(session_id: str) -> None:
    """Start monitoring a new ASR session"""
    metrics_collector.start_session_timing(session_id)


def record_preview_generated(session_id: str) -> None:
    """Record when a preview is generated"""
    metrics_collector.record_first_preview(session_id)


def record_session_completed(session_id: str, success: bool) -> None:
    """Record session completion"""
    metrics_collector.record_session_complete(session_id, success)


def record_asr_success(success: bool, error: Optional[str] = None) -> None:
    """Record ASR operation result"""
    metrics_collector.record_availability("asr", success, error)


def start_processing(session_id: str) -> None:
    """Start timing audio processing"""
    metrics_collector.start_processing(session_id)


def end_processing(session_id: str, samples: int) -> None:
    """End timing and record throughput"""
    metrics_collector.end_processing(session_id, samples)
