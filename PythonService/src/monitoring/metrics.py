"""
Metrics collection for Typeless monitoring
Collects latency and availability metrics
"""

import time
import threading
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Latency metrics for a specific operation"""
    operation: str  # e.g., "audio_to_preview", "stop_to_result"
    timestamps: deque = field(default_factory=lambda: deque(maxlen=100))
    values: deque = field(default_factory=lambda: deque(maxlen=100))

    def record(self, latency_ms: float) -> None:
        """Record a latency measurement"""
        self.timestamps.append(time.time())
        self.values.append(latency_ms)

    def get_stats(self, window_seconds: int = 300) -> Dict:
        """Get latency statistics for recent window"""
        cutoff = time.time() - window_seconds
        recent_values = [
            v for t, v in zip(self.timestamps, self.values)
            if t >= cutoff
        ]

        if not recent_values:
            return {"count": 0, "avg_ms": 0, "p95_ms": 0, "p99_ms": 0, "max_ms": 0}

        sorted_values = sorted(recent_values)
        n = len(sorted_values)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)

        return {
            "count": n,
            "avg_ms": sum(recent_values) / n,
            "p95_ms": sorted_values[min(p95_idx, n - 1)],
            "p99_ms": sorted_values[min(p99_idx, n - 1)],
            "max_ms": max(recent_values)
        }


@dataclass
class AvailabilityMetrics:
    """Availability metrics for a specific operation"""
    operation: str  # e.g., "recording", "asr"
    total: int = 0
    success: int = 0
    failures: deque = field(default_factory=lambda: deque(maxlen=50))

    def record(self, success: bool, error: Optional[str] = None) -> None:
        """Record an operation result"""
        self.total += 1
        if success:
            self.success += 1
        elif error:
            self.failures.append({"time": time.time(), "error": error})

    def get_stats(self) -> Dict:
        """Get availability statistics"""
        if self.total == 0:
            return {"total": 0, "success": 0, "success_rate": 1.0, "recent_failures": []}

        # Get recent failures (last 10)
        recent_failures = [
            f for f in self.failures
            if f["time"] >= time.time() - 3600  # Last hour
        ]

        return {
            "total": self.total,
            "success": self.success,
            "success_rate": self.success / self.total,
            "recent_failures": recent_failures[-10:]
        }


class MetricsCollector:
    """Central metrics collector for Typeless monitoring"""

    def __init__(self):
        self._lock = threading.RLock()
        self._latency_metrics: Dict[str, LatencyMetrics] = {}
        self._availability_metrics: Dict[str, AvailabilityMetrics] = {}
        self._session_timings: Dict[str, Dict] = {}  # For tracking session lifecycle

    def start_session_timing(self, session_id: str) -> None:
        """Start timing a new session"""
        with self._lock:
            self._session_timings[session_id] = {
                "start_time": time.time(),
                "first_audio_time": None,
                "first_preview_time": None,
                "stop_time": None
            }

    def record_first_audio(self, session_id: str) -> None:
        """Record when first audio chunk is received"""
        with self._lock:
            if session_id in self._session_timings:
                self._session_timings[session_id]["first_audio_time"] = time.time()

    def record_first_preview(self, session_id: str) -> None:
        """Record when first preview is generated"""
        with self._lock:
            if session_id in self._session_timings:
                timing = self._session_timings[session_id]
                timing["first_preview_time"] = time.time()

                # Calculate audio_to_preview latency
                if timing.get("first_audio_time"):
                    latency_ms = (timing["first_preview_time"] - timing["first_audio_time"]) * 1000
                    self.record_latency("audio_to_preview", latency_ms)

    def record_session_stop(self, session_id: str) -> None:
        """Record when session stops"""
        with self._lock:
            if session_id in self._session_timings:
                timing = self._session_timings[session_id]
                timing["stop_time"] = time.time()

                # Calculate stop_to_result latency (approximate)
                if timing.get("start_time"):
                    # This will be updated when result is ready
                    pass

    def record_session_complete(self, session_id: str, success: bool) -> None:
        """Record session completion with result"""
        with self._lock:
            if session_id in self._session_timings:
                timing = self._session_timings[session_id]
                complete_time = time.time()

                # Calculate stop_to_result latency
                if timing.get("stop_time"):
                    latency_ms = (complete_time - timing["stop_time"]) * 1000
                    self.record_latency("stop_to_result", latency_ms)

                # Clean up session timing
                del self._session_timings[session_id]

                # Record availability
                self.record_availability("recording", success)

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record a latency measurement"""
        with self._lock:
            if operation not in self._latency_metrics:
                self._latency_metrics[operation] = LatencyMetrics(operation=operation)
            self._latency_metrics[operation].record(latency_ms)

    def record_availability(self, operation: str, success: bool, error: Optional[str] = None) -> None:
        """Record an availability measurement"""
        with self._lock:
            if operation not in self._availability_metrics:
                self._availability_metrics[operation] = AvailabilityMetrics(operation=operation)
            self._availability_metrics[operation].record(success, error)

    def get_latency_report(self, operation: Optional[str] = None) -> Dict:
        """Get latency report for all or specific operation"""
        with self._lock:
            if operation:
                if operation in self._latency_metrics:
                    return {operation: self._latency_metrics[operation].get_stats()}
                return {}

            return {
                op: metrics.get_stats()
                for op, metrics in self._latency_metrics.items()
            }

    def get_availability_report(self, operation: Optional[str] = None) -> Dict:
        """Get availability report for all or specific operation"""
        with self._lock:
            if operation:
                if operation in self._availability_metrics:
                    return {operation: self._availability_metrics[operation].get_stats()}
                return {}

            return {
                op: metrics.get_stats()
                for op, metrics in self._availability_metrics.items()
            }

    def get_full_report(self) -> Dict:
        """Get full monitoring report"""
        return {
            "latency": self.get_latency_report(),
            "availability": self.get_availability_report(),
            "timestamp": time.time()
        }

    def check_alerts(self) -> list:
        """Check for alert conditions"""
        alerts = []

        # Check latency alerts
        latency_report = self.get_latency_report()
        thresholds = {
            "audio_to_preview": 2000,  # 2 seconds
            "stop_to_result": 5000     # 5 seconds
        }

        for operation, stats in latency_report.items():
            if operation in thresholds and stats["count"] > 0:
                if stats["p95_ms"] > thresholds[operation]:
                    alerts.append({
                        "severity": "warning",
                        "type": "latency",
                        "operation": operation,
                        "message": f"{operation} p95 latency {stats['p95_ms']:.0f}ms exceeds threshold {thresholds[operation]}ms"
                    })

        # Check availability alerts
        availability_report = self.get_availability_report()
        availability_thresholds = {
            "recording": 0.95,  # 95%
            "asr": 0.90         # 90%
        }

        for operation, stats in availability_report.items():
            if operation in availability_thresholds and stats["total"] > 10:
                if stats["success_rate"] < availability_thresholds[operation]:
                    alerts.append({
                        "severity": "critical",
                        "type": "availability",
                        "operation": operation,
                        "message": f"{operation} success rate {stats['success_rate']*100:.1f}% below threshold {availability_thresholds[operation]*100:.1f}%"
                    })

        return alerts


# Global metrics collector instance
metrics_collector = MetricsCollector()
