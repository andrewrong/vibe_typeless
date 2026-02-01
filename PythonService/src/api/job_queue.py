"""
Job Queue System for Long-Running Tasks
Async processing of long audio files with status tracking
"""

import uuid
import asyncio
from typing import Dict, Optional, List, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job:
    """Represents a single job in the queue"""

    def __init__(
        self,
        job_id: str,
        task: Callable,
        args: tuple = (),
        kwargs: dict = None,
        metadata: dict = None
    ):
        self.job_id = job_id
        self.task = task
        self.args = args
        self.kwargs = kwargs or {}
        self.metadata = metadata or {}

        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        self.result = None
        self.error: Optional[str] = None
        self.progress: float = 0.0  # 0.0 to 1.0
        self.progress_message: str = ""

    async def run(self):
        """Execute the job task"""
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now()

        try:
            # Run the task
            if asyncio.iscoroutinefunction(self.task):
                self.result = await self.task(*self.args, **self.kwargs)
            else:
                # Run in thread pool for blocking tasks
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as pool:
                    self.result = await loop.run_in_executor(
                        pool,
                        lambda: self.task(*self.args, **self.kwargs)
                    )

            self.status = JobStatus.COMPLETED
            self.progress = 1.0

        except Exception as e:
            self.status = JobStatus.FAILED
            self.error = str(e)

        finally:
            self.completed_at = datetime.now()

    def cancel(self):
        """Cancel the job"""
        if self.status == JobStatus.PENDING:
            self.status = JobStatus.CANCELLED
            self.completed_at = datetime.now()
            return True
        return False

    def update_progress(self, progress: float, message: str = ""):
        """Update job progress"""
        self.progress = max(0.0, min(1.0, progress))
        self.progress_message = message


class JobInfo(BaseModel):
    """Job information for API responses"""
    job_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float
    progress_message: str
    result: Optional[dict] = None
    error: Optional[str] = None
    metadata: dict

    @classmethod
    def from_job(cls, job: Job) -> "JobInfo":
        """Create JobInfo from Job instance"""
        return cls(
            job_id=job.job_id,
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            progress=job.progress,
            progress_message=job.progress_message,
            result=job.result if isinstance(job.result, dict) else None,
            error=job.error,
            metadata=job.metadata
        )


class JobQueue:
    """Async job queue for processing long-running tasks"""

    def __init__(self, max_concurrent_jobs: int = 3):
        self.jobs: Dict[str, Job] = {}
        self.max_concurrent_jobs = max_concurrent_jobs
        self.processing_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.worker_task: Optional[asyncio.Task] = None

    async def submit(
        self,
        task: Callable,
        args: tuple = (),
        kwargs: dict = None,
        metadata: dict = None
    ) -> str:
        """
        Submit a job to the queue

        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            task=task,
            args=args,
            kwargs=kwargs,
            metadata=metadata or {}
        )

        self.jobs[job_id] = job

        # Start processing the job
        asyncio.create_task(self._process_job(job))

        return job_id

    async def _process_job(self, job: Job):
        """Process a job with concurrency control"""
        async with self.processing_semaphore:
            await job.run()

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        job = self.get_job(job_id)
        if job:
            return job.cancel()
        return False

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Job]:
        """List all jobs, optionally filtered by status"""
        jobs = list(self.jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def get_stats(self) -> dict:
        """Get queue statistics"""
        jobs = list(self.jobs.values())

        stats = {
            "total_jobs": len(jobs),
            "pending": sum(1 for j in jobs if j.status == JobStatus.PENDING),
            "processing": sum(1 for j in jobs if j.status == JobStatus.PROCESSING),
            "completed": sum(1 for j in jobs if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in jobs if j.status == JobStatus.FAILED),
            "cancelled": sum(1 for j in jobs if j.status == JobStatus.CANCELLED),
            "max_concurrent_jobs": self.max_concurrent_jobs
        }

        return stats

    def cleanup_old_jobs(self, max_age_hours: int = 24, keep_completed: int = 100):
        """
        Clean up old completed/failed jobs

        Args:
            max_age_hours: Remove jobs older than this
            keep_completed: Keep this many completed jobs regardless of age
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        # Get completed/failed jobs older than cutoff
        old_jobs = [
            j for j in self.jobs.values()
            if j.status in [JobStatus.COMPLETED, JobStatus.FAILED]
            and j.completed_at
            and j.completed_at < cutoff
        ]

        # Sort by completion time (newest first)
        old_jobs.sort(key=lambda j: j.completed_at, reverse=True)

        # Keep the most recent ones
        to_remove = old_jobs[keep_completed:]

        for job in to_remove:
            del self.jobs[job.job_id]

        return len(to_remove)


# Global job queue instance
job_queue = JobQueue(max_concurrent_jobs=3)


# Background task to periodically clean up old jobs
async def cleanup_task():
    """Periodically clean up old jobs"""
    import asyncio

    while True:
        await asyncio.sleep(3600)  # Run every hour
        removed = job_queue.cleanup_old_jobs()
        if removed > 0:
            print(f"Cleaned up {removed} old jobs")
