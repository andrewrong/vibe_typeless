"""
ASR API Routes
FastAPI endpoints for speech-to-text streaming
"""

import uuid
from typing import Dict
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np

from asr.model import ASRModel, AudioConfig


# Request/Response models
class SessionStartResponse(BaseModel):
    """Response for session start"""
    session_id: str
    status: str


class AudioTranscriptResponse(BaseModel):
    """Response for audio transcription"""
    partial_transcript: str
    is_final: bool


class SessionStatusResponse(BaseModel):
    """Response for session status"""
    session_id: str
    status: str
    audio_chunks_received: int


class SessionStopResponse(BaseModel):
    """Response for session stop"""
    session_id: str
    status: str
    final_transcript: str
    total_chunks: int


class FileTranscribeResponse(BaseModel):
    """Response for file transcription"""
    transcript: str
    duration: float
    sample_rate: int


# Router
router = APIRouter(prefix="/api/asr", tags=["ASR"])

# Session storage (in-memory for now, should use Redis in production)
sessions: Dict[str, Dict] = {}

# ASR model instance (singleton)
asr_model = None


def get_asr_model():
    """Get or create ASR model instance"""
    global asr_model
    if asr_model is None:
        config = AudioConfig(sample_rate=16000, channels=1, bit_depth=16)
        asr_model = ASRModel(config=config)
        asr_model.load_model()
    return asr_model


@router.post("/start", response_model=SessionStartResponse)
async def start_session():
    """
    Start a new ASR transcription session

    Returns:
        Session ID and status
    """
    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "session_id": session_id,
        "status": "started",
        "audio_chunks": [],
        "partial_transcript": "",
        "chunks_received": 0
    }

    return SessionStartResponse(
        session_id=session_id,
        status="started"
    )


@router.post("/audio/{session_id}", response_model=AudioTranscriptResponse)
async def send_audio(session_id: str, request: bytes = Body(..., media_type='application/octet-stream')):
    """
    Send audio chunk for transcription

    Args:
        session_id: Session identifier
        request: Raw audio data (bytes)

    Returns:
        Partial transcription result
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Convert bytes to numpy array
    audio_array = np.frombuffer(request, dtype=np.int16)

    # Store audio chunk
    session["audio_chunks"].append(audio_array)
    session["chunks_received"] += 1

    # Get ASR model and transcribe
    model = get_asr_model()
    transcript = model.transcribe(audio_array)

    # Update partial transcript
    session["partial_transcript"] = transcript

    return AudioTranscriptResponse(
        partial_transcript=transcript,
        is_final=False
    )


@router.post("/stop/{session_id}", response_model=SessionStopResponse)
async def stop_session(session_id: str):
    """
    Stop ASR session and get final transcript

    Args:
        session_id: Session identifier

    Returns:
        Final transcription result
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    session["status"] = "stopped"

    # Combine all audio chunks and get final transcript
    model = get_asr_model()

    # Handle empty audio chunks
    if session["audio_chunks"]:
        all_audio = np.concatenate(session["audio_chunks"])
        final_transcript = model.transcribe(all_audio)
    else:
        final_transcript = ""

    # Clean up session
    total_chunks = session["chunks_received"]
    sessions.pop(session_id)

    return SessionStopResponse(
        session_id=session_id,
        status="stopped",
        final_transcript=final_transcript,
        total_chunks=total_chunks
    )


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_status(session_id: str):
    """
    Get ASR session status

    Args:
        session_id: Session identifier

    Returns:
        Session status
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    return SessionStatusResponse(
        session_id=session_id,
        status=session["status"],
        audio_chunks_received=session["chunks_received"]
    )


@router.post("/transcribe", response_model=FileTranscribeResponse)
async def transcribe_file(request: bytes = Body(..., media_type='application/octet-stream')):
    """
    Transcribe a complete audio file

    Args:
        request: Complete audio file data (bytes)

    Returns:
        Full transcription with metadata
    """
    # Convert bytes to numpy array
    audio_array = np.frombuffer(request, dtype=np.int16)

    # Get duration
    model = get_asr_model()
    duration = len(audio_array) / model.config.sample_rate

    # Transcribe
    transcript = model.transcribe(audio_array)

    return FileTranscribeResponse(
        transcript=transcript,
        duration=duration,
        sample_rate=model.config.sample_rate
    )


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming transcription

    Clients can send:
    - {"action": "start"} - Start streaming session
    - <binary audio data> - Send audio chunks
    - {"action": "stop"} - Stop session and get final transcript

    Server responds with:
    - {"status": "started", "session_id": "..."}
    - {"transcript": "...", "is_final": false}
    - {"final_transcript": "...", "total_chunks": N}
    """
    await websocket.accept()

    session_id = str(uuid.uuid4())
    audio_chunks = []
    model = get_asr_model()
    started = False

    try:
        while True:
            # Receive data
            data = await websocket.receive()

            if "text" in data:
                # JSON message
                import json
                message = json.loads(data["text"])

                if message.get("action") == "start" and not started:
                    # Start streaming session
                    started = True
                    await websocket.send_json({
                        "status": "started",
                        "session_id": session_id
                    })

                elif message.get("action") == "stop":
                    # Stop streaming and send final result
                    if audio_chunks:
                        all_audio = np.concatenate(audio_chunks)
                        final_transcript = model.transcribe(all_audio)
                    else:
                        final_transcript = ""

                    await websocket.send_json({
                        "final_transcript": final_transcript,
                        "total_chunks": len(audio_chunks)
                    })
                    break

            elif "bytes" in data and started:
                # Binary audio data
                audio_bytes = data["bytes"]
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_chunks.append(audio_array)

                # Transcribe chunk
                transcript = model.transcribe(audio_array)

                # Send partial result
                await websocket.send_json({
                    "transcript": transcript,
                    "is_final": False
                })

    except WebSocketDisconnect:
        # Client disconnected
        pass
    finally:
        # Cleanup
        audio_chunks.clear()
