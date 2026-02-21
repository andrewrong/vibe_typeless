import AVFoundation
import Foundation

/// Real-time audio recorder using AVAudioEngine for zero-latency recording
/// This is the recommended approach for apps like Telegram/WeChat that need instant voice recording
@MainActor
class RealtimeAudioRecorder: NSObject {
    // MARK: - Properties

    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?

    weak var delegate: AudioRecorderDelegate?

    private(set) var isRecording = false
    private(set) var sampleRate: Double = 16000.0
    private(set) var channels: UInt32 = 1

    /// Flag to track if we're sending the final chunk
    private var isSendingFinalChunk = false

    /// Buffer for accumulating audio data between sends
    private var audioBuffer: Data = Data()

    /// Timer for periodic chunk sending
    private var chunkTimer: Timer?

    /// Chunk interval in seconds
    private let chunkInterval: TimeInterval = 0.1 // 100ms chunks for low latency

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
            NSLog("🎤 RealtimeAudioRecorder: Microphone permission already granted")
            return true
        case .notDetermined:
            NSLog("🎤 RealtimeAudioRecorder: Requesting microphone permission...")
            return await withCheckedContinuation { continuation in
                AVCaptureDevice.requestAccess(for: .audio) { granted in
                    if granted {
                        NSLog("✅ RealtimeAudioRecorder: Microphone permission granted")
                    } else {
                        NSLog("❌ RealtimeAudioRecorder: Microphone permission denied")
                    }
                    continuation.resume(returning: granted)
                }
            }
        case .denied, .restricted:
            NSLog("❌ RealtimeAudioRecorder: Microphone permission denied or restricted")
            return false
        @unknown default:
            NSLog("⚠️ RealtimeAudioRecorder: Unknown microphone permission status")
            return false
        }
        #else
        return true
        #endif
    }

    /// Pre-initialize audio engine to reduce startup latency
    func prepareRecorder() async {
        // Check permission first
        if AVCaptureDevice.authorizationStatus(for: .audio) != .authorized {
            let hasPermission = await requestPermission()
            guard hasPermission else { return }
        }

        // Only create engine if not already exists
        guard audioEngine == nil else {
            NSLog("🎤 RealtimeAudioRecorder: Already initialized")
            return
        }

        setupAudioEngine()
    }

    private func setupAudioEngine() {
        let engine = AVAudioEngine()
        self.audioEngine = engine
        self.inputNode = engine.inputNode

        // Configure input format to match desired output format
        let inputFormat = engine.inputNode.outputFormat(forBus: 0)

        // Create format converter if needed (e.g., from 48kHz to 16kHz)
        guard let targetFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else {
            NSLog("❌ RealtimeAudioRecorder: Failed to create target format")
            return
        }

        // Install tap on input node to capture audio in real-time
        engine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, time in
            guard let self = self, self.isRecording else { return }
            self.processAudioBuffer(buffer)
        }

        NSLog("🎤 RealtimeAudioRecorder: Audio engine configured")
        NSLog("   Input format: \(inputFormat)")
        NSLog("   Target format: \(targetFormat)")
    }

    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        // Convert buffer to Int16 PCM data
        guard let channelData = buffer.int16ChannelData else {
            NSLog("⚠️ RealtimeAudioRecorder: No int16 channel data available")
            return
        }

        let frameLength = Int(buffer.frameLength)
        let channelDataPointer = channelData[0]
        let channelDataArray = Array(UnsafeBufferPointer(start: channelDataPointer, count: frameLength))

        // Convert to Data
        var data = Data()
        data.append(contentsOf: channelDataArray.map { UInt8($0 & 0xFF) })
        data.append(contentsOf: channelDataArray.map { UInt8(($0 >> 8) & 0xFF) })

        // Accumulate in buffer
        audioBuffer.append(data)
    }

    // MARK: - Recording Control

    /// Start recording audio with zero latency
    func startRecording() async throws {
        NSLog("🎤 RealtimeAudioRecorder: startRecording called")
        guard !isRecording else {
            NSLog("⚠️ RealtimeAudioRecorder: Already recording")
            return
        }

        // Check permission
        let authStatus = AVCaptureDevice.authorizationStatus(for: .audio)
        guard authStatus == .authorized else {
            NSLog("❌ RealtimeAudioRecorder: Permission not granted")
            throw AudioRecorderError.notAuthorized
        }

        // Setup engine if not already done
        if audioEngine == nil {
            NSLog("🎤 RealtimeAudioRecorder: Setting up audio engine...")
            setupAudioEngine()
        }

        guard let engine = audioEngine else {
            NSLog("❌ RealtimeAudioRecorder: Audio engine not available")
            throw AudioRecorderError.configurationFailed
        }

        // Clear buffer
        audioBuffer.removeAll()
        isSendingFinalChunk = false

        // Start the engine
        do {
            try engine.start()
            isRecording = true
            NSLog("✅ RealtimeAudioRecorder: Recording started (zero latency)")

            // Start timer to send chunks periodically
            startChunkTimer()

            // Send initial chunk immediately after a very short delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.01) { [weak self] in
                guard let self = self, self.isRecording else { return }
                self.sendChunk(isFinal: false)
            }
        } catch {
            NSLog("❌ RealtimeAudioRecorder: Failed to start engine: \(error)")
            throw AudioRecorderError.recordingFailed(error)
        }
    }

    /// Stop recording audio
    func stopRecording() {
        NSLog("🎤 RealtimeAudioRecorder: stopRecording called")
        guard isRecording else {
            NSLog("⚠️ RealtimeAudioRecorder: Not recording")
            return
        }

        // Stop timer
        chunkTimer?.invalidate()
        chunkTimer = nil

        // Mark that we're sending final chunk
        isSendingFinalChunk = true
        NSLog("🎤 RealtimeAudioRecorder: Sending final audio chunk...")

        // Send remaining audio as final chunk
        sendChunk(isFinal: true)
    }

    /// Called by delegate when final chunk has been sent
    func finishStopping() {
        NSLog("🎤 RealtimeAudioRecorder: Finishing stop (final chunk sent)")

        // Stop engine
        audioEngine?.stop()

        // Reset state
        isRecording = false
        isSendingFinalChunk = false
        audioBuffer.removeAll()

        NSLog("✅ RealtimeAudioRecorder: Recording stopped")
    }

    // MARK: - Private Methods

    private func startChunkTimer() {
        // Send audio chunks every 100ms for low latency
        chunkTimer = Timer.scheduledTimer(withTimeInterval: chunkInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self, self.isRecording, !self.isSendingFinalChunk else { return }
                self.sendChunk(isFinal: false)
            }
        }
    }

    private func sendChunk(isFinal: Bool) {
        guard !audioBuffer.isEmpty else {
            // No data to send, but if final, still notify
            if isFinal {
                notifyFinalChunkSent()
            }
            return
        }

        let pcmData = audioBuffer
        audioBuffer.removeAll() // Clear buffer for next chunk

        // Ensure data is aligned to sample size (2 bytes for Int16)
        let sampleSize = 2
        let padding = pcmData.count % sampleSize
        let alignedData = padding > 0 ? pcmData.dropLast(padding) : pcmData

        guard !alignedData.isEmpty else {
            if isFinal {
                notifyFinalChunkSent()
            }
            return
        }

        NSLog("📤 RealtimeAudioRecorder: Sending chunk: \(alignedData.count) bytes (\(alignedData.count / 2) samples, final=\(isFinal))")

        // Create a dummy buffer for the delegate callback
        let frameCapacity = alignedData.count / sampleSize
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: sampleRate,
            channels: channels,
            interleaved: false
        ) else {
            if isFinal {
                notifyFinalChunkSent()
            }
            return
        }

        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCapacity)) else {
            if isFinal {
                notifyFinalChunkSent()
            }
            return
        }

        buffer.frameLength = AVAudioFrameCount(frameCapacity)

        // Send to delegate
        delegate?.audioRecorder(self, didOutputAudioBuffer: buffer, data: alignedData, isFinal: isFinal)
    }

    private func notifyFinalChunkSent() {
        delegate?.audioRecorderDidFinishSendingFinalChunk(self)
    }
}
