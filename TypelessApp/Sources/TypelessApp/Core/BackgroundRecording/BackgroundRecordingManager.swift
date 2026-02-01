import Foundation
import AVFoundation
import os.log

/// Background recording manager
/// Handles recording without UI, triggered by global hotkey
@MainActor
class BackgroundRecordingManager: AudioRecorderDelegate {
    // MARK: - Properties

    private var audioRecorder: AudioRecorder?
    private var asrService: ASRService
    private var textInjector: TextInjector
    private var sessionId: String?

    private(set) var isRecording = false

    private let logger = OSLog(subsystem: "com.typeless.app", category: "BackgroundRecording")

    // MARK: - Initialization

    init() {
        self.asrService = ASRService()
        self.textInjector = TextInjector()
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
            // Start ASR session
            sessionId = try await asrService.startSession()
            NSLog("✅ [Background] Session started: \(sessionId ?? "nil")")

            // Start audio recorder
            try await audioRecorder?.startRecording()
            isRecording = true
            NSLog("✅ [Background] Recording started")
        } catch {
            NSLog("❌ [Background] Failed to start: \(error.localizedDescription)")
            isRecording = false
        }
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

        self.sessionId = nil
    }

    // MARK: - AudioRecorderDelegate

    nonisolated func audioRecorder(_ recorder: AudioRecorder, didOutputAudioBuffer buffer: AVAudioBuffer, data: Data) {
        Task { @MainActor in
            guard let sessionId = sessionId else {
                NSLog("⚠️ [Background] No session ID, skipping audio chunk")
                return
            }

            do {
                let transcript = try await asrService.sendAudio(sessionId: sessionId, audioData: data)
                // Optionally log partial transcript
                if !transcript.isEmpty {
                    NSLog("📝 [Background] Partial: \(transcript)")
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
