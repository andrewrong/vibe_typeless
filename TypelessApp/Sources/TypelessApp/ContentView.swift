import SwiftUI
import AVFoundation
import os.log

let logger = OSLog(subsystem: "com.typeless.app", category: "Recording")

struct ContentView: View {
    // Recording manager
    @StateObject private var recordingManager = RecordingManager()

    var body: some View {
        VStack(spacing: 20) {
            // Title
            Text("Typeless")
                .font(.largeTitle)
                .fontWeight(.bold)

            // Status indicator
            HStack {
                Circle()
                    .fill(recordingManager.isRecording ? Color.red : Color.green)
                    .frame(width: 10, height: 10)

                Text(recordingManager.status)
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                if recordingManager.progress > 0 && recordingManager.progress < 1 {
                    Text(String(format: "%.0f%%", recordingManager.progress * 100))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            // Transcript preview
            ScrollView {
                Text(recordingManager.transcript.isEmpty ? "No transcript yet..." : recordingManager.transcript)
                    .font(.body)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
            .frame(height: 200)
            .background(Color.gray.opacity(0.1))
            .cornerRadius(10)

            // Progress bar
            if recordingManager.progress > 0 && recordingManager.progress < 1 {
                ProgressView(value: recordingManager.progress)
                    .padding(.horizontal)
            }

            // Control buttons
            HStack(spacing: 20) {
                // Record/Stop button
                Button(action: recordingManager.toggleRecording) {
                    HStack {
                        Image(systemName: recordingManager.isRecording ? "stop.circle.fill" : "mic.circle.fill")
                            .font(.title)
                        Text(recordingManager.isRecording ? "Stop" : "Record")
                    }
                    .padding()
                    .background(recordingManager.isRecording ? Color.red : Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
                .buttonStyle(.plain)
                .disabled(recordingManager.isRecording && recordingManager.progress > 0)

                // Inject text button
                Button(action: injectTranscript) {
                    HStack {
                        Image(systemName: "text.cursor")
                            .font(.title)
                        Text("Inject")
                    }
                    .padding()
                    .background(Color.green)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
                .buttonStyle(.plain)
                .disabled(recordingManager.transcript.isEmpty)
            }

            // Connection status
            HStack {
                Circle()
                    .fill(recordingManager.isConnected ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)

                Text(recordingManager.isConnected ? "Connected to Backend" : "Backend Disconnected")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(30)
        .frame(minWidth: 600, minHeight: 400)
        .onAppear {
            recordingManager.setupServices()
        }
    }

    // MARK: - Actions

    private func injectTranscript() {
        Task {
            do {
                let injector = TextInjector()
                try await injector.inject(text: recordingManager.transcript)
                recordingManager.status = "Text injected!"

                // Clear status after delay
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                recordingManager.status = "Ready"
            } catch {
                recordingManager.status = "Injection failed: \(error.localizedDescription)"
            }
        }
    }
}

// MARK: - Recording Manager

@MainActor
class RecordingManager: ObservableObject {
    @Published var isRecording = false
    @Published var transcript = ""
    @Published var status = "Ready"
    @Published var progress: Double = 0.0
    @Published var isConnected = false

    private var audioRecorder: AudioRecorder?
    private var asrService: ASRService
    private var sessionId: String? = nil

    init() {
        self.audioRecorder = AudioRecorder()
        self.asrService = ASRService()
        self.audioRecorder?.delegate = self
    }

    // MARK: - Public Methods

    func toggleRecording() {
        Task {
            if isRecording {
                await stopRecording()
            } else {
                await startRecording()
            }
        }
    }

    func setupServices() {
        // Connect to backend
        Task {
            let connected = await asrService.checkConnection()
            self.isConnected = connected
            self.status = connected ? "Connected to backend" : "Backend unavailable"
        }
    }

    // MARK: - Private Methods

    private func startRecording() async {
        os_log("🎙️ startRecording called", log: logger, type: .info)
        NSLog("🎙️ Typeless: startRecording called")
        isRecording = true
        status = "Connecting to backend..."
        NSLog("🔴 Status: Connecting to backend...")

        // Start ASR session
        do {
            sessionId = try await asrService.startSession()
            os_log("✅ Session started: %@", log: logger, type: .info, sessionId ?? "nil")
            NSLog("✅ Typeless: Session started: \(sessionId ?? "nil")")
            status = "Session started, preparing recorder..."
            NSLog("🔴 Status: Session started, preparing recorder...")
        } catch {
            os_log("❌ Failed to start session: %{public}@", log: logger, type: .error, error.localizedDescription)
            NSLog("❌ Typeless: Failed to start session: \(error.localizedDescription)")
            status = "Failed to connect: \(error.localizedDescription)"
            isRecording = false
            return
        }

        // Start recording
        guard let recorder = audioRecorder else {
            os_log("❌ Recorder not available", log: logger, type: .error)
            NSLog("❌ Typeless: Recorder not available")
            status = "Recorder not available"
            isRecording = false
            return
        }

        do {
            status = "Requesting microphone access..."
            NSLog("🔴 Status: Requesting microphone access...")
            try await recorder.startRecording()
            status = "Recording..."
            NSLog("✅ Typeless: Recording started successfully")
            os_log("✅ Recording started successfully", log: logger, type: .info)
        } catch {
            os_log("❌ Failed to start recording: %{public}@", log: logger, type: .error, error.localizedDescription)
            NSLog("❌ Typeless: Failed to start recording: \(error.localizedDescription)")
            status = "Failed to start: \(error.localizedDescription)"
            isRecording = false
        }
    }

    private func stopRecording() async {
        status = "Stopping..."
        progress = 1.0

        guard let recorder = audioRecorder else {
            status = "Recorder not available"
            isRecording = false
            progress = 0.0
            return
        }

        // Stop recording
        recorder.stopRecording()
        isRecording = false
        status = "Getting final transcript..."

        // Stop ASR session and get final transcript
        if let sessionId = sessionId {
            do {
                let result = try await asrService.stopSession(sessionId: sessionId)
                transcript = result.finalTranscript
                print("✅ Final transcript: \(result.finalTranscript)")
            } catch {
                print("❌ Failed to stop session: \(error)")
                status = "Failed to get transcript"
            }
            self.sessionId = nil
        }

        status = "Ready"
        progress = 0.0
    }
}

// MARK: - Audio Recorder Delegate

extension RecordingManager: AudioRecorderDelegate {
    nonisolated func audioRecorder(_ recorder: AudioRecorder, didOutputAudioBuffer buffer: AVAudioBuffer, data: Data) {
        print("📤 Audio chunk received: \(data.count) bytes")

        Task { @MainActor in
            guard let sessionId = self.sessionId else {
                print("❌ No session ID")
                return
            }

            do {
                // Send audio to backend for processing
                _ = try await self.asrService.sendAudio(sessionId: sessionId, audioData: data)
                // Don't update transcript during recording - only show final result
                print("📝 Audio chunk sent to backend")
            } catch {
                print("❌ Failed to send audio: \(error)")
            }
        }
    }

    nonisolated func audioRecorder(_ recorder: AudioRecorder, didEncounterError error: AudioRecorderError) {
        print("❌ Audio recorder error: \(error)")
        Task { @MainActor in
            self.status = "Recorder error: \(error.localizedDescription)"
            self.isRecording = false
        }
    }
}
