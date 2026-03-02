import Foundation
import AVFoundation
import AppKit
import os.log

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

    private let logger = OSLog(subsystem: "com.typeless.app", category: "BackgroundRecording")

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
                NSLog("🎙️ First audio buffer received - now recording")
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
            NSLog("🎙️ Starting recording...")
            _ = powerMode.detectAndUpdate()
            pendingAudioChunks.removeAll()

            guard let recorder = audioRecorder else {
                throw NSError(domain: "BackgroundRecording", code: -1, userInfo: [NSLocalizedDescriptionKey: "No audio recorder available"])
            }

            // Start audio recorder (creates engine and starts recording)
            NSLog("🎤 Starting audio recorder...")
            try await recorder.startRecording(sessionReady: false)

            // Create session with actual sample rate from hardware
            if sessionId == nil {
                NSLog("⏳ Creating session with sampleRate=\(Int(recorder.sampleRate))Hz...")
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo, sampleRate: Int(recorder.sampleRate))
                self.sessionId = newSessionId
                NSLog("✅ Session created with sampleRate=\(Int(recorder.sampleRate))Hz")

                // Start sending audio chunks now that session is ready
                recorder.markReadyToSend()
                NSLog("🎤 Audio recorder ready to send chunks")
            }

            totalAudioBytesSent = 0
            recordingStartTime = Date()
            // Don't reset hasRecordingStarted here - it will be set by onFirstBuffer callback
            isRecording = true

        } catch {
            NSLog("❌ Failed to start recording: \(error.localizedDescription)")
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
                NSLog("❌ Failed to send pending chunk: \(error.localizedDescription)")
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
        NSLog("⏹️ stopRecording() called - isRecording=\(isRecording), hasRecordingStarted=\(hasRecordingStarted)")
        guard let recorder = audioRecorder else {
            NSLog("❌ No audio recorder available")
            return
        }

        // If recording hasn't actually started yet (still in preparing state),
        // treat this as a cancel to avoid confusion
        if !hasRecordingStarted {
            NSLog("⚠️ Stop pressed before recording started - treating as cancel")
            await cancelRecording()
            return
        }

        NSLog("⏹️ Calling recorder.stopRecording()")
        recorder.stopRecording()
    }

    /// Called when final audio chunk has been sent
    private func finalizeStopRecording() async {
        NSLog("✅ finalizeStopRecording() called")
        audioRecorder?.finishStopping()
        isRecording = false

        // Wait for pending chunks
        if isSendingPendingChunks {
            NSLog("⏳ Waiting for pending chunks...")
            var attempts = 0
            while isSendingPendingChunks && attempts < 20 {
                try? await Task.sleep(nanoseconds: 100_000_000)
                attempts += 1
            }
            NSLog("✅ Pending chunks complete (attempts: \(attempts))")
        }

        // Handle session not found (404) by recreating session
        if sessionId == nil {
            NSLog("⚠️ Session ID is nil, creating new session...")
            do {
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo)
                self.sessionId = newSessionId
                NSLog("✅ New session created: \(newSessionId.prefix(8))...")
            } catch {
                NSLog("❌ Failed to create new session: \(error)")
                menuBarApp?.updateMenuBarState(.idle)
                return
            }
        }

        if let sessionId = sessionId {
            NSLog("📝 Stopping session: \(sessionId.prefix(8))...")

            if !pendingAudioChunks.isEmpty {
                NSLog("📤 Sending \(pendingAudioChunks.count) pending chunks...")
                await sendPendingAudioChunks()
            }

            NSLog("⏳ Waiting for backend processing...")
            try? await Task.sleep(nanoseconds: 500_000_000)

            do {
                NSLog("🔄 Calling stopSession API...")
                let result = try await asrService.stopSession(sessionId: sessionId)
                let transcript = result.finalTranscript
                NSLog("✅ Got transcript (\(transcript.count) chars): \(transcript.prefix(100))...")

                if !transcript.isEmpty {
                    NSLog("💉 Injecting text...")
                    try await textInjector.inject(text: transcript)
                    NSLog("✅ Text injected successfully")
                } else {
                    NSLog("⚠️ Transcript is empty, nothing to inject")
                }
            } catch ASRError.serverError(404, _) {
                // Session not found - backend may have restarted
                NSLog("⚠️ Session not found on stop (404), creating new session...")
                self.sessionId = nil

                do {
                    let appInfo = getAppInfo()
                    let newSessionId = try await asrService.startSession(appInfo: appInfo)
                    self.sessionId = newSessionId
                    NSLog("✅ New session created, retrying stop...")

                    // Retry stop with new session (though this will be a fresh empty session)
                    let result = try await asrService.stopSession(sessionId: newSessionId)
                    let transcript = result.finalTranscript
                    NSLog("✅ Retry stop successful, transcript (\(transcript.count) chars)")
                    if !transcript.isEmpty {
                        try await textInjector.inject(text: transcript)
                        NSLog("✅ Text injected (retry path)")
                    }
                } catch {
                    NSLog("❌ Failed to recreate session: \(error.localizedDescription)")
                }
            } catch {
                NSLog("❌ Failed to stop session: \(error)")
            }
        } else {
            NSLog("⚠️ No session ID available for stop")
        }

        NSLog("🧹 Cleaning up...")
        menuBarApp?.updateMenuBarState(.idle)
        self.pendingAudioChunks.removeAll()
        self.sessionId = nil
        self.hasRecordingStarted = false
        NSLog("✅ Cleanup complete")

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
        NSLog("❌ Recording cancelled")
    }

    /// Send a single audio chunk
    /// Handles session not found (404) by automatically recreating the session
    private func sendAudioChunk(sessionId: String, data: Data, isFinal: Bool) async {
        do {
            let transcript = try await asrService.sendAudio(sessionId: sessionId, audioData: data)
            if !transcript.isEmpty {
                NSLog("📝 Preview: \(transcript.prefix(50))...")
            }
        } catch ASRError.serverError(404, _) {
            // Session not found - backend may have restarted
            NSLog("⚠️ Session not found (404), recreating session...")
            self.sessionId = nil

            // Create new session
            do {
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo)
                self.sessionId = newSessionId
                NSLog("✅ New session created: \(newSessionId.prefix(8))...")

                // Retry sending the audio chunk with new session
                let transcript = try await asrService.sendAudio(sessionId: newSessionId, audioData: data)
                if !transcript.isEmpty {
                    NSLog("📝 Preview (after retry): \(transcript.prefix(50))...")
                }
            } catch {
                NSLog("❌ Failed to recreate session: \(error.localizedDescription)")
            }
        } catch {
            NSLog("❌ Failed to send audio: \(error.localizedDescription)")
        }
    }
}
