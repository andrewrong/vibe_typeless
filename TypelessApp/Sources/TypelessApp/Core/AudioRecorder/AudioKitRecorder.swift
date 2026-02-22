import AudioKit
import AVFoundation
import Foundation

/// Audio recorder using AudioKit for more stable audio capture
/// Replaces RealtimeAudioRecorder with AudioKit's node-based architecture
class AudioKitRecorder {
    // MARK: - Properties

    /// AudioKit engine instance
    private var engine: AudioEngine?

    /// Callback for audio chunks
    var onAudioChunk: ((Data, Bool) -> Void)?

    /// Callback for errors
    var onError: ((Error) -> Void)?

    /// Callback when recording finished
    var onFinished: (() -> Void)?

    /// Recording state
    private(set) var isRecording = false

    /// Sample rate (16kHz for ASR)
    private(set) var sampleRate: Double = 16000.0

    /// Number of channels (mono for ASR)
    private(set) var channels: UInt32 = 1

    /// Flag to track if we're sending the final chunk
    private var isSendingFinalChunk = false

    /// Buffer for accumulating audio data between sends
    private var audioBuffer: Data = Data()

    /// Serial queue for thread-safe buffer access
    private let bufferQueue = DispatchQueue(label: "com.typeless.audiobuffer", qos: .userInitiated)

    /// Chunk interval in seconds
    private let chunkInterval: TimeInterval = 0.1 // 100ms chunks

    /// Timer for periodic chunk sending
    private var chunkTimer: Timer?

    // MARK: - Initialization

    init() {
        NSLog("🎤 AudioKitRecorder: Initializing")
    }

    deinit {
        NSLog("🎤 AudioKitRecorder: Deinitializing")
        stopEngine()
    }

    // MARK: - Configuration

    /// Request microphone permission
    func requestPermission() async -> Bool {
        #if os(macOS)
        let authStatus = AVCaptureDevice.authorizationStatus(for: .audio)

        switch authStatus {
        case .authorized:
            NSLog("🎤 AudioKitRecorder: Microphone permission already granted")
            return true
        case .notDetermined:
            NSLog("🎤 AudioKitRecorder: Requesting microphone permission...")
            return await withCheckedContinuation { continuation in
                AVCaptureDevice.requestAccess(for: .audio) { granted in
                    if granted {
                        NSLog("✅ AudioKitRecorder: Microphone permission granted")
                    } else {
                        NSLog("❌ AudioKitRecorder: Microphone permission denied")
                    }
                    continuation.resume(returning: granted)
                }
            }
        case .denied, .restricted:
            NSLog("❌ AudioKitRecorder: Microphone permission denied or restricted")
            return false
        @unknown default:
            NSLog("⚠️ AudioKitRecorder: Unknown microphone permission status")
            return false
        }
        #else
        return true
        #endif
    }

    /// Pre-initialize audio engine
    func prepareRecorder() async {
        // Check permission first
        if AVCaptureDevice.authorizationStatus(for: .audio) != .authorized {
            let hasPermission = await requestPermission()
            guard hasPermission else { return }
        }

        // Only create engine if not already exists
        guard engine == nil else {
            return
        }

        setupAudioEngine()
        NSLog("✅ AudioKitRecorder: Audio engine configured and ready")
    }

    private func setupAudioEngine() {
        let newEngine = AudioEngine()
        self.engine = newEngine

        NSLog("🎤 AudioKitRecorder: Audio engine configured")
    }

    // MARK: - Recording Control

    /// Start recording audio
    func startRecording() throws {
        NSLog("🎤 AudioKitRecorder: startRecording called")
        guard !isRecording else {
            NSLog("⚠️ AudioKitRecorder: Already recording")
            return
        }

        // Setup engine if not already done
        if engine == nil {
            NSLog("🎤 AudioKitRecorder: Setting up audio engine...")
            setupAudioEngine()
        }

        guard let engine = engine else {
            NSLog("❌ AudioKitRecorder: Audio engine not available")
            throw AudioRecorderError.configurationFailed
        }

        // Start engine
        if !engine.avEngine.isRunning {
            NSLog("🎤 AudioKitRecorder: Starting audio engine...")
            do {
                try engine.start()

                // Install raw tap on input node for actual audio capture
                installAudioTap()

                NSLog("✅ AudioKitRecorder: Audio engine started")
            } catch {
                NSLog("❌ AudioKitRecorder: Failed to start engine: \(error)")
                throw AudioRecorderError.recordingFailed(error)
            }
        } else {
            NSLog("🎤 AudioKitRecorder: Audio engine already running")
            installAudioTap()
        }

        // Clear buffer and reset state
        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }
        isSendingFinalChunk = false

        // Start recording
        isRecording = true
        NSLog("✅ AudioKitRecorder: Recording started")

        // Start timer to send chunks periodically
        startChunkTimer()

        // Send initial chunk after a short delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.01) { [weak self] in
            guard let self = self, self.isRecording else { return }
            self.sendChunk(isFinal: false)
        }
    }

    /// Install tap on input node for raw audio capture
    private func installAudioTap() {
        guard let inputNode = engine?.input?.avAudioNode as? AVAudioInputNode else {
            NSLog("❌ AudioKitRecorder: Cannot get input node for tap")
            return
        }

        let inputFormat = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, time in
            guard let self = self else { return }
            self.processAudioBuffer(buffer)
        }

        NSLog("🎤 AudioKitRecorder: Audio tap installed")
    }

    /// Remove tap from input node
    private func removeAudioTap() {
        guard let inputNode = engine?.input?.avAudioNode as? AVAudioInputNode else { return }
        inputNode.removeTap(onBus: 0)
        NSLog("🎤 AudioKitRecorder: Audio tap removed")
    }

    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        // Only process audio when actually recording
        guard isRecording, !isSendingFinalChunk else { return }

        let frameLength = Int(buffer.frameLength)
        guard frameLength > 0 else { return }

        var data = Data()
        data.reserveCapacity(frameLength * 2) // Int16 = 2 bytes

        // Convert buffer to Int16 data
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

    /// Stop recording audio
    func stopRecording() {
        NSLog("🎤 AudioKitRecorder: stopRecording called")
        guard isRecording else {
            NSLog("⚠️ AudioKitRecorder: Not recording")
            return
        }

        // Stop timer first
        chunkTimer?.invalidate()
        chunkTimer = nil

        // Mark that we're sending final chunk
        isSendingFinalChunk = true
        NSLog("🎤 AudioKitRecorder: Sending final audio chunk...")

        // Give a tiny delay to ensure the last audio buffer is processed
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.02) { [weak self] in
            guard let self = self else { return }
            // Send remaining audio as final chunk
            self.sendChunk(isFinal: true)
        }
    }

    /// Called when final chunk has been sent
    func finishStopping() {
        NSLog("🎤 AudioKitRecorder: Finishing stop (final chunk sent)")

        // Reset state for next recording
        isRecording = false
        isSendingFinalChunk = false

        // Remove audio tap
        removeAudioTap()

        // Clear buffer
        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }

        // Stop engine
        stopEngine()

        NSLog("✅ AudioKitRecorder: Recording stopped")
    }

    /// Stop the audio engine
    private func stopEngine() {
        engine?.stop()
        engine = nil
        NSLog("🎤 AudioKitRecorder: Engine stopped and cleaned up")
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

            NSLog("📤 AudioKitRecorder: Sending chunk: \(alignedData.count) bytes (\(alignedData.count / 2) samples, final=\(isFinal))")

            // Callback on main thread
            let chunkData = Data(alignedData)
            let finalChunk = isFinal
            DispatchQueue.main.async { [weak self] in
                self?.onAudioChunk?(chunkData, finalChunk)

                // If this was the final chunk, trigger onFinished after sending
                if finalChunk {
                    self?.onFinished?()
                }
            }
        }
    }
}
