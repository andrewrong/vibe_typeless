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

        Task {
            await self.audioRecorder?.prepareRecorder()
            await prepareNextSession()
        }
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
    func prepareNextSession() async {
        guard sessionId == nil else { return }
        do {
            let appInfo = getAppInfo()
            let newSessionId = try await asrService.startSession(appInfo: appInfo)
            self.sessionId = newSessionId
        } catch {
            NSLog("⚠️ Failed to pre-create session: \(error.localizedDescription)")
        }
    }

    /// Start background recording
    func startRecording() async {
        do {
            menuBarApp?.updateMenuBarState(.preparing)
            NSLog("🎙️ Starting recording...")
            _ = powerMode.detectAndUpdate()
            pendingAudioChunks.removeAll()

            // Create session if needed
            if sessionId == nil {
                NSLog("⏳ Creating session...")
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo)
                self.sessionId = newSessionId
                NSLog("✅ Session created")
            }

            guard let recorder = audioRecorder else {
                throw NSError(domain: "BackgroundRecording", code: -1, userInfo: [NSLocalizedDescriptionKey: "No audio recorder available"])
            }

            NSLog("🎤 Starting audio recorder...")
            try recorder.startRecording(sessionReady: sessionId != nil)

            totalAudioBytesSent = 0
            recordingStartTime = Date()
            hasRecordingStarted = false
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
        guard let recorder = audioRecorder else { return }

        // If recording hasn't actually started yet (still in preparing state),
        // treat this as a cancel to avoid confusion
        if !hasRecordingStarted {
            NSLog("⚠️ Stop pressed before recording started - treating as cancel")
            await cancelRecording()
            return
        }

        recorder.stopRecording()
    }

    /// Called when final audio chunk has been sent
    private func finalizeStopRecording() async {
        audioRecorder?.finishStopping()
        isRecording = false

        // Wait for pending chunks
        if isSendingPendingChunks {
            var attempts = 0
            while isSendingPendingChunks && attempts < 20 {
                try? await Task.sleep(nanoseconds: 100_000_000)
                attempts += 1
            }
        }

        // Handle session not found (404) by recreating session
        if sessionId == nil {
            do {
                let appInfo = getAppInfo()
                let newSessionId = try await asrService.startSession(appInfo: appInfo)
                self.sessionId = newSessionId
            } catch {
                menuBarApp?.updateMenuBarState(.idle)
                return
            }
        }

        if let sessionId = sessionId {
            if !pendingAudioChunks.isEmpty {
                await sendPendingAudioChunks()
            }

            try? await Task.sleep(nanoseconds: 500_000_000)

            do {
                let result = try await asrService.stopSession(sessionId: sessionId)
                let transcript = result.finalTranscript

                if !transcript.isEmpty {
                    try await textInjector.inject(text: transcript)
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
                    if !transcript.isEmpty {
                        try await textInjector.inject(text: transcript)
                    }
                } catch {
                    NSLog("❌ Failed to recreate session: \(error.localizedDescription)")
                }
            } catch {
                NSLog("❌ Failed to stop session: \(error)")
            }
        }

        menuBarApp?.updateMenuBarState(.idle)
        self.pendingAudioChunks.removeAll()
        self.sessionId = nil
        self.hasRecordingStarted = false

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
