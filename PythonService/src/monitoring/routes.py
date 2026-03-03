"""
Monitoring API routes
Provides endpoints for metrics and health checks
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

from src.monitoring.metrics import metrics_collector

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


class LatencyReport(BaseModel):
    """Latency metrics report"""
    count: int
    avg_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float


class AvailabilityReport(BaseModel):
    """Availability metrics report"""
    total: int
    success: int
    success_rate: float


class FullReport(BaseModel):
    """Full monitoring report"""
    latency: Dict[str, LatencyReport]
    availability: Dict[str, AvailabilityReport]
    alerts: List[dict]
    timestamp: float


@router.get("/metrics/latency")
async def get_latency_metrics():
    """
    Get latency metrics for all operations

    Returns:
        Latency metrics by operation
    """
    return metrics_collector.get_latency_report()


@router.get("/metrics/availability")
async def get_availability_metrics():
    """
    Get availability metrics for all operations

    Returns:
        Availability metrics by operation
    """
    return metrics_collector.get_availability_report()


@router.get("/metrics", response_model=FullReport)
async def get_full_metrics():
    """
    Get full monitoring report including alerts

    Returns:
        Complete monitoring report
    """
    report = metrics_collector.get_full_report()
    report["alerts"] = metrics_collector.check_alerts()
    return report


@router.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        Service health status
    """
    alerts = metrics_collector.check_alerts()
    critical_alerts = [a for a in alerts if a["severity"] == "critical"]

    if critical_alerts:
        return {
            "status": "degraded",
            "alerts": critical_alerts
        }

    return {
        "status": "healthy",
        "alerts": []
    }
