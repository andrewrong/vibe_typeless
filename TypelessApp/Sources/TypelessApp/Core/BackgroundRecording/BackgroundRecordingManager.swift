import Foundation
import AVFoundation
import AppKit

/// Background recording manager
/// Handles recording without UI, triggered by global hotkey
@MainActor
class BackgroundRecordingManager {
    // MARK: - Properties

    private var audioRecorder: RealtimeAudioRecorder?
    private var asrService: ASRService
    private var textInjector: TextInjector
    private var powerMode: PowerModeManager
    private var sessionId: String?

    private(set) var isRecording = false

    /// Reference to menu bar app for status updates
    weak var menuBarApp: MenuBarApp?

    /// Buffer for audio chunks received before session is ready
    private var pendingAudioChunks: [Data] = []

    /// Flag to track if pending chunks are being sent
    private var isSendingPendingChunks = false

    /// Track total audio bytes sent for comparison with ASR result
    private var totalAudioBytesSent: Int = 0
    private var recordingStartTime: Date?

    /// Flag to track if recording has actually started (first buffer received)
    private var hasRecordingStarted = false

    // MARK: - Initialization

    init(menuBarApp: MenuBarApp? = nil) {
        self.asrService = ASRService()
        self.textInjector = TextInjector()
        self.powerMode = PowerModeManager()
        self.audioRecorder = RealtimeAudioRecorder()
        self.menuBarApp = menuBarApp

        setupRecorderCallbacks()

        // Note: prepareRecorder is now called when user presses hotkey
        // to avoid keeping microphone open (which forces HFP mode)
        // This allows A2DP music mode when not recording
    }

    private func setupRecorderCallbacks() {
        audioRecorder?.onAudioChunk = { [weak self] data, isFinal in
            Task { @MainActor in
                guard let self = self else { return }
                await self.handleAudioChunk(data: data, isFinal: isFinal)
            }
        }

        audioRecorder?.onFinished = { [weak self] in
            Task { @MainActor in
                guard let self = self else { return }
                await self.finalizeStopRecording()
            }
        }

        audioRecorder?.onFirstBuffer = { [weak self] in
            Task { @MainActor in
                guard let self = self else { return }
                self.hasRecordingStarted = true
                TLogInfo("🎙️ Recording started")
                self.menuBarApp?.updateMenuBarState(.recording)
            }
        }
    }

    private func handleAudioChunk(data: Data, isFinal: Bool) async {
        guard isRecording else { return }
        totalAudioBytesSent += data.count

        guard let sessionId = sessionId else {
            pendingAudioChunks.append(data)
            return
        }

        await sendAudioChunk(sessionId: sessionId, data: data, isFinal: isFinal)
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

    /// Pre-create ASR session so it's ready when user presses hotkey
    /// Note: Session is now created when recording starts (after sample rate is determined)
    func prepareNextSession() async {
        // Session creation deferred to startRecording when sample rate is known
        // This ensures backend receives correct sample rate for resampling
    }

    /// Start background recording
    func startRecording() async {
        do {
            menuBarApp?.updateMenuBarState(.preparing)
            TLogInfo("🎙️ Starting recording...")
            _ = powerMode.detectAndUpdate()
            pendingAudioChunks.removeAll()

            guard let recorder = audioRecorder else {
                throw NSError(domain: "BackgroundRecording", code: -1, userInfo: [NSLocalizedDescriptionKey: "No audio recorder available"])
            }

            // Start audio recorder (creates engine and starts recording)
            TLogDebug("Starting audio recorder...")
            try await recorder.startRecording(sessionReady: false)

            // Create session with actual sample rate from hardware
            if sessionId == nil {
                TLogInfo("⏳ Creating session (sampleRate=\(Int(recorder.sampleRate))Hz)...")
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo, sampleRate: Int(recorder.sampleRate))
                self.sessionId = newSessionId
                TLogInfo("✅ Session created")

                // Start sending audio chunks now that session is ready
                recorder.markReadyToSend()
                TLogDebug("Audio recorder ready")
            }

            totalAudioBytesSent = 0
            recordingStartTime = Date()
            // Don't reset hasRecordingStarted here - it will be set by onFirstBuffer callback
            isRecording = true

        } catch {
            TLogError("Failed to start recording: \(error.localizedDescription)")
            isRecording = false
            pendingAudioChunks.removeAll()
            menuBarApp?.updateMenuBarState(.idle)
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

        for (_, data) in chunksToSend.enumerated() {
            do {
                _ = try await asrService.sendAudio(sessionId: sessionId, audioData: data)
            } catch {
                TLogDebug("Failed to send pending chunk: \(error.localizedDescription)")
            }
        }
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
        TLogInfo("⏹️ Stopping recording...")
        guard let recorder = audioRecorder else {
            TLogError("No audio recorder available")
            return
        }

        // If recording hasn't actually started yet (still in preparing state),
        // treat this as a cancel to avoid confusion
        if !hasRecordingStarted {
            TLogDebug("Stop pressed before recording started - treating as cancel")
            await cancelRecording()
            return
        }

        recorder.stopRecording()
    }

    /// Called when final audio chunk has been sent
    private func finalizeStopRecording() async {
        TLogDebug("Finalizing stop recording...")
        audioRecorder?.finishStopping()
        isRecording = false

        // Wait for pending chunks
        if isSendingPendingChunks {
            TLogDebug("Waiting for pending chunks...")
            var attempts = 0
            while isSendingPendingChunks && attempts < 20 {
                try? await Task.sleep(nanoseconds: 100_000_000)
                attempts += 1
            }
        }

        // Handle session not found (404) by recreating session
        if sessionId == nil {
            TLogDebug("Session ID nil, creating new session...")
            do {
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo)
                self.sessionId = newSessionId
                TLogInfo("✅ New session created")
            } catch {
                TLogError("Failed to create new session: \(error)")
                menuBarApp?.updateMenuBarState(.idle)
                return
            }
        }

        if let sessionId = sessionId {
            TLogInfo("📝 Processing transcription...")

            if !pendingAudioChunks.isEmpty {
                TLogDebug("Sending \(pendingAudioChunks.count) pending chunks...")
                await sendPendingAudioChunks()
            }

            try? await Task.sleep(nanoseconds: 500_000_000)

            do {
                let result = try await asrService.stopSession(sessionId: sessionId)
                let transcript = result.finalTranscript

                if !transcript.isEmpty {
                    TLogInfo("✅ Got transcript (\(transcript.count) chars)")
                    try await textInjector.inject(text: transcript)
                    TLogInfo("✅ Text injected")
                } else {
                    TLogInfo("⚠️ Transcript empty")
                }
            } catch ASRError.serverError(404, _) {
                // Session not found - backend may have restarted
                TLogDebug("Session not found (404), recreating...")
                self.sessionId = nil

                do {
                    let appInfo = getAppInfo()
                    let newSessionId = try await asrService.startSession(appInfo: appInfo)
                    self.sessionId = newSessionId

                    // Retry stop with new session (though this will be a fresh empty session)
                    let result = try await asrService.stopSession(sessionId: newSessionId)
                    let transcript = result.finalTranscript
                    if !transcript.isEmpty {
                        try await textInjector.inject(text: transcript)
                        TLogInfo("✅ Text injected (retry)")
                    }
                } catch {
                    TLogError("Failed to recreate session: \(error.localizedDescription)")
                }
            } catch {
                TLogError("Failed to stop session: \(error)")
            }
        } else {
            TLogDebug("No session ID available")
        }

        menuBarApp?.updateMenuBarState(.idle)
        self.pendingAudioChunks.removeAll()
        self.sessionId = nil
        self.hasRecordingStarted = false
        TLogDebug("Cleanup complete")

        Task {
            await prepareNextSession()
        }
    }

    /// Cancel recording without saving transcript
    func cancelRecording() async {
        pendingAudioChunks.removeAll()
        audioRecorder?.stopRecording()
        isRecording = false
        hasRecordingStarted = false
        sessionId = nil
        menuBarApp?.updateMenuBarState(.idle)
        TLogInfo("❌ Recording cancelled")
    }

    /// Send a single audio chunk
    /// Handles session not found (404) by automatically recreating the session
    private func sendAudioChunk(sessionId: String, data: Data, isFinal: Bool) async {
        do {
            let transcript = try await asrService.sendAudio(sessionId: sessionId, audioData: data)
            if !transcript.isEmpty {
                TLogInfo("📝 Preview: \(transcript)")
            }
        } catch ASRError.serverError(404, _) {
            // Session not found - backend may have restarted
            TLogDebug("Session not found (404), recreating...")
            self.sessionId = nil

            // Create new session
            do {
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo)
                self.sessionId = newSessionId
                TLogInfo("✅ New session created (retry)")

                // Retry sending the audio chunk with new session
                let transcript = try await asrService.sendAudio(sessionId: newSessionId, audioData: data)
                if !transcript.isEmpty {
                    TLogInfo("📝 Preview: \(transcript)")
                }
            } catch {
                TLogError("Failed to recreate session: \(error.localizedDescription)")
            }
        } catch {
            TLogDebug("Failed to send audio: \(error.localizedDescription)")
        }
    }
}
