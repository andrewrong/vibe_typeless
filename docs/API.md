# Typeless API Documentation

## Base URL

```
http://127.0.0.1:8000
```

## Interactive Documentation

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

## API Endpoints

### Health & Status

#### GET /
Root endpoint

**Response:**
```json
{
  "message": "Typeless Service API",
  "status": "running"
}
```

#### GET /health
Health check

**Response:**
```json
{
  "status": "healthy"
}
```

---

## ASR (Automatic Speech Recognition)

### POST /api/asr/start
Start a new transcription session

**Response:**
```json
{
  "session_id": "uuid-string",
  "status": "started"
}
```

### POST /api/asr/audio/{session_id}
Send audio chunk for transcription

**Parameters:**
- `session_id` (path): Session ID from /api/asr/start
- Body: Binary audio data (16kHz/16bit mono)

**Headers:**
```
Content-Type: application/octet-stream
```

**Response:**
```json
{
  "partial_transcript": "Transcribed text",
  "is_final": false
}
```

### POST /api/asr/stop/{session_id}
Stop session and get final transcript

**Response:**
```json
{
  "session_id": "uuid-string",
  "status": "stopped",
  "final_transcript": "Complete transcription",
  "total_chunks": 5
}
```

### GET /api/asr/status/{session_id}
Get session status

**Response:**
```json
{
  "session_id": "uuid-string",
  "status": "started",
  "audio_chunks_received": 3
}
```

### POST /api/asr/transcribe
Transcribe complete audio file

**Body:** Binary audio data (16kHz/16bit mono)

**Response:**
```json
{
  "transcript": "Transcribed text",
  "duration": 3.5,
  "sample_rate": 16000
}
```

---

## Text Post-Processing

### POST /api/postprocess/text
Process text with rule-based or cloud LLM

**Request Body:**
```json
{
  "text": "um hello uh this is a test",
  "use_cloud_llm": false,
  "provider": "claude"
}
```

**Response:**
```json
{
  "original": "um hello uh this is a test",
  "processed": "hello this is a test",
  "stats": {
    "fillers_removed": 8,
    "duplicates_removed": 0,
    "corrections_applied": 0,
    "total_changes": 8
  },
  "provider_used": "rules"
}
```

### POST /api/postprocess/config
Update post-processing configuration

**Request Body:**
```json
{
  "mode": "rules",
  "provider": "claude",
  "custom_fillers": ["habitual", "phrase"],
  "enable_corrections": true,
  "enable_formatting": true
}
```

**Response:**
```json
{
  "status": "Configuration updated",
  "mode": "rules",
  "provider": "claude",
  "custom_fillers_count": 2
}
```

### GET /api/postprocess/config
Get current configuration

**Response:**
```json
{
  "mode": "rules",
  "provider": "claude",
  "custom_fillers": ["like", "you know", "habitual", "phrase"],
  "correction_phrases": ["no wait", "actually no", "no I mean"]
}
```

### GET /api/postprocess/status
Get service capabilities

**Response:**
```json
{
  "status": "running",
  "capabilities": {
    "rule_based": true,
    "cloud_llm": true,
    "providers": ["claude", "openai"],
    "features": [
      "filler_removal",
      "duplicate_removal",
      "self_correction",
      "auto_formatting"
    ]
  }
}
```

---

## Audio File Processing

### POST /api/postprocess/upload
Upload and process audio file

**Form Data:**
- `file`: Audio file (WAV, MP3, M4A, FLAC, OGG, AAC)
- `apply_postprocess`: Apply text cleaning (default: true)
- `remove_silence`: Remove silence (default: false)
- `normalize_volume`: Normalize volume (default: false)
- `detect_silence_only`: Only detect silence/VAD (default: false)

**Example using curl:**
```bash
curl -X POST http://127.0.0.1:8000/api/postprocess/upload \
  -F "file=@recording.wav" \
  -F "apply_postprocess=true" \
  -F "remove_silence=true"
```

**Response:**
```json
{
  "transcript": "Transcribed text",
  "processed_transcript": "Cleaned text",
  "audio_metadata": {
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16,
    "duration": 5.2,
    "frames": 83200
  },
  "processing_stats": {
    "silence_removed_samples": 5000,
    "postprocess_stats": {
      "fillers_removed": 15,
      "duplicates_removed": 3
    }
  }
}
```

---

## WebSocket Streaming

### WebSocket /api/asr/stream
Real-time audio streaming

**Connect via WebSocket:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/api/asr/stream');

// Send start message
ws.send(JSON.stringify({ action: 'start' }));

// Send binary audio
ws.send(audioData);

// Send stop message
ws.send(JSON.stringify({ action: 'stop' }));

// Receive responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

---

## Usage Examples

### Example 1: Quick Text Processing

```bash
curl -X POST http://127.0.0.1:8000/api/postprocess/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "um like hello everyone uh this is is a demo",
    "use_cloud_llm": false
  }'
```

### Example 2: Session-Based Transcription

```python
import httpx

# Start session
response = httpx.post("http://127.0.0.1:8000/api/asr/start")
session_id = response.json()["session_id"]

# Send audio chunks
with open("audio_chunk.wav", "rb") as f:
    audio_data = f.read()
    httpx.post(
        f"http://127.0.0.1:8000/api/asr/audio/{session_id}",
        content=audio_data,
        headers={"Content-Type": "application/octet-stream"}
    )

# Stop and get final transcript
response = httpx.post(f"http://127.0.0.1:8000/api/asr/stop/{session_id}")
transcript = response.json()["final_transcript"]
print(transcript)
```

### Example 3: Audio File Processing

```bash
# Upload and transcribe audio file
curl -X POST http://127.0.0.1:8000/api/postprocess/upload \
  -F "file=@meeting.mp3" \
  -F "apply_postprocess=true" \
  -F "remove_silence=true"
```

### Example 4: Custom Configuration

```bash
# Add custom filler words
curl -X POST http://127.0.0.1:8000/api/postprocess/config \
  -H "Content-Type: application/json" \
  -d '{
    "custom_fillers": ["technical", "jargon"],
    "enable_corrections": true
  }'
```

---

## Response Codes

- `200 OK`: Success
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

---

## Python Client Example

```python
from httpx import Client

class TypelessClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = Client()

    def process_text(self, text: str, use_llm: bool = False) -> dict:
        """Process text"""
        response = self.client.post(
            f"{self.base_url}/api/postprocess/text",
            json={"text": text, "use_cloud_llm": use_llm}
        )
        return response.json()

    def upload_audio(self, file_path: str, **options) -> dict:
        """Upload and process audio file"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = self.client.post(
                f"{self.base_url}/api/postprocess/upload",
                files=files,
                data=options
            )
        return response.json()

# Usage
client = TypelessClient()
result = client.process_text("um hello uh test")
print(result["processed"])
```

---

## WebSocket Client Example

```python
import asyncio
import websockets
import json

async def transcribe_stream(audio_chunks):
    uri = "ws://127.0.0.1:8000/api/asr/stream"
    async with websockets.connect(uri) as ws:
        # Start session
        await ws.send(json.dumps({"action": "start"}).encode())

        # Send audio chunks
        for chunk in audio_chunks:
            await ws.send(chunk)

            # Receive partial result
            response = await ws.recv()
            data = json.loads(response)
            print(f"Partial: {data}")

        # Stop session
        await ws.send(json.dumps({"action": "stop"}).encode())

        # Receive final result
        final = await ws.recv()
        print(f"Final: {final}")
```

---

## Configuration

### Environment Variables

```bash
# Anthropic Claude API Key (for cloud LLM)
export ANTHROPIC_API_KEY="your-key-here"

# OpenAI API Key (for cloud LLM)
export OPENAI_API_KEY="your-key-here"
```

### Processing Modes

1. **Rules Mode** (default)
   - Fast, no external dependencies
   - Filler removal, duplicate removal, self-correction
   - Auto-formatting

2. **Cloud LLM Mode**
   - Higher quality processing
   - Requires API key
   - Intelligent text improvement
   - Falls back to rules on error

---

## Performance Considerations

- **ASR Latency**: Currently placeholder, target < 500ms with MLX model
- **Post-Processing**: < 100ms for rules mode
- **Cloud LLM**: 1-3 seconds depending on text length
- **File Upload**: Depends on file size and network

---

## Troubleshooting

### Server not starting
- Check if port 8000 is available
- Verify dependencies: `uv run python -m api.server`

### File upload failing
- Verify audio format is supported
- Check file size limits
- Ensure python-multipart is installed

### Cloud LLM not working
- Verify API keys are set
- Check internet connection
- Falls back to rules mode automatically

---

## See Also

- [Architecture Documentation](./ARCHITECTURE.md)
- [Project README](./README.md)
- [CLAUDE.md](./CLAUDE.md)
