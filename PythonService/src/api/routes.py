"""
ASR API Routes
FastAPI endpoints for speech-to-text streaming
"""

import uuid
import logging
from typing import Dict, Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Body, UploadFile, File

logger = logging.getLogger(__name__)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np


# Power Mode configuration
def detect_app_category(app_info: str) -> str:
    """Detect app category from bundle identifier"""
    if not app_info:
        return "general"

    bundle_id = app_info.split("|")[-1].lower()

    # Coding apps
    if any(x in bundle_id for x in ["xcode", "vscode", "jetbrains", "sublimetext"]):
        return "coding"

    # Writing apps
    if any(x in bundle_id for x in ["notion", "word", "pages"]):
        return "writing"

    # Chat apps
    if any(x in bundle_id for x in ["wechat", "slack", "discord"]):
        return "chat"

    # Browser apps
    if any(x in bundle_id for x in ["chrome", "safari", "firefox"]):
        return "browser"

    # Terminal apps
    if any(x in bundle_id for x in ["terminal", "iterm"]):
        return "terminal"

    return "general"


def get_power_mode_config(category: str) -> Dict:
    """Get Power Mode configuration for app category"""
    configs = {
        "coding": {
            "add_punctuation": False,        # Code doesn't need punctuation
            "preserve_case": True,           # Keep variable names case
            "technical_terms": True,         # Recognize tech terms
            "remove_fillers": True
        },
        "writing": {
            "add_punctuation": True,         # Full punctuation
            "preserve_case": False,          # Normalize capitalization
            "technical_terms": False,
            "remove_fillers": True
        },
        "chat": {
            "add_punctuation": True,         # Casual punctuation
            "preserve_case": False,
            "technical_terms": False,
            "remove_fillers": False          # Keep natural speech
        },
        "browser": {
            "add_punctuation": True,
            "preserve_case": False,
            "technical_terms": False,
            "remove_fillers": True
        },
        "terminal": {
            "add_punctuation": False,        # Commands don't need punctuation
            "preserve_case": True,           # Commands are case-sensitive
            "technical_terms": True,
            "remove_fillers": True
        },
        "general": {
            "add_punctuation": True,
            "preserve_case": False,
            "technical_terms": False,
            "remove_fillers": True
        }
    }

    return configs.get(category, configs["general"])

from src.asr.model import ASRModel, AudioConfig
from src.asr.whisper_model import WhisperASR
from src.asr.optimized_whisper import OptimizedWhisperASR
from src.asr.model_config import model_manager, ModelSize, ASRModelConfig, ModelInfo
from src.asr.audio_processor import AudioProcessor
from src.asr.audio_pipeline import AudioPipeline
from src.postprocess.processor import TextProcessor
from src.postprocess.dictionary import personal_dictionary
from src.postprocess.cloud_llm import ProviderConfig, create_provider_from_env
from src.postprocess.ai_processor import AIPostProcessor, PostProcessRequest as AIRequest, PostProcessResponse as AIResponse
from src.api.websocket_stream import streamer
from src.api.job_queue import job_queue, JobInfo


# Request/Response models
class SessionStartRequest(BaseModel):
    """Request for session start"""
    app_info: Optional[str] = None


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


def _get_asr_model_instance(language: str = "auto"):
    """
    Get or create ASR model instance

    Model selection is controlled in src/asr/__init__.py
    Change MODEL_TYPE there to switch between Whisper, VibeVoice, or SenseVoice

    Args:
        language: Language code ("auto", "zh", "en", "ja", "ko", "yue")
                Only used for SenseVoice. Defaults to "auto".
    """
    global asr_model

    # Import from factory (avoid naming conflict with this function)
    from src.asr import get_asr_model

    # Get model from factory (singleton pattern per language)
    return get_asr_model(language=language)


@router.post("/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest = None):
    """
    Start a new ASR transcription session

    Args:
        request: Optional session start request with app_info

    Returns:
        Session ID and status
    """
    import logging
    logger = logging.getLogger(__name__)

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "session_id": session_id,
        "status": "started",
        "audio_chunks": [],
        "partial_transcript": "",
        "chunks_received": 0,
        "app_info": request.app_info if request else None
    }

    # Log app info for Power Mode
    if request and request.app_info:
        logger.info(f"📱 Power Mode: App={request.app_info}")

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
        Partial transcription result (empty during recording)
    """
    import logging
    logger = logging.getLogger(__name__)

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Log received data size
    logger.info(f"Received audio chunk: {len(request)} bytes for session {session_id[:8]}...")

    # Convert bytes to numpy array
    try:
        audio_array = np.frombuffer(request, dtype=np.int16)
        logger.info(f"Converted to numpy array: {len(audio_array)} samples")
    except Exception as e:
        logger.error(f"Failed to convert audio data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid audio data: {e}")

    # Store audio chunk (don't transcribe yet - wait for stop)
    session["audio_chunks"].append(audio_array)
    session["chunks_received"] += 1

    # Real-time preview: transcribe every 5 chunks
    CHUNKS_FOR_PREVIEW = 5
    partial_transcript = ""

    if session['chunks_received'] % CHUNKS_FOR_PREVIEW == 0:
        logger.info(f"🔄 Real-time preview: transcribing {session['chunks_received']} chunks...")

        # Combine all chunks so far and transcribe
        all_audio = np.concatenate(session["audio_chunks"])

        try:
            # Apply audio pipeline for preview (faster, no VAD for speed)
            model = _get_asr_model_instance()

            # For preview, skip VAD to save time
            from src.asr.audio_pipeline import AudioEnhancer
            enhancer = AudioEnhancer()
            enhanced = enhancer.enhance(all_audio.astype(np.float32) / 32768.0)
            enhanced_int16 = (enhanced * 32767).astype(np.int16)

            # Transcribe
            partial_transcript = model.transcribe(enhanced_int16, language="auto")

            # Apply processing for preview (punctuation + dictionary)
            if partial_transcript:
                # Apply intelligent punctuation correction
                partial_transcript = processor.punctuation_corrector.correct(partial_transcript)
                # Apply dictionary for technical terms
                partial_transcript = personal_dictionary.apply(partial_transcript)

            logger.info(f"📝 Preview transcript: '{partial_transcript[:50]}...'")

        except Exception as e:
            logger.error(f"Preview transcription failed: {e}")

    logger.info(f"Session {session_id[:8]}... has {session['chunks_received']} chunks, total audio: {sum(len(c) for c in session['audio_chunks'])} samples")

    return AudioTranscriptResponse(
        partial_transcript=partial_transcript,
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
    import logging
    logger = logging.getLogger(__name__)

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    session["status"] = "stopped"

    # Power Mode: Detect app category and apply config
    app_info = session.get("app_info", "")
    app_category = detect_app_category(app_info)
    power_config = get_power_mode_config(app_category)

    logger.info(f"📱 Power Mode: {app_info} → {app_category}")
    logger.info(f"   Config: punctuation={power_config['add_punctuation']}, technical={power_config['technical_terms']}")

    # Combine all audio chunks and get final transcript
    model = _get_asr_model_instance()

    # Handle empty audio chunks
    if session["audio_chunks"]:
        all_audio = np.concatenate(session["audio_chunks"])

        # Apply audio processing pipeline (VAD → Enhancement → Segmentation)
        logger.info("🎛️ Applying audio processing pipeline...")

        # Create audio pipeline
        pipeline = AudioPipeline(
            vad_threshold=0.5,
            enable_enhancement=True,
            enable_vad=True
        )

        # Process audio
        processed_segments, stats = pipeline.process(all_audio)

        logger.info(f"   Processed {stats['segments']} segments, "
                   f"removed {stats['silence_removed'] / 16000:.2f}s silence")

        # Transcribe each segment and combine
        transcripts = []
        for i, segment in enumerate(processed_segments):
            logger.info(f"   Transcribing segment {i+1}/{len(processed_segments)} "
                       f"({len(segment)} samples)")
            segment_transcript = model.transcribe(segment, language="auto")
            if segment_transcript:
                transcripts.append(segment_transcript)

        # Combine transcripts
        final_transcript = " ".join(transcripts).strip()
        logger.info(f"📝 Combined transcript ({len(final_transcript)} chars): '{final_transcript}'")

        # Apply Power Mode configuration
        if final_transcript:
            # Apply intelligent punctuation correction
            if power_config['add_punctuation']:
                logger.info(f"🔧 Applying punctuation correction ({len(final_transcript)} chars)...")
                logger.info(f"   Processor has punctuation_corrector: {hasattr(processor, 'punctuation_corrector')}")
                if hasattr(processor, 'punctuation_corrector'):
                    before_punct = final_transcript
                    final_transcript = processor.punctuation_corrector.correct(final_transcript)
                    logger.info(f"✅ After punctuation ({len(final_transcript)} chars): '{final_transcript}'")
                    if len(final_transcript) < len(before_punct):
                        logger.error(f"⚠️ Text got shorter! Before: {len(before_punct)}, After: {len(final_transcript)}")
                else:
                    logger.warning("⚠️ processor.punctuation_corrector not found, skipping punctuation correction")

            # Apply personal dictionary (especially for technical terms)
            if power_config['technical_terms']:
                logger.info(f"🔧 Applying dictionary ({len(final_transcript)} chars)...")
                before_dict = final_transcript
                final_transcript = personal_dictionary.apply(final_transcript)
                logger.info(f"✅ After dictionary ({len(final_transcript)} chars): '{final_transcript}'")
                if len(final_transcript) < len(before_dict):
                    logger.error(f"⚠️ Text got shorter! Before: {len(before_dict)}, After: {len(final_transcript)}")

            # Apply AI post-processing for text enhancement (NEW)
            # Check if AI processing is enabled via .env file
            from src.config import settings

            if settings.ENABLE_AI_POSTPROCESS and len(final_transcript) > 10:  # Only AI process if text > 10 chars
                try:
                    logger.info(f"🤖 Applying AI post-processing ({len(final_transcript)} chars)...")

                    # Create AI processor
                    ai_processor = AIPostProcessor()

                    # Create request (use provider from .env)
                    ai_request = AIRequest(
                        text=final_transcript,
                        provider=settings.AI_PROVIDER,  # From .env: openai, gemini, ollama
                        model=None  # Use default model from .env
                    )

                    # Process with AI
                    ai_response = await ai_processor.process(ai_request)

                    final_transcript = ai_response.processed
                    logger.info(f"✅ AI processing complete ({len(final_transcript)} chars)")
                    logger.debug(f"   AI processed: '{final_transcript[:100]}...'")

                except Exception as e:
                    logger.warning(f"⚠️ AI post-processing failed: {e}")
                    logger.warning(f"   Falling back to rule-based result")
                    # Keep original text if AI processing fails

        logger.info(f"✅ Final transcript: '{final_transcript}'")
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
    model = _get_asr_model_instance()
    duration = len(audio_array) / model.config.sample_rate

    # Transcribe
    transcript = model.transcribe(audio_array, language="auto")

    return FileTranscribeResponse(
        transcript=transcript,
        duration=duration,
        sample_rate=model.config.sample_rate
    )


# Model Configuration endpoints
class ModelConfigRequest(BaseModel):
    """Request for updating model configuration"""
    model_size: str = "base"
    language: Optional[str] = None
    fp16: bool = True


class ModelConfigResponse(BaseModel):
    """Response for model configuration"""
    current_model: str
    language: Optional[str]
    fp16: bool
    available_models: list[str]


class ModelInfoResponse(BaseModel):
    """Response for model information"""
    size: str
    params: str
    download_size: str
    ram_required: str
    speed: str
    description: str


@router.get("/config", response_model=ModelConfigResponse)
async def get_model_config():
    """
    Get current ASR model configuration

    Returns:
        Current model configuration and available models
    """
    # Get model from new factory (supports Whisper, VibeVoice, SenseVoice)
    model = _get_asr_model_instance()
    config = model.config

    return ModelConfigResponse(
        current_model=config.model_size,
        language=config.language,
        fp16=config.fp16,
        available_models=["tiny", "base", "small", "medium", "large-v3", "sensevoice"]
    )


@router.post("/config", response_model=ModelConfigResponse)
async def set_model_config(request: ModelConfigRequest):
    """
    Update ASR model configuration

    Args:
        request: New model configuration

    Returns:
        Updated configuration

    Raises:
        ValueError: If model_size is invalid
    """
    try:
        # Update model size
        if request.model_size != model_manager.current_model_size:
            model_manager.set_model_size(request.model_size)

        # Update language if specified
        if request.language is not None and request.language != model_manager.config.language:
            model_manager.set_language(request.language)

        # Update fp16 setting if different
        if request.fp16 != model_manager.config.fp16:
            model_manager.set_fp16(request.fp16)

        config = model_manager.config

        return ModelConfigResponse(
            current_model=config.model_size,
            language=config.language,
            fp16=config.fp16,
            available_models=ModelSize.all()
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models")
async def list_models():
    """
    Get information about all available models

    Returns:
        Dictionary of model information
    """
    models = model_manager.get_available_models()

    return {
        size: {
            "params": info.params,
            "download_size": info.download_size,
            "ram_required": info.ram_required,
            "speed": info.speed,
            "description": info.description
        }
        for size, info in models.items()
    }


@router.get("/models/{model_size}", response_model=ModelInfoResponse)
async def get_model_info(model_size: str):
    """
    Get information about a specific model

    Args:
        model_size: Model size to query

    Returns:
        Model information

    Raises:
        HTTPException: If model_size is invalid
    """
    try:
        info = model_manager.get_model_info(model_size)
        return ModelInfoResponse(
            size=info.size,
            params=info.params,
            download_size=info.download_size,
            ram_required=info.ram_required,
            speed=info.speed,
            description=info.description
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reset")
async def reset_model_config():
    """
    Reset model configuration to defaults

    Returns:
        Default configuration
    """
    model_manager.reset_to_defaults()
    config = model_manager.config

    return ModelConfigResponse(
        current_model=config.model_size,
        language=config.language,
        fp16=config.fp16,
        available_models=ModelSize.all()
    )


# Dictionary management endpoints
class DictionaryEntryRequest(BaseModel):
    """Request for dictionary entry"""
    spoken: str
    written: str
    category: str = "custom"
    case_sensitive: bool = False
    whole_word: bool = False


class DictionaryEntryResponse(BaseModel):
    """Response for dictionary entry"""
    spoken: str
    written: str
    category: str
    case_sensitive: bool
    whole_word: bool


@router.get("/dictionary")
async def get_dictionary():
    """
    Get all dictionary entries

    Returns:
        All dictionary entries grouped by category
    """
    from src.postprocess.dictionary import personal_dictionary

    entries_by_category = {}

    for category in personal_dictionary.get_all_categories():
        entries = personal_dictionary.get_entries_by_category(category)
        entries_by_category[category] = [
            {
                "spoken": e.spoken,
                "written": e.written,
                "case_sensitive": e.case_sensitive,
                "whole_word": e.whole_word
            }
            for e in entries
        ]

    return {
        "entries": entries_by_category,
        "total": sum(len(v) for v in entries_by_category.values())
    }


@router.post("/dictionary")
async def add_dictionary_entry(request: DictionaryEntryRequest):
    """
    Add a new dictionary entry

    Args:
        request: Dictionary entry data

    Returns:
        Success message
    """
    from src.postprocess.dictionary import personal_dictionary

    personal_dictionary.add_entry(
        spoken=request.spoken,
        written=request.written,
        category=request.category,
        case_sensitive=request.case_sensitive,
        whole_word=request.whole_word
    )

    # Save to file
    personal_dictionary.save_to_file()

    return {
        "status": "success",
        "message": f"Added entry: '{request.spoken}' → '{request.written}'"
    }


@router.delete("/dictionary/{spoken}")
async def remove_dictionary_entry(spoken: str):
    """
    Remove a dictionary entry

    Args:
        spoken: Spoken form to remove

    Returns:
        Success message
    """
    from src.postprocess.dictionary import personal_dictionary

    personal_dictionary.remove_entry(spoken)
    personal_dictionary.save_to_file()

    return {
        "status": "success",
        "message": f"Removed entry: '{spoken}'"
    }


@router.post("/dictionary/clear")
async def clear_custom_dictionary():
    """
    Clear all custom dictionary entries, keep defaults

    Returns:
        Success message
    """
    from src.postprocess.dictionary import personal_dictionary

    personal_dictionary.clear_custom_entries()
    personal_dictionary.save_to_file()

    return {
        "status": "success",
        "message": "Cleared all custom entries"
    }


@router.post("/dictionary/reload")
async def reload_dictionary():
    """
    Reload dictionary from file

    Returns:
        Success message
    """
    from src.postprocess.dictionary import personal_dictionary

    # Reinitialize dictionary
    global personal_dictionary
    from src.postprocess.dictionary import PersonalDictionary
    personal_dictionary = PersonalDictionary()

    return {
        "status": "success",
        "message": "Dictionary reloaded",
        "entries": len(personal_dictionary.entries)
    }


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
    model = _get_asr_model_instance()
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
                        final_transcript = model.transcribe(all_audio, language="auto")
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
                transcript = model.transcribe(audio_array, language="auto")

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


@router.websocket("/stream-progress")
async def websocket_stream_with_progress(websocket: WebSocket):
    """
    Enhanced WebSocket endpoint for streaming with progress updates

    Protocol:
    Client sends:
    - {"action": "start"} - Start streaming session
    - <binary audio data> - Send audio chunks
    - {"action": "process", "strategy": "hybrid"} - Process with long audio
    - {"action": "stop"} - Stop session

    Server sends:
    - {"type": "started", "session_id": "..."}
    - {"type": "chunk_received", "chunk_number": N}
    - {"type": "progress", "current_segment": N, "total_segments": M, "progress_percent": 50.0}
    - {"type": "segment_complete", "transcript_part": "...", ...}
    - {"type": "complete", "final_transcript": "...", ...}
    - {"type": "error", "message": "..."}
    """
    await streamer.handle_streaming_session(websocket)


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
    detect_silence_only: bool = False,
    language: str = "auto"
):
    """
    Upload and process audio file (for short audio < 30s)

    Args:
        file: Audio file (WAV, MP3, M4A, etc.)
        apply_postprocess: Whether to apply text post-processing
        remove_silence: Whether to remove silence from audio
        normalize_volume: Whether to normalize volume
        detect_silence_only: Only detect silence, don't transcribe
        language: Language code - "zh" (Chinese), "en" (English), "ja" (Japanese), "ko" (Korean), "yue" (Cantonese), or "auto" (auto-detect)

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

        # Transcribe (convert normalized float32 back to int16)
        audio_int16 = (audio_array * 32767).astype(np.int16)
        model = _get_asr_model_instance()
        transcript = model.transcribe(audio_int16, language=language)

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


class LongAudioProcessRequest(BaseModel):
    """Request for long audio file processing"""
    strategy: str = "hybrid"  # fixed, vad, hybrid
    merge_strategy: str = "simple"  # simple, overlap, smart
    apply_postprocess: bool = True


class LongAudioProcessResponse(BaseModel):
    """Response for long audio file processing"""
    transcript: str
    processed_transcript: Optional[str]
    audio_metadata: Dict
    processing_stats: Dict
    segments: List[Dict]


@postprocess_router.post("/upload-long", response_model=LongAudioProcessResponse)
async def upload_long_audio(
    file: UploadFile = File(...),
    apply_postprocess: bool = True,
    language: str = "auto"
):
    """
    Upload and process long audio file (> 30 seconds)

    Uses the same AudioPipeline as real-time ASR for consistent results.

    Args:
        file: Audio file (WAV, MP3, M4A, etc.)
        apply_postprocess: Whether to apply text post-processing
        language: Language code - "zh" (Chinese), "en" (English), "ja" (Japanese), "ko" (Korean), "yue" (Cantonese), or "auto" (auto-detect)

    Returns:
        Full transcription with segment information
    """
    # Log incoming request parameters
    logger.info(f"📥 upload-long request: file={file.filename}, apply_postprocess={apply_postprocess}, language={language}")

    # Get file format from extension
    file_format = file.filename.split('.')[-1] if '.' in file.filename else None

    if file_format not in ['wav', 'mp3', 'm4a', 'flac', 'ogg', 'aac']:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file_format}. Supported: WAV, MP3, M4A, FLAC, OGG, AAC"
        )

    # Read file data
    file_data = await file.read()

    try:
        # Use same pipeline as real-time ASR (AudioPipeline)
        from src.asr.audio_pipeline import AudioPipeline
        from src.asr.audio_processor import AudioProcessor

        # Load and convert audio (same as /upload endpoint)
        audio_processor = AudioProcessor()
        audio_array, metadata = audio_processor.process_audio_file(
            file_data=file_data,
            file_format=file_format
        )

        # Process with AudioPipeline (same as real-time ASR)
        pipeline = AudioPipeline(
            vad_threshold=0.5,
            enable_enhancement=True,
            enable_vad=True
        )

        processed_segments, stats = pipeline.process(audio_array)
        logger.info(f"   AudioPipeline: {stats['segments']} segments, removed {stats['silence_removed'] / 16000:.2f}s silence")

        # Transcribe all segments (same as real-time ASR stop endpoint)
        model = _get_asr_model_instance(language=language)
        transcripts = []

        for i, segment in enumerate(processed_segments):
            logger.info(f"   Transcribing segment {i+1}/{len(processed_segments)} ({len(segment)} samples)")
            segment_transcript = model.transcribe(segment, language=language)
            if segment_transcript:
                transcripts.append(segment_transcript)

        # Join transcripts
        full_transcript = " ".join(transcripts) if transcripts else ""

        # Apply post-processing if requested
        processed_transcript = None
        postprocess_stats = None
        if apply_postprocess and full_transcript:
            result = processor.process(full_transcript)
            processed_transcript = result.processed
            postprocess_stats = result.stats

        return LongAudioProcessResponse(
            transcript=full_transcript,
            processed_transcript=processed_transcript,
            audio_metadata=metadata,
            processing_stats={
                "num_segments": len(processed_segments),
                "strategy": "audio_pipeline",
                "postprocess_stats": postprocess_stats
            },
            segments=[{
                "segment_index": i,
                "duration": len(segment) / 16000
            } for i, segment in enumerate(processed_segments)]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing long audio file: {str(e)}"
        )


# Batch transcription models
class BatchTranscriptionItem(BaseModel):
    """Result for a single file in batch"""
    filename: str
    success: bool
    transcript: Optional[str] = None
    processed_transcript: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class BatchTranscriptionResponse(BaseModel):
    """Response for batch transcription"""
    total_files: int
    successful: int
    failed: int
    results: List[BatchTranscriptionItem]
    total_duration: float
    processing_time: float


@postprocess_router.post("/batch-transcribe", response_model=BatchTranscriptionResponse)
async def batch_transcribe(
    files: List[UploadFile] = File(...),
    apply_postprocess: bool = True,
    strategy: str = "auto"
):
    """
    Transcribe multiple audio files in a single request

    Args:
        files: List of audio files (WAV, MP3, M4A, etc.)
        apply_postprocess: Whether to apply text post-processing
        strategy: "auto" (use long audio for >30s), "short" (force short), "long" (force long)

    Returns:
        Batch transcription results with individual file results
    """
    import time
    import tempfile
    start_time = time.time()

    results = []
    successful = 0
    failed = 0
    total_duration = 0.0

    audio_processor = AudioProcessor()

    for file in files:
        file_result = BatchTranscriptionItem(
            filename=file.filename,
            success=False
        )

        try:
            # Get file format
            file_format = file.filename.split('.')[-1] if '.' in file.filename else None

            if file_format not in ['wav', 'mp3', 'm4a', 'flac', 'ogg', 'aac']:
                file_result.error = f"Unsupported format: {file_format}"
                failed += 1
                results.append(file_result)
                continue

            # Read file data
            file_data = await file.read()

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
                tmp_file.write(file_data)
                tmp_file_path = tmp_file.name

            try:
                # Load and convert audio
                audio_array, metadata = audio_processor.process_audio_file(
                    file_data=file_data,
                    file_format=file_format
                )

                duration = metadata.get("duration", 0)
                total_duration += duration

                # Decide which strategy to use
                use_long_audio = (
                    strategy == "long" or
                    (strategy == "auto" and duration > 30)
                )

                # Convert to int16
                audio_int16 = (audio_array * 32767).astype(np.int16)

                # Transcribe
                model = _get_asr_model_instance()

                if use_long_audio:
                    # Use long audio processing
                    from src.asr.long_audio import process_long_audio

                    def transcribe_fn(audio):
                        return model.transcribe(audio)

                    transcript, _ = process_long_audio(
                        audio_path=tmp_file_path,
                        transcribe_fn=transcribe_fn,
                        strategy="hybrid"
                    )
                else:
                    # Simple transcription
                    transcript = model.transcribe(audio_int16)

                # Apply post-processing
                processed_transcript = None
                if apply_postprocess and transcript:
                    result = processor.process(transcript)
                    processed_transcript = result.processed

                # Update result
                file_result.success = True
                file_result.transcript = transcript
                file_result.processed_transcript = processed_transcript
                file_result.duration = duration

                successful += 1

            finally:
                # Clean up temp file
                import os
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        except Exception as e:
            file_result.error = str(e)
            failed += 1

        results.append(file_result)

    processing_time = time.time() - start_time

    return BatchTranscriptionResponse(
        total_files=len(files),
        successful=successful,
        failed=failed,
        results=results,
        total_duration=total_duration,
        processing_time=processing_time
    )


# Job queue router
job_router = APIRouter(prefix="/api/jobs", tags=["Job Queue"])


class JobSubmitResponse(BaseModel):
    """Response for job submission"""
    job_id: str
    status: str
    message: str


@job_router.post("/submit", response_model=JobSubmitResponse)
async def submit_job(
    file: UploadFile = File(...),
    strategy: str = "hybrid",
    merge_strategy: str = "simple",
    apply_postprocess: bool = True
):
    """
    Submit a transcription job to the queue

    Returns immediately with a job_id. Use GET /api/jobs/{job_id} to check status.

    Args:
        file: Audio file (WAV, MP3, M4A, etc.)
        strategy: Chunking strategy
        merge_strategy: Transcript merging strategy
        apply_postprocess: Whether to apply text post-processing

    Returns:
        Job submission response with job_id
    """
    import tempfile

    # Read file data
    file_data = await file.read()
    file_format = file.filename.split('.')[-1] if '.' in file.filename else None

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as tmp_file:
        tmp_file.write(file_data)
        tmp_file_path = tmp_file.name

    # Define the task
    async def process_task():
        from src.asr.long_audio import process_long_audio

        def transcribe_fn(audio):
            model = _get_asr_model_instance()
            return model.transcribe(audio)

        transcript, metadata = process_long_audio(
            audio_path=tmp_file_path,
            transcribe_fn=transcribe_fn,
            strategy=strategy,
            merge_strategy=merge_strategy
        )

        # Apply post-processing
        processed_transcript = None
        if apply_postprocess and transcript:
            result = processor.process(transcript)
            processed_transcript = result.processed

        return {
            "transcript": transcript,
            "processed_transcript": processed_transcript,
            "metadata": metadata
        }

    # Submit to queue
    job_id = await job_queue.submit(
        task=process_task,
        metadata={
            "filename": file.filename,
            "strategy": strategy,
            "merge_strategy": merge_strategy
        }
    )

    return JobSubmitResponse(
        job_id=job_id,
        status="submitted",
        message="Job submitted successfully. Use GET /api/jobs/{job_id} to check status."
    )


@job_router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100
):
    """
    List all jobs

    Args:
        status: Filter by status (pending, processing, completed, failed, cancelled)
        limit: Maximum number of jobs to return

    Returns:
        List of job information
    """
    from api.job_queue import JobStatus

    job_status = JobStatus(status) if status else None
    jobs = job_queue.list_jobs(status=job_status, limit=limit)

    return {
        "jobs": [JobInfo.from_job(j) for j in jobs],
        "count": len(jobs)
    }


@job_router.get("/stats")
async def get_queue_stats():
    """
    Get queue statistics

    Returns:
        Queue statistics including job counts and concurrency limits
    """
    return job_queue.get_stats()


@job_router.get("/{job_id}", response_model=JobInfo)
async def get_job_status(job_id: str):
    """
    Get job status and results

    Args:
        job_id: Job identifier

    Returns:
        Job information including status, progress, and results if completed
    """
    job = job_queue.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobInfo.from_job(job)


@job_router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a pending job

    Args:
        job_id: Job identifier

    Returns:
        Cancellation result
    """
    success = job_queue.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be cancelled (may be already completed or running)"
        )

    return {"success": True, "message": "Job cancelled successfully"}

# AI Post-processing endpoint (can be toggled)
@router.post("/ai-enhance")
async def ai_enhance_text(request: AIRequest):
    """
    AI-based text enhancement using multiple LLM providers

    This endpoint provides intelligent text processing including:
    - Grammar and fluency improvements
    - List formatting
    - Number conversion (Chinese text → Arabic numerals)
    - Paragraph organization
    - Filler word removal
    - Support for Chinese-English mixed text

    Supported providers:
    - openai: GPT-4o, GPT-4o-mini, etc.
    - gemini: Gemini Pro, Gemini Flash, etc.
    - ollama: Local models (optional)

    Args:
        request: AI enhancement request with text and provider options

    Returns:
        Enhanced text

    Examples:
        # Use OpenAI (default)
        POST /api/asr/ai-enhance
        {
            "text": "嗯 那个 五个 事情 首先 我们需要...",
            "provider": "openai",
            "model": "gpt-4o-mini"
        }

        # Use Gemini
        POST /api/asr/ai-enhance
        {
            "text": "嗯 那个 五个 事情 首先 我们需要...",
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp"
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    if not request.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    logger.info(f"🤖 AI enhancement request: {len(request.text)} chars, provider={request.provider}")

    try:
        # Create AI processor
        ai_processor = AIPostProcessor()

        # Process
        response = await ai_processor.process(request)

        logger.info(f"✅ AI enhancement complete: {len(response.processed)} chars")
        return {
            "original": response.original,
            "enhanced": response.processed,
            "provider": response.provider,
            "model": response.model
        }
    except Exception as e:
        logger.error(f"❌ AI enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


# Include postprocess router in the main router
router.include_router(postprocess_router)

