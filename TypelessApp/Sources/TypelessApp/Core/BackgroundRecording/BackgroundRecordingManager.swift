import Foundation
import AVFoundation
import AppKit
import os.log

/// Background recording manager
/// Handles recording without UI, triggered by global hotkey
@MainActor
class BackgroundRecordingManager: AudioRecorderDelegate {
    // MARK: - Properties

    private var audioRecorder: RealtimeAudioRecorder?
    private var asrService: ASRService
    private var textInjector: TextInjector
    private var powerMode: PowerModeManager
    private var previewWindow: PreviewWindow?
    private var sessionId: String?

    private(set) var isRecording = false

    /// Buffer for audio chunks received before session is ready
    private var pendingAudioChunks: [Data] = []

    /// Flag to track if pending chunks are being sent
    private var isSendingPendingChunks = false

    private let logger = OSLog(subsystem: "com.typeless.app", category: "BackgroundRecording")

    // MARK: - Initialization

    init() {
        self.asrService = ASRService()
        self.textInjector = TextInjector()
        self.powerMode = PowerModeManager()
        self.previewWindow = PreviewWindow()
        self.audioRecorder = RealtimeAudioRecorder()
        self.audioRecorder?.delegate = self

        // Pre-initialize recorder to reduce startup latency
        Task {
            await self.audioRecorder?.prepareRecorder()
        }
    }

    // MARK: - Recording Control

    /// Toggle recording state
    func toggleRecording() async {
        if isRecording {
            await stopRecording()
        } else {
            await startRecording()
        }
    }

    /// Start background recording
    func startRecording() async {
        NSLog("🎙️ [Background] Starting recording...")

        do {
            // Detect current app for Power Mode
            _ = powerMode.detectAndUpdate()
            NSLog("📱 [Background] Power Mode: \(powerMode.getCategory())")

            // Clear any pending chunks from previous session
            pendingAudioChunks.removeAll()

            // Start audio recorder FIRST (don't wait for network)
            // This ensures audio is captured immediately when user presses the key
            guard let recorder = audioRecorder else {
                throw NSError(domain: "BackgroundRecording", code: -1, userInfo: [NSLocalizedDescriptionKey: "No audio recorder available"])
            }
            try await recorder.startRecording()

            // Mark as recording immediately so audio chunks are accepted
            isRecording = true
            NSLog("✅ [Background] Recording started (audio capturing)")

            // Then create ASR session in background (this may take time due to network)
            Task {
                do {
                    let appInfo = getAppInfo()
                    let newSessionId = try await asrService.startSession(appInfo: appInfo)
                    self.sessionId = newSessionId
                    NSLog("✅ [Background] Session started (ready to receive audio)")

                    // Send any pending audio chunks that were received while waiting for session
                    // This is critical even if user has stopped recording - ensures audio is not lost
                    await sendPendingAudioChunks()

                    // If user has already stopped recording (isRecording is false), trigger finalize now
                    // This ensures pending chunks are processed before stopSession
                    if !self.isRecording && !self.pendingAudioChunks.isEmpty {
                        NSLog("⏳ [Background] User stopped during session creation, finalizing...")
                        // Don't call finalizeStopRecording here as it needs to be called from delegate
                        // The pending chunks are already sent above
                    }
                } catch {
                    NSLog("❌ [Background] Failed to create session: \(error.localizedDescription)")
                    // Don't stop recording, just log the error
                    // The user can still cancel manually
                }
            }
        } catch {
            NSLog("❌ [Background] Failed to start: \(error.localizedDescription)")
            isRecording = false
            pendingAudioChunks.removeAll()
        }
    }

    /// Send any pending audio chunks that were buffered before session was ready
    private func sendPendingAudioChunks() async {
        guard let sessionId = sessionId else { return }
        guard !isSendingPendingChunks else { return }

        isSendingPendingChunks = true
        defer { isSendingPendingChunks = false }

        let chunksToSend = pendingAudioChunks
        pendingAudioChunks.removeAll()

        guard !chunksToSend.isEmpty else { return }

        NSLog("📤 [Background] Sending \(chunksToSend.count) pending audio chunks...")

        for (index, data) in chunksToSend.enumerated() {
            do {
                let transcript = try await asrService.sendAudio(sessionId: sessionId, audioData: data)
                if !transcript.isEmpty {
                    NSLog("📝 [Background] Preview from pending chunk \(index+1): \(transcript.prefix(50))...")
                    previewWindow?.updateText(transcript)
                }
            } catch {
                NSLog("❌ [Background] Failed to send pending chunk \(index+1): \(error.localizedDescription)")
            }
        }

        NSLog("✅ [Background] Finished sending pending chunks")
    }

    /// Get current app information
    private func getAppInfo() -> String {
        let app = NSWorkspace.shared.frontmostApplication
        let bundleId = app?.bundleIdentifier ?? "unknown"
        let appName = app?.localizedName ?? "Unknown"
        return "\(appName)|\(bundleId)"
    }

    /// Stop background recording and inject text
    func stopRecording() async {
        NSLog("⏹️ [Background] Stopping recording...")

        guard let recorder = audioRecorder else {
            NSLog("❌ [Background] No recorder")
            return
        }

        // Stop recording - this will trigger final chunk send
        // The actual stop and cleanup will happen in audioRecorderDidFinishSendingFinalChunk
        recorder.stopRecording()
        // Don't set isRecording = false yet - wait for final chunk to be sent
    }

    /// Called when final audio chunk has been sent
    private func finalizeStopRecording() async {
        NSLog("⏹️ [Background] Finalizing stop recording...")

        // Now stop the recorder completely
        audioRecorder?.finishStopping()
        isRecording = false

        // Wait for any pending chunks to finish sending (from earlier sendPendingAudioChunks call)
        if isSendingPendingChunks {
            NSLog("⏳ [Background] Waiting for pending chunks to finish sending...")
            // Give it a short time to complete (max 2 seconds)
            var attempts = 0
            while isSendingPendingChunks && attempts < 20 {
                try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
                attempts += 1
            }
        }

        // If we have a session, send remaining pending chunks and stop
        if let sessionId = sessionId {
            // Send any remaining pending chunks
            if !pendingAudioChunks.isEmpty {
                NSLog("📤 [Background] Sending remaining pending chunks before stop...")
                await sendPendingAudioChunks()
            }

            do {
                let result = try await asrService.stopSession(sessionId: sessionId)
                let transcript = result.finalTranscript

                NSLog("📝 [Background] Transcript: \(transcript)")

                // Inject text if not empty
                if !transcript.isEmpty {
                    try await textInjector.inject(text: transcript)
                    NSLog("✅ [Background] Text injected successfully")
                } else {
                    NSLog("⚠️ [Background] Empty transcript, skipping injection")
                }
            } catch {
                NSLog("❌ [Background] Failed to stop session: \(error)")
            }
        }

        // Hide preview window
        previewWindow?.hide()

        // Clean up
        self.sessionId = nil
        self.pendingAudioChunks.removeAll()
    }

    /// Cancel recording without saving transcript
    func cancelRecording() async {
        NSLog("❌ [Background] Cancelling recording...")

        // Clear pending chunks
        pendingAudioChunks.removeAll()

        guard let recorder = audioRecorder else {
            NSLog("❌ [Background] No recorder to cancel")
            return
        }

        // Stop recording
        recorder.stopRecording()
        isRecording = false

        // Cancel ASR session (discard results)
        if let sessionId = sessionId {
            // Note: We don't call stopSession, just discard the session
            // The backend will timeout and clean up
            NSLog("🗑️ [Background] Discarded session: \(sessionId)")
        }

        // Hide preview window
        previewWindow?.hide()

        self.sessionId = nil

        NSLog("✅ [Background] Recording cancelled, transcript discarded")
    }

    // MARK: - AudioRecorderDelegate

    func audioRecorder(_ recorder: AnyObject, didOutputAudioBuffer buffer: AVAudioBuffer, data: Data, isFinal: Bool) {
        // 检查是否还在录音（防止停止后的延迟回调）
        guard isRecording else {
            NSLog("⚠️ [Background] Recording stopped, skipping audio chunk")
            return
        }

        // If no session yet, buffer the audio chunk for later
        guard let sessionId = sessionId else {
            NSLog("⏳ [Background] No session ID yet, buffering audio chunk (\(data.count) bytes)")
            pendingAudioChunks.append(data)
            return
        }

        Task {
            await sendAudioChunk(sessionId: sessionId, data: data, isFinal: isFinal, recorder: recorder)
        }
    }

    /// Send a single audio chunk
    private func sendAudioChunk(sessionId: String, data: Data, isFinal: Bool, recorder: AnyObject) async {
        do {
            let transcript = try await asrService.sendAudio(sessionId: sessionId, audioData: data)

            // Update preview window with partial transcript
            if !transcript.isEmpty {
                NSLog("📝 [Background] Preview: \(transcript.prefix(50))...")
                previewWindow?.updateText(transcript)
            }

            // If this is the final chunk, notify that we're done
            if isFinal {
                NSLog("✅ [Background] Final audio chunk sent successfully")
                audioRecorderDidFinishSendingFinalChunk(recorder)
            }
        } catch {
            NSLog("❌ [Background] Failed to send audio: \(error.localizedDescription)")
            // Even on error, if this is final chunk, we should proceed
            if isFinal {
                audioRecorderDidFinishSendingFinalChunk(recorder)
            }
        }
    }

    func audioRecorder(_ recorder: AnyObject, didEncounterError error: AudioRecorderError) {
        NSLog("❌ [Background] Audio recorder error: \(error.localizedDescription)")
    }

    func audioRecorderDidFinishSendingFinalChunk(_ recorder: AnyObject) {
        NSLog("✅ [Background] Final chunk confirmed sent, proceeding to stop session")
        Task {
            await finalizeStopRecording()
        }
    }
}
