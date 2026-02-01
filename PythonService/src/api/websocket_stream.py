"""
WebSocket Streaming with Progress Updates
Real-time transcription with detailed progress tracking for long audio files
"""

import uuid
import asyncio
from typing import Dict, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import numpy as np
from datetime import datetime

from src.asr.model_config import model_manager
from src.asr.whisper_model import WhisperASR
from src.asr.model import AudioConfig
from src.asr.long_audio import LongAudioProcessor, AudioSegment, TranscriptionSegment


class ProgressUpdate(BaseModel):
    """Progress update message"""
    type: str  # "progress", "segment_complete", "error", "complete"
    session_id: str
    current_segment: int
    total_segments: int
    progress_percent: float
    message: str
    transcript_part: Optional[str] = None
    is_final: bool = False


class StreamingSession:
    """Manages a streaming session with progress tracking"""

    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.audio_chunks: List[np.ndarray] = []
        self.transcripts: List[TranscriptionSegment] = []
        self.started = False
        self.stopped = False
        self.created_at = datetime.now()

    async def send_progress(
        self,
        type: str,
        current_segment: int,
        total_segments: int,
        message: str,
        transcript_part: Optional[str] = None,
        is_final: bool = False
    ):
        """Send progress update to client"""
        progress = ProgressUpdate(
            type=type,
            session_id=self.session_id,
            current_segment=current_segment,
            total_segments=total_segments,
            progress_percent=(current_segment / total_segments * 100) if total_segments > 0 else 0,
            message=message,
            transcript_part=transcript_part,
            is_final=is_final
        )
        await self.websocket.send_json(progress.dict())


class WebSocketStreamer:
    """Enhanced WebSocket streaming with progress updates"""

    def __init__(self):
        self.active_sessions: Dict[str, StreamingSession] = {}

    async def handle_streaming_session(self, websocket: WebSocket):
        """
        Handle WebSocket connection for streaming with progress

        Protocol:
        Client sends:
        - {"action": "start", "strategy": "hybrid"} - Start session
        - <binary audio data> - Send audio chunk
        - {"action": "process"} - Process accumulated audio with long audio
        - {"action": "stop"} - Stop and get final result

        Server sends:
        - {"type": "started", "session_id": "..."}
        - {"type": "chunk_received", "chunk_number": N}
        - {"type": "progress", "current_segment": N, "total_segments": M, "progress_percent": 50.0}
        - {"type": "segment_complete", "transcript_part": "...", "current_segment": N, "total_segments": M}
        - {"type": "complete", "final_transcript": "...", "total_segments": M}
        - {"type": "error", "message": "..."}
        """
        await websocket.accept()

        session_id = str(uuid.uuid4())
        session = StreamingSession(session_id, websocket)
        self.active_sessions[session_id] = session

        try:
            # Send session started message
            await websocket.send_json({
                "type": "started",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })

            while True:
                data = await websocket.receive()

                if "text" in data:
                    # JSON message
                    import json
                    message = json.loads(data["text"])
                    action = message.get("action")

                    if action == "start" and not session.started:
                        # Start streaming session
                        session.started = True
                        await websocket.send_json({
                            "type": "ready",
                            "message": "Ready to receive audio chunks",
                            "session_id": session_id
                        })

                    elif action == "process":
                        # Process accumulated audio with long audio
                        await self._process_long_audio(
                            session,
                            strategy=message.get("strategy", "hybrid"),
                            merge_strategy=message.get("merge_strategy", "simple"),
                            apply_postprocess=message.get("apply_postprocess", True)
                        )

                    elif action == "stop":
                        # Stop session
                        await self._stop_session(session)
                        break

                elif "bytes" in data and session.started and not session.stopped:
                    # Binary audio data
                    audio_bytes = data["bytes"]
                    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                    session.audio_chunks.append(audio_array)

                    # Acknowledge chunk receipt
                    await websocket.send_json({
                        "type": "chunk_received",
                        "chunk_number": len(session.audio_chunks),
                        "session_id": session_id
                    })

        except WebSocketDisconnect:
            # Client disconnected
            pass
        except Exception as e:
            # Send error message
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "session_id": session_id
                })
            except:
                pass
        finally:
            # Cleanup
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

    async def _process_long_audio(
        self,
        session: StreamingSession,
        strategy: str,
        merge_strategy: str,
        apply_postprocess: bool
    ):
        """Process accumulated audio with progress updates"""

        if not session.audio_chunks:
            await session.websocket.send_json({
                "type": "error",
                "message": "No audio chunks received"
            })
            return

        try:
            # Combine all audio chunks
            await session.send_progress(
                type="progress",
                current_segment=0,
                total_segments=1,
                message="Combining audio chunks..."
            )

            all_audio = np.concatenate(session.audio_chunks)
            duration = len(all_audio) / 16000.0  # Assume 16kHz

            await session.send_progress(
                type="progress",
                current_segment=0,
                total_segments=1,
                message=f"Audio duration: {duration:.1f}s. Splitting into segments..."
            )

            # Use LongAudioProcessor to split
            processor = LongAudioProcessor()
            segments = processor.split_hybrid(all_audio, max_chunk_duration=30.0)

            total_segments = len(segments)

            await session.send_progress(
                type="progress",
                current_segment=0,
                total_segments=total_segments,
                message=f"Split into {total_segments} segments. Starting transcription..."
            )

            # Transcribe each segment with progress updates
            config = AudioConfig(sample_rate=16000, channels=1, bit_depth=16)
            model = WhisperASR(config=config, model_size=model_manager.current_model_size)
            transcripts = []

            for i, segment in enumerate(segments):
                # Send progress update
                await session.send_progress(
                    type="progress",
                    current_segment=i + 1,
                    total_segments=total_segments,
                    message=f"Processing segment {i + 1}/{total_segments} ({segment.end_time - segment.start_time:.1f}s)..."
                )

                # Convert to int16 if needed
                if segment.audio.dtype == np.float32:
                    audio_int16 = (segment.audio * 32767).astype(np.int16)
                else:
                    audio_int16 = segment.audio

                # Transcribe
                text = model.transcribe(audio_int16)

                transcripts.append(TranscriptionSegment(
                    text=text,
                    start_time=segment.start_time,
                    end_time=segment.end_time
                ))

                # Send segment complete update
                await session.send_progress(
                    type="segment_complete",
                    current_segment=i + 1,
                    total_segments=total_segments,
                    message=f"Segment {i + 1}/{total_segments} complete",
                    transcript_part=text
                )

            # Merge transcripts
            await session.send_progress(
                type="progress",
                current_segment=total_segments,
                total_segments=total_segments,
                message="Merging transcripts..."
            )

            full_transcript = processor.merge_transcripts(transcripts, merge_strategy=merge_strategy)

            # Apply post-processing if requested
            processed_transcript = None
            if apply_postprocess and full_transcript:
                from postprocess.processor import TextProcessor
                text_processor = TextProcessor()
                result = text_processor.process(full_transcript)
                processed_transcript = result.processed

            # Send final result
            await session.websocket.send_json({
                "type": "complete",
                "session_id": session.session_id,
                "final_transcript": full_transcript,
                "processed_transcript": processed_transcript,
                "total_segments": total_segments,
                "duration": duration,
                "strategy": strategy,
                "merge_strategy": merge_strategy
            })

            session.stopped = True

        except Exception as e:
            await session.websocket.send_json({
                "type": "error",
                "message": f"Error processing audio: {str(e)}",
                "session_id": session.session_id
            })

    async def _stop_session(self, session: StreamingSession):
        """Stop session and return results"""

        if not session.audio_chunks:
            await session.websocket.send_json({
                "type": "complete",
                "session_id": session.session_id,
                "final_transcript": "",
                "total_segments": 0,
                "message": "No audio received"
            })
            return

        # If not already processed, do simple transcription
        if not session.stopped:
            all_audio = np.concatenate(session.audio_chunks)
            config = AudioConfig(sample_rate=16000, channels=1, bit_depth=16)
            model = WhisperASR(config=config, model_size=model_manager.current_model_size)
            transcript = model.transcribe(all_audio)

            await session.websocket.send_json({
                "type": "complete",
                "session_id": session.session_id,
                "final_transcript": transcript,
                "total_segments": 1,
                "message": "Processing complete"
            })

        session.stopped = True

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions.keys())

    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.active_sessions)


# Global streamer instance
streamer = WebSocketStreamer()
