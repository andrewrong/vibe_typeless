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
    var onFirstBuffer: (() -> Void)?

    private(set) var isRecording = false
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
        guard isRecording else { return }
        isReadyToSend = true
        sendAccumulatedAudio()
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

    private func setupAudioEngine() {
        let engine = AVAudioEngine()
        self.audioEngine = engine
        self.inputNode = engine.inputNode
        let inputFormat = engine.inputNode.outputFormat(forBus: 0)
        engine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, time in
            guard let self = self else { return }
            self.processAudioBuffer(buffer)
        }
    }

    private var firstBufferTime: Date?
    private var bufferCount = 0
    private var recordingStartTime: Date?

    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        if firstBufferTime == nil {
            firstBufferTime = Date()
            if isPrewarming {
                let sessionReady = isReadyToSend
                completeRecordingStart(sessionReady: sessionReady)
                DispatchQueue.main.async { [weak self] in
                    self?.onFirstBuffer?()
                }
            }
        }

        let frameLength = Int(buffer.frameLength)
        guard frameLength > 0 else { return }

        var data = Data()
        data.reserveCapacity(frameLength * 2)

        if buffer.format.commonFormat == .pcmFormatFloat32 {
            guard let channelData = buffer.floatChannelData else { return }
            let channelDataPointer = channelData[0]
            for i in 0..<frameLength {
                let sample = max(-1.0, min(1.0, Double(channelDataPointer[i])))
                let intSample = Int16(sample * 32767.0)
                data.append(UInt8(intSample & 0xFF))
                data.append(UInt8((intSample >> 8) & 0xFF))
            }
        } else if buffer.format.commonFormat == .pcmFormatInt16 {
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

        if isPrewarming {
            prewarmBufferQueue.async { [weak self] in
                self?.prewarmBuffer.append(data)
            }
            return
        }

        guard isRecording, !isSendingFinalChunk else { return }
        bufferCount += 1

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

    /// Start recording audio with ZERO latency
    func startRecording(sessionReady: Bool = false) throws {
        guard !isRecording else { return }

        if audioEngine == nil {
            setupAudioEngine()
        }

        guard let engine = audioEngine else {
            throw AudioRecorderError.configurationFailed
        }

        if !engine.isRunning {
            do {
                try engine.start()
            } catch {
                throw AudioRecorderError.recordingFailed(error)
            }
        }

        bufferQueue.async { [weak self] in
            self?.audioBuffer.removeAll()
        }
        isSendingFinalChunk = false
        firstBufferTime = nil
        bufferCount = 0

        isPrewarming = true
        prewarmBufferQueue.async { [weak self] in
            self?.prewarmBuffer.removeAll()
        }

        isReadyToSend = sessionReady
    }

    /// Complete the recording start process (called when first audio buffer arrives)
    private func completeRecordingStart(sessionReady: Bool) {
        guard isPrewarming else { return }

        isPrewarming = false
        isRecording = true
        recordingStartTime = Date()

        // Move prewarm buffer to main audio buffer
        prewarmBufferQueue.sync { [weak self] in
            guard let self = self else { return }
            if !self.prewarmBuffer.isEmpty {
                self.bufferQueue.async {
                    self.audioBuffer.append(self.prewarmBuffer)
                }
                self.prewarmBuffer.removeAll()
            }
        }
    }

    /// Stop recording audio
    func stopRecording() {
        guard isRecording || isPrewarming else { return }

        // If still prewarming (user stopped before first buffer arrived), cancel prewarming
        if isPrewarming {
            isPrewarming = false
            prewarmBuffer.removeAll()
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
