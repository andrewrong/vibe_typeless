import AVFoundation
import Foundation
import Cocoa

/// Audio recording errors
enum AudioRecorderError: Error {
    case notAuthorized
    case configurationFailed
    case recordingFailed(Error)
}

/// Audio recorder delegate
@MainActor
protocol AudioRecorderDelegate: AnyObject {
    func audioRecorder(_ recorder: AudioRecorder, didOutputAudioBuffer buffer: AVAudioBuffer, data: Data, isFinal: Bool)
    func audioRecorder(_ recorder: AudioRecorder, didEncounterError error: AudioRecorderError)
    /// Called when the final audio chunk has been sent
    func audioRecorderDidFinishSendingFinalChunk(_ recorder: AudioRecorder)
}

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

    /// Start recording audio
    func startRecording() async throws {
        NSLog("🎤 AudioRecorder: startRecording called")
        guard !isRecording else {
            NSLog("⚠️ AudioRecorder: Already recording")
            return
        }

        // Check permission
        NSLog("🎤 AudioRecorder: Checking permissions...")
        let hasPermission = await requestPermission()
        guard hasPermission else {
            NSLog("❌ AudioRecorder: Permission denied")
            throw AudioRecorderError.notAuthorized
        }

        // Create temporary file for recording
        let tempDir = NSTemporaryDirectory()
        let tempFile = tempDir + "recording_\(UUID().uuidString).wav"
        let fileURL = URL(fileURLWithPath: tempFile)
        self.audioFileURL = fileURL

        // Configure recording settings
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: sampleRate,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsNonInterleaved: false
        ]

        NSLog("🎤 AudioRecorder: Creating AVAudioRecorder...")
        guard let recorder = try? AVAudioRecorder(url: fileURL, settings: settings) else {
            NSLog("❌ AudioRecorder: Failed to create recorder")
            throw AudioRecorderError.configurationFailed
        }

        self.audioRecorder = recorder
        recorder.delegate = self
        recorder.isMeteringEnabled = true

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

        // Stop recorder
        audioRecorder?.stop()
        audioRecorder = nil

        // Clean up temp file
        if let fileURL = audioFileURL {
            try? FileManager.default.removeItem(at: fileURL)
            audioFileURL = nil
        }

        isSendingFinalChunk = false
        isRecording = false
        NSLog("✅ AudioRecorder: Recording stopped")
    }

    // MARK: - Private Methods

    private func startAudioChunkTimer() {
        // Send audio chunks every 0.5 seconds
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self,
                      let recorder = self.audioRecorder,
                      recorder.isRecording,
                      let fileURL = self.audioFileURL else {
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
}
