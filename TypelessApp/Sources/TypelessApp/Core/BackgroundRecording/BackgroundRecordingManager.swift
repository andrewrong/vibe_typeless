import Foundation
import AVFoundation
import AppKit
import os.log

/// Background recording manager
/// Handles recording without UI, triggered by global hotkey
@MainActor
class BackgroundRecordingManager: AudioRecorderDelegate {
    // MARK: - Properties

    private var audioRecorder: AudioRecorder?
    private var asrService: ASRService
    private var textInjector: TextInjector
    private var powerMode: PowerModeManager
    private var previewWindow: PreviewWindow?
    private var sessionId: String?

    private(set) var isRecording = false

    private let logger = OSLog(subsystem: "com.typeless.app", category: "BackgroundRecording")

    // MARK: - Initialization

    init() {
        self.asrService = ASRService()
        self.textInjector = TextInjector()
        self.powerMode = PowerModeManager()
        self.previewWindow = PreviewWindow()
        self.audioRecorder = AudioRecorder()
        self.audioRecorder?.delegate = self
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

            // Start ASR session
            let appInfo = getAppInfo()
            sessionId = try await asrService.startSession(appInfo: appInfo)
            NSLog("✅ [Background] Session started")

            // Start audio recorder
            guard let recorder = audioRecorder else {
                throw NSError(domain: "BackgroundRecording", code: -1, userInfo: [NSLocalizedDescriptionKey: "No audio recorder available"])
            }
            try await recorder.startRecording()
            isRecording = true
            NSLog("✅ [Background] Recording started")
        } catch {
            NSLog("❌ [Background] Failed to start: \(error.localizedDescription)")
            isRecording = false
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
        NSLog("⏹️ [Background] Stopping recording...")

        guard let recorder = audioRecorder else {
            NSLog("❌ [Background] No recorder")
            return
        }

        // Stop recording
        recorder.stopRecording()
        isRecording = false

        // Get final transcript
        guard let sessionId = sessionId else {
            NSLog("❌ [Background] No session ID")
            return
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

        // Hide preview window
        previewWindow?.hide()

        self.sessionId = nil
    }

    /// Cancel recording without saving transcript
    func cancelRecording() async {
        NSLog("❌ [Background] Cancelling recording...")

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

    nonisolated func audioRecorder(_ recorder: AudioRecorder, didOutputAudioBuffer buffer: AVAudioBuffer, data: Data) {
        Task { @MainActor in
            // 检查是否还在录音（防止停止后的延迟回调）
            guard isRecording else {
                NSLog("⚠️ [Background] Recording stopped, skipping audio chunk")
                return
            }

            guard let sessionId = sessionId else {
                NSLog("⚠️ [Background] No session ID, skipping audio chunk")
                return
            }

            do {
                let transcript = try await asrService.sendAudio(sessionId: sessionId, audioData: data)

                // Update preview window with partial transcript
                if !transcript.isEmpty {
                    NSLog("📝 [Background] Preview: \(transcript.prefix(50))...")
                    previewWindow?.updateText(transcript)
                }
            } catch {
                NSLog("❌ [Background] Failed to send audio: \(error.localizedDescription)")
            }
        }
    }

    nonisolated func audioRecorder(_ recorder: AudioRecorder, didEncounterError error: AudioRecorderError) {
        NSLog("❌ [Background] Audio recorder error: \(error.localizedDescription)")
    }
}
