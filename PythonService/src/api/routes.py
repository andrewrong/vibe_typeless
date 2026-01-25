"""
ASR API Routes
FastAPI endpoints for speech-to-text streaming
"""

import uuid
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Body, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np

from asr.model import ASRModel, AudioConfig
from asr.audio_processor import AudioProcessor
from postprocess.processor import TextProcessor
from postprocess.cloud_llm import ProviderConfig, create_provider_from_env


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


# Post-processing request/response models
class PostProcessRequest(BaseModel):
    """Request for text post-processing"""
    text: str
    use_cloud_llm: bool = False
    provider: Optional[str] = "claude"  # "claude" or "openai"


class PostProcessResponse(BaseModel):
    """Response for text post-processing"""
    original: str
    processed: str
    stats: Dict
    provider_used: Optional[str] = None


class ProcessConfig(BaseModel):
    """Post-processing configuration"""
    mode: str  # "rules", "cloud", "hybrid"
    provider: str = "claude"
    custom_fillers: list[str] = []
    enable_corrections: bool = True
    enable_formatting: bool = True


# Audio file processing models
class AudioFileProcessRequest(BaseModel):
    """Request for audio file processing"""
    apply_postprocess: bool = True
    remove_silence: bool = True
    normalize_volume: bool = False
    detect_silence_only: bool = False


class AudioFileProcessResponse(BaseModel):
    """Response for audio file processing"""
    transcript: str
    processed_transcript: Optional[str]
    audio_metadata: Dict
    processing_stats: Optional[Dict] = None
    silence_regions: Optional[list] = None


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


# Post-processing router
postprocess_router = APIRouter(prefix="/api/postprocess", tags=["Post-Processing"])

# Global processor instance
processor = TextProcessor()


@postprocess_router.post("/text", response_model=PostProcessResponse)
async def process_text(request: PostProcessRequest):
    """
    Process text with rule-based or cloud LLM post-processing

    Args:
        request: Post-processing request with text and options

    Returns:
        Processed text with statistics
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if request.use_cloud_llm:
        # Use cloud LLM for processing
        try:
            provider = create_provider_from_env(provider=request.provider)
            llm_response = provider.process_text(request.text)

            if llm_response.has_error():
                # Fallback to rule-based processing
                result = processor.process(request.text)
                return PostProcessResponse(
                    original=request.text,
                    processed=result.processed,
                    stats=result.stats,
                    provider_used="rules (fallback)"
                )

            return PostProcessResponse(
                original=request.text,
                processed=llm_response.text,
                stats={
                    "fillers_removed": 0,
                    "duplicates_removed": 0,
                    "corrections_applied": 0,
                    "total_changes": len(request.text) - len(llm_response.text)
                },
                provider_used=llm_response.provider
            )
        except Exception as e:
            # Fallback to rule-based processing on error
            result = processor.process(request.text)
            return PostProcessResponse(
                original=request.text,
                processed=result.processed,
                stats=result.stats,
                provider_used=f"rules (error: {str(e)})"
            )
    else:
        # Use rule-based processing
        result = processor.process(request.text)
        return PostProcessResponse(
            original=request.text,
            processed=result.processed,
            stats=result.stats,
            provider_used="rules"
        )


@postprocess_router.post("/config")
async def update_config(config: ProcessConfig):
    """
    Update post-processing configuration

    Args:
        config: New configuration

    Returns:
        Current configuration
    """
    # Update custom fillers
    if config.custom_fillers:
        processor.fillers.update(config.custom_fillers)

    return {
        "status": "Configuration updated",
        "mode": config.mode,
        "provider": config.provider,
        "custom_fillers_count": len(config.custom_fillers)
    }


@postprocess_router.get("/config")
async def get_config():
    """
    Get current post-processing configuration

    Returns:
        Current configuration
    """
    return {
        "mode": "rules",
        "provider": "claude",
        "custom_fillers": list(processor.fillers),
        "correction_phrases": list(processor.correction_phrases)
    }


@postprocess_router.get("/status")
async def get_status():
    """
    Get post-processing service status

    Returns:
        Service status and capabilities
    """
    return {
        "status": "running",
        "capabilities": {
            "rule_based": True,
            "cloud_llm": True,
            "providers": ["claude", "openai"],
            "features": [
                "filler_removal",
                "duplicate_removal",
                "self_correction",
                "auto_formatting"
            ]
        }
    }


@postprocess_router.post("/upload", response_model=AudioFileProcessResponse)
async def upload_audio_file(
    file: UploadFile = File(...),
    apply_postprocess: bool = True,
    remove_silence: bool = False,
    normalize_volume: bool = False,
    detect_silence_only: bool = False
):
    """
    Upload and process audio file

    Args:
        file: Audio file (WAV, MP3, M4A, etc.)
        apply_postprocess: Whether to apply text post-processing
        remove_silence: Whether to remove silence from audio
        normalize_volume: Whether to normalize volume
        detect_silence_only: Only detect silence, don't transcribe

    Returns:
        Transcription with optional post-processing
    """
    # Get file format from extension
    file_format = file.filename.split('.')[-1] if '.' in file.filename else None

    if file_format not in ['wav', 'mp3', 'm4a', 'flac', 'ogg', 'aac']:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_format}. Supported: WAV, MP3, M4A, FLAC, OGG, AAC"
        )

    # Read file data
    file_data = await file.read()

    # Process audio
    audio_processor = AudioProcessor()

    try:
        # Load and convert audio
        audio_array, metadata = audio_processor.process_audio_file(
            file_data=file_data,
            file_format=file_format
        )

        # Apply preprocessing if requested
        processing_stats = {}
        silence_regions = None

        if remove_silence:
            original_length = len(audio_array)
            audio_array = audio_processor.remove_silence(audio_array)
            processing_stats["silence_removed_samples"] = original_length - len(audio_array)

        if normalize_volume:
            audio_array = audio_processor.normalize_volume(audio_array)
            processing_stats["volume_normalized"] = True

        if detect_silence_only:
            # Only detect silence, don't transcribe
            silence_regions = audio_processor.detect_silence(audio_array)
            return AudioFileProcessResponse(
                transcript="",
                processed_transcript=None,
                audio_metadata=metadata,
                processing_stats=None,
                silence_regions=[{
                    "start_sample": int(start),
                    "end_sample": int(end),
                    "duration_ms": int((end - start) / metadata["sample_rate"] * 1000)
                } for start, end in silence_regions]
            )

        # Transcribe
        model = get_asr_model()
        transcript = model.transcribe(
            audio_array.astype(np.int16)
        )

        # Apply post-processing if requested
        processed_transcript = None
        if apply_postprocess and transcript:
            result = processor.process(transcript)
            processed_transcript = result.processed
            processing_stats["postprocess_stats"] = result.stats

        return AudioFileProcessResponse(
            transcript=transcript,
            processed_transcript=processed_transcript,
            audio_metadata=metadata,
            processing_stats=processing_stats if processing_stats else None,
            silence_regions=silence_regions
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing audio file: {str(e)}"
        )


# Include postprocess router in the main router
router.include_router(postprocess_router)

