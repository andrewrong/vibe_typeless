import AVFoundation
import Foundation

/// Real-time audio recorder using AVAudioEngine for zero-latency recording
class RealtimeAudioRecorder: NSObject {
    // MARK: - Properties

    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?

    // Callback closures
    var onAudioChunk: ((Data, Bool) -> Void)?
    var onError: ((Error) -> Void)?
    var onFinished: (() -> Void)?

    private(set) var isRecording = false
    private(set) var sampleRate: Double = 16000.0
    private(set) var channels: UInt32 = 1

    /// Flag to track if we're sending the final chunk
    private var isSendingFinalChunk = false

    /// Buffer for accumulating audio data between sends
    private var audioBuffer: Data = Data()

    /// Timer for periodic chunk sending
    private var chunkTimer: Timer?

    /// Serial queue for thread-safe buffer access
    private let bufferQueue = DispatchQueue(label: "com.typeless.audiobuffer", qos: .userInitiated)

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

    /// Pre-initialize and start audio engine (runs continuously in background)
    func prepareRecorder() async {
        // Check permission first
        if AVCaptureDevice.authorizationStatus(for: .audio) != .authorized {
            let hasPermission = await requestPermission()
            guard hasPermission else { return }
        }

        // Only create engine if not already exists
        guard audioEngine == nil else {
            // Engine already exists, just ensure it's running
            if audioEngine?.isRunning == false {
                try? audioEngine?.start()
            }
            return
        }

        setupAudioEngine()

        // Start engine immediately and keep it running
        // This ensures zero latency when user presses the hotkey
        do {
            try audioEngine?.start()
            NSLog("✅ RealtimeAudioRecorder: Audio engine started and running (ready for instant recording)")
        } catch {
            NSLog("❌ RealtimeAudioRecorder: Failed to start engine: \(error)")
        }
    }

    private func setupAudioEngine() {
        let engine = AVAudioEngine()
        self.audioEngine = engine
        self.inputNode = engine.inputNode

        // Configure input format to match desired output format
        let inputFormat = engine.inputNode.outputFormat(forBus: 0)

        // Install tap on input node to capture audio in real-time
        engine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, time in
            guard let self = self else { return }
            self.processAudioBuffer(buffer)
        }

        NSLog("🎤 RealtimeAudioRecorder: Audio engine configured")
        NSLog("   Input format: \(inputFormat)")
    }

    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        // Only process audio when actually recording
        // This allows the engine to run continuously with zero start latency
        guard isRecording, !isSendingFinalChunk else { return }

        let frameLength = Int(buffer.frameLength)
        guard frameLength > 0 else { return }

        var data = Data()
        data.reserveCapacity(frameLength * 2) // Int16 = 2 bytes

        // Check buffer format and convert accordingly
        if buffer.format.commonFormat == .pcmFormatFloat32 {
            // Convert Float32 to Int16
            guard let channelData = buffer.floatChannelData else { return }

            let channelDataPointer = channelData[0]
            for i in 0..<frameLength {
                // Convert Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
                let sample = max(-1.0, min(1.0, Double(channelDataPointer[i])))
                let intSample = Int16(sample * 32767.0)
                data.append(UInt8(intSample & 0xFF))
                data.append(UInt8((intSample >> 8) & 0xFF))
            }
        } else if buffer.format.commonFormat == .pcmFormatInt16 {
            // Already Int16, just copy
            guard let channelData = buffer.int16ChannelData else { return }

            let channelDataPointer = channelData[0]
            for i in 0..<frameLength {
                let sample = channelDataPointer[i]
                data.append(UInt8(sample & 0xFF))
                data.append(UInt8((sample >> 8) & 0xFF))
            }
        } else {
            return
        }

        // Accumulate in buffer (thread-safe)
        bufferQueue.async { [weak self] in
            guard let self = self else { return }
            self.audioBuffer.append(data)
        }
    }

    // MARK: - Recording Control

    /// Start recording audio with ZERO latency
    /// AudioEngine should already be running, but will auto-start if needed
    func startRecording() throws {
        NSLog("🎤 RealtimeAudioRecorder: startRecording called")
        guard !isRecording else {
            NSLog("⚠️ RealtimeAudioRecorder: Already recording")
            return
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

        // Start engine if not running (should already be running from prepareRecorder)
        if !engine.isRunning {
            NSLog("🎤 RealtimeAudioRecorder: Starting audio engine...")
            do {
                try engine.start()
            } catch {
                NSLog("❌ RealtimeAudioRecorder: Failed to start engine: \(error)")
                throw AudioRecorderError.recordingFailed(error)
            }
        }

        // Clear buffer and reset state (thread-safe)
        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }
        isSendingFinalChunk = false

        // Start recording - just set the flag!
        // Audio is already being captured by the running engine
        isRecording = true
        NSLog("✅ RealtimeAudioRecorder: Recording started (TRUE zero latency)")

        // Start timer to send chunks periodically
        startChunkTimer()

        // Send initial chunk immediately after a very short delay
        let recorder = self
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.01) { [weak recorder] in
            guard let recorder = recorder, recorder.isRecording else { return }
            recorder.sendChunk(isFinal: false)
        }
    }

    /// Stop recording audio
    /// Note: AudioEngine keeps running for instant next recording
    func stopRecording() {
        NSLog("🎤 RealtimeAudioRecorder: stopRecording called")
        guard isRecording else {
            NSLog("⚠️ RealtimeAudioRecorder: Not recording")
            return
        }

        // Stop timer first
        chunkTimer?.invalidate()
        chunkTimer = nil

        // Mark that we're sending final chunk
        isSendingFinalChunk = true
        NSLog("🎤 RealtimeAudioRecorder: Sending final audio chunk...")

        // Note: We DON'T stop the engine here - it keeps running for instant restart
        // Just process any remaining audio in the buffer

        // Give a tiny delay to ensure the last audio buffer is processed
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.02) { [weak self] in
            guard let self = self else { return }
            // Send remaining audio as final chunk
            self.sendChunk(isFinal: true)
        }
    }

    /// Called when final chunk has been sent
    func finishStopping() {
        NSLog("🎤 RealtimeAudioRecorder: Finishing stop (final chunk sent)")

        // Reset state for next recording
        // Note: AudioEngine keeps running, just reset recording state
        isRecording = false
        isSendingFinalChunk = false
        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }

        NSLog("✅ RealtimeAudioRecorder: Recording stopped (engine still running for instant restart)")
    }

    // MARK: - Private Methods

    private func startChunkTimer() {
        // Send audio chunks every 100ms for low latency
        chunkTimer = Timer.scheduledTimer(withTimeInterval: chunkInterval, repeats: true) { [weak self] _ in
            guard let self = self, self.isRecording, !self.isSendingFinalChunk else { return }
            self.sendChunk(isFinal: false)
        }
    }

    private func sendChunk(isFinal: Bool) {
        // Get buffer data (thread-safe)
        bufferQueue.sync { [weak self] in
            guard let self = self else { return }

            guard !self.audioBuffer.isEmpty else {
                if isFinal {
                    DispatchQueue.main.async { [weak self] in self?.onFinished?() }
                }
                return
            }

            let pcmData = self.audioBuffer
            self.audioBuffer.removeAll()

            // Process the data
            let sampleSize = 2
            let padding = pcmData.count % sampleSize
            let alignedData = padding > 0 ? pcmData.dropLast(padding) : pcmData

            guard !alignedData.isEmpty else {
                if isFinal {
                    DispatchQueue.main.async { [weak self] in self?.onFinished?() }
                }
                return
            }

            NSLog("📤 RealtimeAudioRecorder: Sending chunk: \(alignedData.count) bytes (\(alignedData.count / 2) samples, final=\(isFinal))")

            // Create buffer for callback
            let frameCapacity = alignedData.count / sampleSize
            guard let format = AVAudioFormat(
                commonFormat: .pcmFormatInt16,
                sampleRate: self.sampleRate,
                channels: self.channels,
                interleaved: false
            ), let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frameCapacity)) else {
                if isFinal {
                    DispatchQueue.main.async { [weak self] in self?.onFinished?() }
                }
                return
            }

            buffer.frameLength = AVAudioFrameCount(frameCapacity)

            // Callback on main thread - capture data explicitly
            let chunkData = Data(alignedData)
            let finalChunk = isFinal
            DispatchQueue.main.async { [weak self] in
                self?.onAudioChunk?(chunkData, finalChunk)
            }
        }
    }
}
