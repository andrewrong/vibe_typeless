# API Improvements Documentation

## Overview

This document describes the major API improvements added to the Typeless ASR service, including WebSocket streaming with progress updates, batch transcription, job queue system, rate limiting, and authentication.

---

## 1. WebSocket Streaming with Progress Updates

### Endpoint: `WS /api/asr/stream-progress`

Enhanced WebSocket endpoint that provides real-time progress updates during long audio processing.

### Protocol

#### Client Messages

**Start Session**
```json
{
  "action": "start"
}
```

**Send Audio Chunk**
```python
# Send binary audio data (16kHz, 16-bit, mono)
await websocket.send(audio_bytes)
```

**Process Accumulated Audio**
```json
{
  "action": "process",
  "strategy": "hybrid",
  "merge_strategy": "simple",
  "apply_postprocess": true
}
```

**Stop Session**
```json
{
  "action": "stop"
}
```

#### Server Messages

**Session Started**
```json
{
  "type": "started",
  "session_id": "uuid",
  "timestamp": "2025-01-26T10:00:00"
}
```

**Ready for Audio**
```json
{
  "type": "ready",
  "message": "Ready to receive audio chunks",
  "session_id": "uuid"
}
```

**Chunk Received**
```json
{
  "type": "chunk_received",
  "chunk_number": 5,
  "session_id": "uuid"
}
```

**Progress Update**
```json
{
  "type": "progress",
  "current_segment": 2,
  "total_segments": 4,
  "progress_percent": 50.0,
  "message": "Processing segment 2/4 (28.5s)...",
  "session_id": "uuid"
}
```

**Segment Complete**
```json
{
  "type": "segment_complete",
  "current_segment": 2,
  "total_segments": 4,
  "transcript_part": "This is the transcript for segment 2...",
  "session_id": "uuid"
}
```

**Complete**
```json
{
  "type": "complete",
  "session_id": "uuid",
  "final_transcript": "Full transcript...",
  "processed_transcript": "Cleaned transcript...",
  "total_segments": 4,
  "duration": 120.5,
  "strategy": "hybrid",
  "merge_strategy": "simple"
}
```

**Error**
```json
{
  "type": "error",
  "message": "Error description",
  "session_id": "uuid"
}
```

### Example Usage

```python
import websockets
import json
import asyncio

async def transcribe_with_progress(audio_file_path):
    uri = "ws://127.0.0.1:8000/api/asr/stream-progress"

    async with websockets.connect(uri) as websocket:
        # Start session
        await websocket.send(json.dumps({"action": "start"}))

        # Receive ready confirmation
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Server: {data['message']}")

        # Send audio in chunks
        with open(audio_file_path, "rb") as f:
            while True:
                chunk = f.read(32000)  # 2 seconds at 16kHz
                if not chunk:
                    break
                await websocket.send(chunk)

                # Get acknowledgment
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Chunk {data['chunk_number']} received")

        # Request processing
        await websocket.send(json.dumps({
            "action": "process",
            "strategy": "hybrid",
            "apply_postprocess": True
        }))

        # Receive progress updates
        while True:
            response = await websocket.recv()
            data = json.loads(response)

            if data['type'] == 'progress':
                print(f"{data['progress_percent']:.0f}% - {data['message']}")
            elif data['type'] == 'segment_complete':
                print(f"Segment {data['current_segment']}/{data['total_segments']} complete")
            elif data['type'] == 'complete':
                print("Processing complete!")
                return data['final_transcript']
```

---

## 2. Batch Transcription API

### Endpoint: `POST /api/postprocess/batch-transcribe`

Process multiple audio files in a single request.

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| files | List[UploadFile] | Yes | - | List of audio files to process |
| apply_postprocess | boolean | No | true | Whether to apply text post-processing |
| strategy | string | No | "auto" | "auto", "short", or "long" |

### Response

```json
{
  "total_files": 3,
  "successful": 2,
  "failed": 1,
  "total_duration": 45.0,
  "processing_time": 5.2,
  "results": [
    {
      "filename": "file1.wav",
      "success": true,
      "transcript": "Transcript text...",
      "processed_transcript": "Cleaned text...",
      "duration": 15.0,
      "error": null
    },
    {
      "filename": "file2.mp3",
      "success": true,
      "transcript": "Another transcript...",
      "processed_transcript": null,
      "duration": 20.0,
      "error": null
    },
    {
      "filename": "corrupted.wav",
      "success": false,
      "transcript": null,
      "processed_transcript": null,
      "duration": null,
      "error": "Unsupported format or corrupted file"
    }
  ]
}
```

### Example Usage

**Python**
```python
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=300)

# Prepare files
files = [
    ("files", ("audio1.wav", open("audio1.wav", "rb"), "audio/wav")),
    ("files", ("audio2.mp3", open("audio2.mp3", "rb"), "audio/mpeg")),
    ("files", ("audio3.wav", open("audio3.wav", "rb"), "audio/wav"))
]

response = client.post(
    "/api/postprocess/batch-transcribe",
    files=files,
    params={"apply_postprocess": "true", "strategy": "auto"}
)

result = response.json()
print(f"Processed {result['total_files']} files")
print(f"Successful: {result['successful']}")
print(f"Failed: {result['failed']}")

for item in result['results']:
    if item['success']:
        print(f"{item['filename']}: {item['transcript'][:50]}...")
```

**cURL**
```bash
curl -X POST http://127.0.0.1:8000/api/postprocess/batch-transcribe \
  -F "files=@audio1.wav" \
  -F "files=@audio2.mp3" \
  -F "files=@audio3.wav" \
  -F "apply_postprocess=true" \
  -F "strategy=auto"
```

---

## 3. Job Queue System

### Submit Job

**Endpoint:** `POST /api/jobs/submit`

Submit a long-running transcription job to the queue.

**Request Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file | UploadFile | Yes | - | Audio file to transcribe |
| strategy | string | No | "hybrid" | Chunking strategy |
| merge_strategy | string | No | "simple" | Merge strategy |
| apply_postprocess | boolean | No | true | Apply post-processing |

**Response:**
```json
{
  "job_id": "uuid",
  "status": "submitted",
  "message": "Job submitted successfully. Use GET /api/jobs/{job_id} to check status."
}
```

### Get Job Status

**Endpoint:** `GET /api/jobs/{job_id}`

Get the status and results of a job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "created_at": "2025-01-26T10:00:00",
  "started_at": "2025-01-26T10:00:05",
  "completed_at": "2025-01-26T10:02:30",
  "progress": 1.0,
  "progress_message": "",
  "result": {
    "transcript": "Full transcript...",
    "processed_transcript": "Cleaned transcript...",
    "metadata": {
      "duration": 120.0,
      "num_segments": 4
    }
  },
  "error": null,
  "metadata": {
    "filename": "audio.wav",
    "strategy": "hybrid"
  }
}
```

**Status Values:**
- `pending`: Job is queued, waiting to start
- `processing`: Job is currently running
- `completed`: Job finished successfully
- `failed`: Job failed with error
- `cancelled`: Job was cancelled

### Cancel Job

**Endpoint:** `POST /api/jobs/{job_id}/cancel`

Cancel a pending job.

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled successfully"
}
```

### List Jobs

**Endpoint:** `GET /api/jobs/`

List all jobs, optionally filtered by status.

**Query Parameters:**
- `status`: Filter by status (pending, processing, completed, failed, cancelled)
- `limit`: Maximum number of jobs to return (default: 100)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "uuid-1",
      "status": "completed",
      "progress": 1.0,
      ...
    },
    {
      "job_id": "uuid-2",
      "status": "processing",
      "progress": 0.5,
      ...
    }
  ],
  "count": 2
}
```

### Get Queue Statistics

**Endpoint:** `GET /api/jobs/stats`

Get queue statistics.

**Response:**
```json
{
  "total_jobs": 150,
  "pending": 5,
  "processing": 3,
  "completed": 140,
  "failed": 2,
  "cancelled": 0,
  "max_concurrent_jobs": 3
}
```

### Example Usage

```python
import httpx
import time

client = httpx.Client(base_url="http://127.0.0.1:8000")

# Submit job
with open("long_audio.wav", "rb") as f:
    response = client.post(
        "/api/jobs/submit",
        files={"file": f},
        params={"strategy": "hybrid"}
    )

job_info = response.json()
job_id = job_info['job_id']
print(f"Job submitted: {job_id}")

# Poll for status
while True:
    response = client.get(f"/api/jobs/{job_id}")
    status = response.json()

    print(f"Status: {status['status']} | Progress: {status['progress'] * 100:.0f}%")

    if status['status'] in ['completed', 'failed', 'cancelled']:
        if status['status'] == 'completed':
            result = status['result']
            print(f"Transcript: {result['transcript']}")
        break

    time.sleep(5)
```

---

## 4. Rate Limiting

### Overview

The API implements rate limiting to prevent abuse and ensure fair usage. Different endpoints have different rate limits based on their resource consumption.

### Rate Limits by Endpoint

| Endpoint Pattern | Rate Limit | Description |
|-----------------|------------|-------------|
| `/api/asr/transcribe` | 10/minute | Single file transcription |
| `/api/postprocess/upload` | 10/minute | Audio upload |
| `/api/postprocess/upload-long` | 5/minute | Long audio processing |
| `/api/postprocess/batch-transcribe` | 3/minute | Batch transcription |
| `/api/asr/config` | 60/minute | Configuration |
| `/api/asr/models` | 60/minute | Model information |
| `/api/postprocess/text` | 30/minute | Text post-processing |
| `/api/asr/start`, `/api/asr/stop` | 20/minute | Session management |
| `/health`, `/status` | 1000/minute | Health checks |
| WebSocket endpoints | None | No rate limiting |

### Rate Limit Response

When rate limit is exceeded:

**Status Code:** `429 Too Many Requests`

**Response:**
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Limit: 10/minute",
  "retry_after": 45
}
```

**Headers:**
```
Retry-After: 45
```

### Configuration

Rate limiting is configured in `src/api/rate_limit.py`:

```python
# Default rate limit
default_limits = ["200/minute"]

# Endpoint-specific limits
endpoint_limits = {
    "transcribe": "10/minute",
    "upload-long": "5/minute",
    # ...
}
```

To disable rate limiting (not recommended for production):

```python
# In server.py
limiter.enabled = False
```

---

## 5. Authentication (Optional)

### Overview

API key authentication is available but optional by default. When enabled, clients must provide a valid API key via the `X-API-Key` header.

### Configuration

Set environment variables:

```bash
# Enable authentication
export TYPELESS_AUTH_ENABLED=true

# Require authentication for all endpoints
export TYPELESS_REQUIRE_AUTH=true

# Set valid API keys (comma-separated)
export TYPELESS_API_KEYS=key1,key2,key3

# Set admin keys (can manage other keys)
export TYPELESS_ADMIN_KEYS=admin-key-1,admin-key-2
```

### Using API Keys

**With cURL:**
```bash
curl -H "X-API-Key: your-api-key" \
  http://127.0.0.1:8000/api/asr/config
```

**With Python:**
```python
import httpx

client = httpx.Client(
    base_url="http://127.0.0.1:8000",
    headers={"X-API-Key": "your-api-key"}
)

response = client.get("/api/asr/config")
```

### Error Responses

**Missing API Key:**
```json
{
  "detail": "API key is missing. Please provide X-API-Key header."
}
```
Status: `401 Unauthorized`

**Invalid API Key:**
```json
{
  "detail": "Invalid API key"
}
```
Status: `403 Forbidden`

---

## Performance Considerations

### Batch Transcription

- **Best for:** Processing 2-10 files simultaneously
- **Avoid:** More than 20 files in a single batch (timeout risk)
- **Strategy:** Use "auto" to let the server decide between short/long processing

### Job Queue

- **Concurrent jobs:** Maximum 3 by default (configurable)
- **Queue depth:** Unlimited (old jobs are cleaned up after 24 hours)
- **Polling interval:** 2-5 seconds recommended

### WebSocket Streaming

- **Chunk size:** 2 seconds (32KB) recommended
- **Connection timeout:** 300 seconds (5 minutes)
- **Best for:** Real-time progress updates on long files (> 30s)

---

## Migration Guide

### From Old API to New API

#### Single File Transcription

**Old (still works):**
```python
response = client.post(
    "/api/asr/transcribe",
    content=audio_data,
    headers={"Content-Type": "application/octet-stream"}
)
```

**New (with progress):**
```python
# Use WebSocket for real-time progress
async with websockets.connect(uri) as websocket:
    # Send audio chunks
    # Receive progress updates
```

#### Multiple Files

**Old (loop):**
```python
for file in files:
    response = client.post("/api/asr/transcribe", ...)
```

**New (batch):**
```python
response = client.post(
    "/api/postprocess/batch-transcribe",
    files=[...],
    params={"strategy": "auto"}
)
```

#### Long Audio

**Old (synchronous):**
```python
response = client.post(
    "/api/postprocess/upload-long",
    files={"file": f}
)
# Wait for completion...
```

**New (async job queue):**
```python
response = client.post("/api/jobs/submit", files={"file": f})
job_id = response.json()['job_id']
# Poll for status later
```

---

## Troubleshooting

### WebSocket Connection Issues

**Problem:** Connection drops during long processing

**Solution:**
- Increase timeout on client side
- Send audio in smaller chunks
- Implement reconnection logic

### Job Queue Not Processing

**Problem:** Jobs stuck in "pending" status

**Solution:**
- Check `/api/jobs/stats` for concurrent job limit
- Verify server has sufficient resources
- Check server logs for errors

### Rate Limit Errors

**Problem:** Getting 429 errors frequently

**Solution:**
- Implement exponential backoff
- Use batch API for multiple files
- Use job queue for long-running tasks
- Contact admin for increased limits

---

## Summary

The API improvements provide:

1. **Better UX** with real-time progress updates
2. **Higher throughput** with batch processing
3. **Scalability** with async job queue
4. **Protection** with rate limiting
5. **Security** with optional authentication

All improvements are backward compatible - existing code continues to work while new features are opt-in.
