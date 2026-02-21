import AVFoundation
import Foundation
import Cocoa

// Note: AudioRecorderError and AudioRecorderDelegate are defined in AudioRecorderTypes.swift

/// Audio recorder for capturing system audio
@MainActor
class AudioRecorder: NSObject, AVAudioRecorderDelegate {
    // MARK: - Properties

    private var audioRecorder: AVAudioRecorder?
    private var recordingTimer: Timer?
    private var audioFileURL: URL?
    private var lastSentPosition: Int64 = 0

    weak var delegate: AudioRecorderDelegate?

    private(set) var isRecording = false
    private(set) var sampleRate: Double = 16000.0
    private(set) var channels: UInt32 = 1

    /// Flag to track if we're sending the final chunk
    private var isSendingFinalChunk = false

    // MARK: - Initialization

    override init() {
        super.init()
    }

    // MARK: - Configuration

    /// Request microphone permission
    func requestPermission() async -> Bool {
        #if os(macOS)
        let authStatus = AVCaptureDevice.authorizationStatus(for: .audio)

        switch authStatus {
        case .authorized:
            NSLog("🎤 Microphone permission already granted")
            return true
        case .notDetermined:
            NSLog("🎤 Requesting microphone permission...")
            return await withCheckedContinuation { continuation in
                AVCaptureDevice.requestAccess(for: .audio) { granted in
                    if granted {
                        NSLog("✅ Microphone permission granted")
                    } else {
                        NSLog("❌ Microphone permission denied")
                    }
                    continuation.resume(returning: granted)
                }
            }
        case .denied, .restricted:
            NSLog("❌ Microphone permission denied or restricted")
            return false
        @unknown default:
            NSLog("⚠️ Unknown microphone permission status")
            return false
        }
        #else
        return true
        #endif
    }

    // MARK: - Recording Control

    /// Pre-initialize recorder to reduce startup latency
    func prepareRecorder() async {
        // Check permission first (only if not already granted)
        if AVCaptureDevice.authorizationStatus(for: .audio) != .authorized {
            let hasPermission = await requestPermission()
            guard hasPermission else { return }
        }

        // Only create recorder if not already exists
        guard audioRecorder == nil else {
            NSLog("🎤 AudioRecorder: Already initialized")
            return
        }

        // Create temp file
        let tempDir = NSTemporaryDirectory()
        let tempFile = tempDir + "recording_\(UUID().uuidString).wav"
        let fileURL = URL(fileURLWithPath: tempFile)
        self.audioFileURL = fileURL

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: sampleRate,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsNonInterleaved: false
        ]

        guard let recorder = try? AVAudioRecorder(url: fileURL, settings: settings) else {
            return
        }

        self.audioRecorder = recorder
        recorder.delegate = self
        recorder.isMeteringEnabled = true
        NSLog("🎤 AudioRecorder: Pre-initialized and ready")
    }

    /// Start recording audio (optimized for minimal latency)
    func startRecording() async throws {
        NSLog("🎤 AudioRecorder: startRecording called")
        guard !isRecording else {
            NSLog("⚠️ AudioRecorder: Already recording")
            return
        }

        // Skip permission check - should already be done in prepareRecorder
        // This saves ~50-100ms of startup time

        // Use pre-initialized recorder if available
        if audioRecorder == nil {
            NSLog("⚠️ AudioRecorder: Not pre-initialized, creating now...")

            // Quick permission check using AVCaptureDevice (for macOS)
            let authStatus = AVCaptureDevice.authorizationStatus(for: .audio)
            guard authStatus == .authorized else {
                NSLog("❌ AudioRecorder: Permission not granted")
                throw AudioRecorderError.notAuthorized
            }

            let tempDir = NSTemporaryDirectory()
            let tempFile = tempDir + "recording_\(UUID().uuidString).wav"
            let fileURL = URL(fileURLWithPath: tempFile)
            self.audioFileURL = fileURL

            let settings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatLinearPCM),
                AVSampleRateKey: sampleRate,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsBigEndianKey: false,
                AVLinearPCMIsFloatKey: false,
                AVLinearPCMIsNonInterleaved: false
            ]

            guard let recorder = try? AVAudioRecorder(url: fileURL, settings: settings) else {
                NSLog("❌ AudioRecorder: Failed to create recorder")
                throw AudioRecorderError.configurationFailed
            }

            self.audioRecorder = recorder
            recorder.delegate = self
            recorder.isMeteringEnabled = true
        } else {
            NSLog("✅ AudioRecorder: Using pre-initialized recorder")
        }

        guard let recorder = audioRecorder else {
            throw AudioRecorderError.configurationFailed
        }

        NSLog("🎤 AudioRecorder: Starting recording...")
        if !recorder.record() {
            NSLog("❌ AudioRecorder: record() returned false")
            throw AudioRecorderError.recordingFailed(NSError(domain: "AudioRecorder", code: -1))
        }

        NSLog("✅ AudioRecorder: Recording started")
        isRecording = true
        lastSentPosition = 0

        // Start timer to read and send audio chunks
        startAudioChunkTimer()

        // Immediately trigger first chunk read after a very short delay (10ms)
        // This ensures the first chunk is sent as quickly as possible
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.01) { [weak self] in
            guard let self = self, self.isRecording else { return }
            NSLog("🎤 AudioRecorder: Sending initial chunk...")
            self.readAndSendAudioChunk(isFinal: false)
        }
    }

    /// Stop recording audio
    func stopRecording() {
        NSLog("🎤 AudioRecorder: stopRecording called")
        guard isRecording else {
            NSLog("⚠️ AudioRecorder: Not recording")
            return
        }

        // Stop timer first to prevent new chunks
        recordingTimer?.invalidate()
        recordingTimer = nil

        // Wait a short time to ensure final audio is written to file
        // This helps capture the last bit of audio before stopping
        Thread.sleep(forTimeInterval: 0.05) // 50ms delay

        // Mark that we're about to send the final chunk
        isSendingFinalChunk = true
        NSLog("🎤 AudioRecorder: Reading final audio chunk...")

        // Read and send final audio chunk
        readAndSendAudioChunk(isFinal: true)

        // Note: We don't stop the recorder or clean up here
        // We'll do that after the final chunk is confirmed sent
        // See audioRecorderDidFinishSendingFinalChunk
    }

    /// Called by delegate when final chunk has been sent
    func finishStopping() {
        NSLog("🎤 AudioRecorder: Finishing stop (final chunk sent)")

        // Stop recorder but keep it for reuse (minimize startup latency)
        audioRecorder?.stop()
        // Note: We don't nil audioRecorder here to enable reuse

        // Clean up temp file
        if let fileURL = audioFileURL {
            try? FileManager.default.removeItem(at: fileURL)
            // Create new file URL for next recording
            let tempDir = NSTemporaryDirectory()
            let tempFile = tempDir + "recording_\(UUID().uuidString).wav"
            self.audioFileURL = URL(fileURLWithPath: tempFile)
        }

        isSendingFinalChunk = false
        isRecording = false
        lastSentPosition = 0
        NSLog("✅ AudioRecorder: Recording stopped")

        // Re-configure recorder with new file URL for next recording
        if let fileURL = audioFileURL {
            let settings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatLinearPCM),
                AVSampleRateKey: sampleRate,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsBigEndianKey: false,
                AVLinearPCMIsFloatKey: false,
                AVLinearPCMIsNonInterleaved: false
            ]

            if let recorder = try? AVAudioRecorder(url: fileURL, settings: settings) {
                self.audioRecorder = recorder
                recorder.delegate = self
                recorder.isMeteringEnabled = true
                NSLog("🎤 AudioRecorder: Re-prepared for next recording")
            }
        }
    }

    // MARK: - Private Methods

    private func startAudioChunkTimer() {
        // Send audio chunks every 0.5 seconds
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self,
                      let recorder = self.audioRecorder,
                      recorder.isRecording,
                      self.audioFileURL != nil else {
                    return
                }

                self.readAndSendAudioChunk()
            }
        }
    }

    private func readAndSendAudioChunk(isFinal: Bool = false) {
        guard let fileURL = audioFileURL else {
            // If no file but this is final chunk, notify completion
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        // Read the current file size
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: fileURL.path),
              let fileSize = attributes[.size] as? Int64 else {
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        // Calculate how much new data we have
        let newPosition = fileSize
        let bytesToRead = Int(newPosition - lastSentPosition)

        guard bytesToRead > 0 else {
            // No new data, but if this is final chunk, still notify
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        // Read new audio data from file
        guard let handle = try? FileHandle(forReadingFrom: fileURL) else {
            NSLog("❌ Failed to open file handle")
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        handle.seek(toFileOffset: UInt64(lastSentPosition))
        let audioData = handle.readData(ofLength: bytesToRead)
        handle.closeFile()

        NSLog("📥 Raw file data: \(audioData.count) bytes (position \(lastSentPosition)->\(newPosition), final=\(isFinal))")

        // WAV file header parsing
        let wavHeaderSize: Int64 = 44
        var pcmData: Data = audioData

        // For PCM format with AVAudioRecorder settings, the header might be different
        // Let's check if we're still in the header region
        if lastSentPosition < wavHeaderSize {
            // We're in the header region, skip it
            let bytesToSkip = Int(wavHeaderSize - lastSentPosition)

            if audioData.count > bytesToSkip {
                // Part of this chunk is header, skip it
                pcmData = audioData.advanced(by: bytesToSkip)
                lastSentPosition = wavHeaderSize
                NSLog("⏭️ Skipped WAV header (\(bytesToSkip) bytes), remaining PCM: \(pcmData.count) bytes")
            } else {
                // Entire chunk is header, skip it all
                lastSentPosition = newPosition
                NSLog("⏭️ Entire chunk was header (\(audioData.count) bytes), skipping")
                if isFinal {
                    delegate?.audioRecorderDidFinishSendingFinalChunk(self)
                }
                return
            }
        } else {
            // Normal chunk - already past header
            lastSentPosition = newPosition
        }

        // Also skip any partial data that's not a complete sample
        // Int16 = 2 bytes per sample
        let sampleSize = 2
        let padding = pcmData.count % sampleSize
        if padding > 0 {
            pcmData = pcmData.dropLast(padding)
        }

        guard !pcmData.isEmpty else {
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        NSLog("📤 Audio chunk: \(pcmData.count) bytes (raw PCM, \(pcmData.count / 2) samples, final=\(isFinal))")

        // Create a dummy buffer for the delegate callback
        let frameCapacity = pcmData.count / sampleSize
        guard let format = AVAudioFormat(commonFormat: .pcmFormatInt16,
                                        sampleRate: sampleRate,
                                        channels: channels,
                                        interleaved: false) else {
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCapacity)) else {
            if isFinal {
                delegate?.audioRecorderDidFinishSendingFinalChunk(self)
            }
            return
        }

        buffer.frameLength = AVAudioFrameCount(frameCapacity)

        // Send to delegate - for final chunk, the delegate is responsible for calling finishStopping
        delegate?.audioRecorder(self, didOutputAudioBuffer: buffer, data: pcmData, isFinal: isFinal)
    }

    // MARK: - AVAudioRecorderDelegate

    nonisolated func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        NSLog("🎤 AudioRecorder: Did finish recording, success: \(flag)")
    }

    // Helper to notify delegate with correct type
    private func notifyDelegateDidFinishSendingFinalChunk() {
        delegate?.audioRecorderDidFinishSendingFinalChunk(self)
    }
}
