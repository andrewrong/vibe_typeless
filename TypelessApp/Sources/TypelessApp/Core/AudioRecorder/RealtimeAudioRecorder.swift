import AVFoundation
import Foundation
#if os(macOS)
import AppKit
#endif

/// Real-time audio recorder using AVAudioEngine for zero-latency recording
class RealtimeAudioRecorder: NSObject {
    // MARK: - Properties

    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?

    // Callback closures
    var onAudioChunk: ((Data, Bool) -> Void)?
    var onError: ((Error) -> Void)?
    var onFinished: (() -> Void)?
    var onFirstBuffer: (() -> Void)?

    private(set) var isRecording = false
    /// Current audio sample rate (determined by hardware, e.g., 16000 for Bluetooth HFP, 48000 for some devices)
    private(set) var sampleRate: Double = 16000.0
    private(set) var channels: UInt32 = 1

    /// Flag to track if we're sending the final chunk
    private var isSendingFinalChunk = false

    /// Buffer for accumulating audio data between sends
    private var audioBuffer: Data = Data()

    /// Serial queue for thread-safe buffer access
    private let bufferQueue = DispatchQueue(label: "com.typeless.audiobuffer", qos: .userInitiated)

    /// Flag to control when chunks should be sent (Session must be ready)
    /// Manager sets this to true when ASR session is ready
    private var isReadyToSend: Bool = false

    /// Track total audio bytes sent for debugging
    private var totalBytesSent: Int = 0
    private var firstSendTime: Date?
    private var lastSendTime: Date?

    // MARK: - Initialization

    override init() {
        super.init()
    }

    /// Called by manager when ASR session is ready
    func markReadyToSend() {
        // Note: This can be called during prewarming (before isRecording becomes true)
        // So we don't check isRecording here
        isReadyToSend = true
        NSLog("🎤 markReadyToSend: isReadyToSend=true, isRecording=\(isRecording), isPrewarming=\(isPrewarming)")
        if isRecording {
            sendAccumulatedAudio()
        }
    }

    /// Send accumulated audio from buffer in chunks
    private func sendAccumulatedAudio() {
        bufferQueue.sync { [weak self] in
            guard let self = self, !self.audioBuffer.isEmpty else { return }

            let chunkSize = 3200
            let chunkIntervalMs = 100

            var chunks: [Data] = []
            var tempBuffer = self.audioBuffer
            self.audioBuffer.removeAll()

            while !tempBuffer.isEmpty {
                let bytesToSend = min(chunkSize, tempBuffer.count)
                let chunk = tempBuffer.prefix(bytesToSend)
                tempBuffer.removeFirst(bytesToSend)
                chunks.append(Data(chunk))
            }

            for (index, chunkData) in chunks.enumerated() {
                DispatchQueue.main.asyncAfter(deadline: .now() + Double(index) * Double(chunkIntervalMs) / 1000.0) { [weak self] in
                    guard let self = self, self.isRecording else { return }
                    self.onAudioChunk?(chunkData, false)
                }
            }
        }
    }

    // MARK: - Configuration

    /// Request microphone permission
    func requestPermission() async -> Bool {
        #if os(macOS)
        let authStatus = AVCaptureDevice.authorizationStatus(for: .audio)

        switch authStatus {
        case .authorized:
            return true
        case .notDetermined:
            return await withCheckedContinuation { continuation in
                AVCaptureDevice.requestAccess(for: .audio) { granted in
                    continuation.resume(returning: granted)
                }
            }
        case .denied, .restricted:
            return false
        @unknown default:
            return false
        }
        #else
        return true
        #endif
    }

    /// Pre-initialize audio engine
    func prepareRecorder() async {
        if AVCaptureDevice.authorizationStatus(for: .audio) != .authorized {
            let hasPermission = await requestPermission()
            guard hasPermission else { return }
        }
        guard audioEngine == nil else { return }
        setupAudioEngine()
    }

    private var isTapInstalled = false

    private func setupAudioEngine() {
        NSLog("🎤 Setting up new audio engine...")

        // Log audio device info for debugging
        #if os(macOS)
        if let defaultDevice = AVCaptureDevice.default(for: .audio) {
            NSLog("🎤 Default input device: \(defaultDevice.localizedName)")
        }
        #endif

        // Ensure any existing engine is fully cleaned up
        if let oldEngine = audioEngine {
            if oldEngine.isRunning {
                oldEngine.stop()
            }
            oldEngine.inputNode.removeTap(onBus: 0)
            NSLog("🎤 Cleaned up old engine")
        }

        let engine = AVAudioEngine()
        self.audioEngine = engine
        self.inputNode = engine.inputNode

        // Get the current input format - use inputFormat to get the actual hardware input format
        let inputFormat = engine.inputNode.inputFormat(forBus: 0)

        NSLog("🎤 Hardware input format: \(inputFormat)")
        NSLog("🎤 Sample rate: \(inputFormat.sampleRate) Hz")
        NSLog("🎤 Channels: \(inputFormat.channelCount)")

        // Check if format is valid
        guard inputFormat.sampleRate > 0, inputFormat.channelCount > 0 else {
            NSLog("❌ Invalid input format")
            return
        }

        // Update sample rate to match hardware
        self.sampleRate = inputFormat.sampleRate
        NSLog("🎤 Updated sampleRate to \(self.sampleRate) Hz")

        // Install tap with nil format - use hardware format, backend will handle resampling
        engine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: nil) { [weak self] buffer, time in
            guard let self = self else { return }
            self.processAudioBuffer(buffer)
        }

        isTapInstalled = true
        NSLog("✅ Audio engine setup complete (tap installed with hardware format)")
    }

    /// Clean up engine resources - called before creating new engine
    private func cleanupEngine() {
        guard let engine = audioEngine else { return }
        NSLog("🎤 Cleaning up audio engine...")
        engine.inputNode.removeTap(onBus: 0)
        if engine.isRunning {
            engine.stop()
        }
        audioEngine = nil
        inputNode = nil
        isTapInstalled = false
        NSLog("✅ Audio engine cleaned up")
    }

    private var firstBufferTime: Date?
    private var bufferCount = 0
    private var recordingStartTime: Date?

    private var consecutiveEmptyBuffers = 0


    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        // Check for empty buffer
        if buffer.frameLength == 0 {
            consecutiveEmptyBuffers += 1
            if consecutiveEmptyBuffers > 5 {
                NSLog("⚠️ Too many consecutive empty buffers")
            }
            return
        } else {
            consecutiveEmptyBuffers = 0
        }

        // Convert buffer to data first (needed for both first buffer and subsequent buffers)
        let frameLength = Int(buffer.frameLength)
        guard frameLength > 0 else { return }

        var data = Data()
        data.reserveCapacity(frameLength * 2)
        var maxSample: Double = 0.0
        var minSample: Double = 0.0
        var sumSample: Double = 0.0

        if buffer.format.commonFormat == .pcmFormatFloat32 {
            guard let channelData = buffer.floatChannelData else { return }
            let channelDataPointer = channelData[0]
            for i in 0..<frameLength {
                let sample = max(-1.0, min(1.0, Double(channelDataPointer[i])))
                maxSample = max(maxSample, sample)
                minSample = min(minSample, sample)
                sumSample += abs(sample)
                let intSample = Int16(sample * 32767.0)
                data.append(UInt8(intSample & 0xFF))
                data.append(UInt8((intSample >> 8) & 0xFF))
            }
        } else if buffer.format.commonFormat == .pcmFormatInt16 {
            guard let channelData = buffer.int16ChannelData else { return }
            let channelDataPointer = channelData[0]
            for i in 0..<frameLength {
                let sample = channelDataPointer[i]
                let floatSample = Double(sample) / 32768.0
                maxSample = max(maxSample, floatSample)
                minSample = min(minSample, floatSample)
                sumSample += abs(floatSample)
                data.append(UInt8(sample & 0xFF))
                data.append(UInt8((sample >> 8) & 0xFF))
            }
        } else {
            return
        }

        // Log audio levels for every buffer to diagnose microphone issues
        let avgLevel = sumSample / Double(frameLength)
        if firstBufferTime == nil {
            if maxSample < 0.001 {
                NSLog("🎙️ First buffer: SILENT (max: \(String(format: "%.4f", maxSample)), avg: \(String(format: "%.4f", avgLevel)))")
                // Check if we're using the right input device
                #if os(macOS)
                if let device = AVCaptureDevice.default(for: .audio) {
                    NSLog("🎙️ Current input device: \(device.localizedName), format: \(buffer.format)")
                }
                #endif
            } else {
                NSLog("🎙️ First buffer: OK (max: \(String(format: "%.4f", maxSample)), avg: \(String(format: "%.4f", avgLevel)))")
            }
        }

        // Log buffer reception with gap detection
        bufferCount += 1
        let isEngineRunning = audioEngine?.isRunning ?? false
        if bufferCount == 1 {
            NSLog("🎙️ First audio buffer: \(buffer.frameLength) frames @ \(Int(buffer.format.sampleRate))Hz, engineRunning=\(isEngineRunning)")
        } else if bufferCount % 50 == 0 {
            // Log every 50th buffer to avoid spam
            NSLog("🎙️ Buffer #\(bufferCount): \(buffer.frameLength) frames, engineRunning=\(isEngineRunning)")
        }

        // Update last buffer time for watchdog monitoring
        if firstBufferTime == nil {
            firstBufferTime = Date()
            if isPrewarming {
                // First add current data to prewarmBuffer before calling completeRecordingStart
                prewarmBufferQueue.async { [weak self] in
                    guard let self = self else { return }
                    self.prewarmBuffer.append(data)

                    // Now complete recording start on main thread
                    DispatchQueue.main.async {
                        let sessionReady = self.isReadyToSend
                        self.completeRecordingStart(sessionReady: sessionReady)
                        // Play beep sound to indicate recording has started
                        NSSound.beep()
                        self.onFirstBuffer?()
                    }
                }
                return
            }
        }

        if isPrewarming {
            prewarmBufferQueue.async { [weak self] in
                self?.prewarmBuffer.append(data)
            }
            return
        }

        guard isRecording, !isSendingFinalChunk else {
            if !isRecording {
                NSLog("⚠️ processAudioBuffer #\(bufferCount): isRecording=false, skipping (prewarming=\(isPrewarming))")
            }
            if isSendingFinalChunk {
                NSLog("⚠️ processAudioBuffer #\(bufferCount): isSendingFinalChunk=true, skipping")
            }
            return
        }

        bufferQueue.async { [weak self] in
            guard let self = self else { return }
            self.audioBuffer.append(data)

            if self.isReadyToSend && !self.isSendingFinalChunk {
                let chunkData = Data(self.audioBuffer)
                let chunkSize = chunkData.count
                self.audioBuffer.removeAll()
                self.totalBytesSent += chunkSize
                if self.firstSendTime == nil {
                    self.firstSendTime = Date()
                }
                self.lastSendTime = Date()
                DispatchQueue.main.async { [weak self] in
                    self?.onAudioChunk?(chunkData, false)
                }
            }
        }
    }

    // MARK: - Recording Control

    /// Pre-warmed audio buffer - captures audio before recording officially starts
    /// This prevents losing the first ~100ms of audio due to hardware latency
    private var prewarmBuffer: Data = Data()
    private let prewarmBufferQueue = DispatchQueue(label: "com.typeless.prewarmbuffer", qos: .userInitiated)
    private var isPrewarming: Bool = false

    /// Track engine errors
    private var engineStartError: Error?

    /// Start recording audio with ZERO latency
    func startRecording(sessionReady: Bool = false) async throws {
        guard !isRecording else {
            NSLog("⚠️ Already recording, ignoring start request")
            return
        }

        // Check microphone permission first
        let authStatus = AVCaptureDevice.authorizationStatus(for: .audio)
        if authStatus != .authorized {
            NSLog("🎤 Requesting microphone permission...")
            let granted = await requestPermission()
            if !granted {
                NSLog("❌ Microphone permission denied")
                throw AudioRecorderError.notAuthorized
            }
        }

        // Clean up any existing engine
        cleanupEngine()

        // IMPORTANT: Configure audio session for recording to force HFP mode on Bluetooth
        #if os(macOS)
        // On macOS, we need to ensure the default input device is set correctly
        // Sometimes the system reports the wrong format before the engine starts
        NSLog("🎤 Configuring audio for recording...")
        #endif

        // Create new engine
        setupAudioEngine()

        guard let engine = audioEngine else {
            NSLog("❌ Audio engine not available")
            throw AudioRecorderError.configurationFailed
        }

        // Start engine - this will activate the microphone and trigger HFP mode switch
        do {
            try engine.start()
            NSLog("✅ Audio engine started")

            // After starting, re-check the actual input format
            // The format may have changed after the engine started (HFP mode activation)
            // Wait a bit for Bluetooth HFP mode to fully activate
            try? await Task.sleep(nanoseconds: 100_000_000) // 0.1s
            let actualFormat = engine.inputNode.inputFormat(forBus: 0)
            if actualFormat.sampleRate != self.sampleRate {
                NSLog("🎤 Sample rate changed after start: \(self.sampleRate)Hz → \(actualFormat.sampleRate)Hz")
                self.sampleRate = actualFormat.sampleRate
            }
        } catch {
            NSLog("❌ Failed to start audio engine: \(error)")
            engineStartError = error
            throw AudioRecorderError.recordingFailed(error)
        }

        // Reset state
        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }
        prewarmBufferQueue.async { [weak self] in
            self?.prewarmBuffer.removeAll()
        }
        isSendingFinalChunk = false
        firstBufferTime = nil
        bufferCount = 0
        isPrewarming = true
        isReadyToSend = sessionReady

        NSLog("🎤 Recording started at \(Int(sampleRate))Hz, waiting for first buffer...")
    }

    /// Complete the recording start process (called when first audio buffer arrives)
    private func completeRecordingStart(sessionReady: Bool) {
        guard isPrewarming else {
            NSLog("⚠️ completeRecordingStart called but not prewarming")
            return
        }

        // NSLog("🎙️ Completing recording start")

        isPrewarming = false
        isRecording = true
        recordingStartTime = Date()

        // Move prewarm buffer to main audio buffer synchronously to avoid race condition
        let prewarmData = prewarmBufferQueue.sync { [weak self] () -> Data in
            guard let self = self else { return Data() }
            let data = self.prewarmBuffer
            self.prewarmBuffer.removeAll()
            return data
        }

        // If already ready to send (session was created during prewarming), start sending accumulated audio
        if isReadyToSend {
            // NSLog("🎙️ completeRecordingStart: isReadyToSend=true, moving prewarm data and starting to send")
            bufferQueue.sync { [weak self] in
                guard let self = self else { return }
                if !prewarmData.isEmpty {
                    self.audioBuffer.append(prewarmData)
                }
                // Now send all accumulated audio
                self.sendAccumulatedAudioSync()
            }
        } else {
            // Just move prewarm data to buffer for later sending
            if !prewarmData.isEmpty {
                bufferQueue.async { [weak self] in
                    self?.audioBuffer.append(prewarmData)
                    NSLog("🎙️ Moved \(prewarmData.count) bytes from prewarm to main buffer (waiting for session)")
                }
            }
        }
    }

    /// Synchronous version of sendAccumulatedAudio (must be called within bufferQueue)
    private func sendAccumulatedAudioSync() {
        guard !self.audioBuffer.isEmpty else { return }

        let chunkData = Data(self.audioBuffer)
        let chunkSize = chunkData.count
        self.audioBuffer.removeAll()
        self.totalBytesSent += chunkSize
        if self.firstSendTime == nil {
            self.firstSendTime = Date()
        }
        self.lastSendTime = Date()

        DispatchQueue.main.async { [weak self] in
            self?.onAudioChunk?(chunkData, false)
            // NSLog("🎙️ Sent accumulated audio: \(chunkSize) bytes")
        }
    }

    /// Stop recording audio
    func stopRecording() {
        // Allow stopping if we're in any active state (recording, prewarming, or waiting for first buffer)
        guard isRecording || isPrewarming || recordingStartTime != nil else {
            NSLog("⚠️ StopRecording called but not in active state (isRecording=\(isRecording), isPrewarming=\(isPrewarming))")
            return
        }

        // If still prewarming (user stopped before first buffer arrived), cancel prewarming
        if isPrewarming {
            isPrewarming = false
            prewarmBuffer.removeAll()
            // Important: Must call finishStopping to clean up audio engine for Bluetooth
            finishStopping()
            DispatchQueue.main.async { [weak self] in
                self?.onFinished?()
            }
            return
        }

        isSendingFinalChunk = true
        isRecording = false

        // Send remaining audio immediately
        bufferQueue.async { [weak self] in
            guard let self = self else { return }
            if !self.audioBuffer.isEmpty {
                let chunkData = Data(self.audioBuffer)
                self.audioBuffer.removeAll()
                DispatchQueue.main.async { [weak self] in
                    self?.onAudioChunk?(chunkData, true)
                    self?.onFinished?()
                }
            } else {
                DispatchQueue.main.async { [weak self] in
                    self?.onFinished?()
                }
            }
        }
    }

    /// Called when final chunk has been sent
    func finishStopping() {
        // Reset state for next recording
        isSendingFinalChunk = false
        isReadyToSend = false
        isPrewarming = false
        firstBufferTime = nil
        bufferCount = 0
        recordingStartTime = nil
        totalBytesSent = 0
        firstSendTime = nil
        lastSendTime = nil
        prewarmBuffer.removeAll()

        // Stop the engine and remove tap to prevent AUGraph conflicts on restart
        if let engine = audioEngine {
            engine.inputNode.removeTap(onBus: 0)
            if engine.isRunning {
                engine.stop()
            }
            self.audioEngine = nil
            self.inputNode = nil
        }

        // Clear buffer
        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }
    }

    // MARK: - Private Methods
}
