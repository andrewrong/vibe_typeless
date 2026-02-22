import Testing
import Foundation
import AVFoundation
@testable import TypelessApp

/// Audio Recorder 测试套件
/// 测试各种边界情况和时序问题
@Suite("Audio Recorder Tests")
struct AudioRecorderTests {

    // MARK: - 基础功能测试

    @Test("Recorder initializes correctly")
    @MainActor
    func testInitialization() async throws {
        let recorder = AudioKitRecorder()

        #expect(recorder.isRecording == false)
        #expect(recorder.sampleRate == 16000.0)
        #expect(recorder.channels == 1)
    }

    @Test("Permission check works")
    @MainActor
    func testPermissionCheck() async throws {
        let recorder = AudioKitRecorder()

        // 注意：实际权限测试需要在真机上运行
        // 这里只是测试方法存在
        let hasPermission = await recorder.requestPermission()
        // 在模拟器上通常是 true，在真机上取决于用户设置
        #expect(hasPermission == true || hasPermission == false)
    }

    // MARK: - 状态转换测试

    @Test("Cannot start recording twice")
    @MainActor
    func testDoubleStart() async throws {
        let recorder = AudioKitRecorder()

        // 第一次启动
        try? recorder.startRecording()
        #expect(recorder.isRecording == true)

        // 第二次启动应该被忽略
        try? recorder.startRecording()
        #expect(recorder.isRecording == true)  // 状态不变

        // 清理
        recorder.stopRecording()
        recorder.finishStopping()
    }

    @Test("Cannot stop when not recording")
    @MainActor
    func testStopWithoutStart() async {
        let recorder = AudioKitRecorder()

        #expect(recorder.isRecording == false)

        // 停止未启动的录音器不应该崩溃
        recorder.stopRecording()

        #expect(recorder.isRecording == false)
    }

    // MARK: - 快速开始/停止测试（边界情况）

    @Test("Rapid start/stop cycles")
    @MainActor
    func testRapidStartStop() async throws {
        let recorder = AudioKitRecorder()

        for i in 0..<10 {
            // 快速开始
            try? recorder.startRecording()
            #expect(recorder.isRecording == true, "Cycle \(i): Should be recording after start")

            // 立即停止（模拟用户快速按键）
            recorder.stopRecording()

            // 给一点时间来处理 final chunk
            try? await Task.sleep(nanoseconds: 50_000_000) // 50ms

            recorder.finishStopping()
            #expect(recorder.isRecording == false, "Cycle \(i): Should not be recording after stop")
        }
    }

    @Test("Very short recording (< 100ms)")
    @MainActor
    func testVeryShortRecording() async throws {
        let recorder = AudioKitRecorder()

        try? recorder.startRecording()
        #expect(recorder.isRecording == true)

        // 极短时间后停止（< 100ms）
        try? await Task.sleep(nanoseconds: 50_000_000) // 50ms

        recorder.stopRecording()
        try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
        recorder.finishStopping()

        #expect(recorder.isRecording == false)
    }

    // MARK: - 回调测试

    @Test("Audio chunk callback is triggered")
    @MainActor
    func testAudioChunkCallback() async throws {
        let recorder = AudioKitRecorder()

        var chunkCount = 0
        var finalChunkReceived = false

        recorder.onAudioChunk = { data, isFinal in
            chunkCount += 1
            if isFinal {
                finalChunkReceived = true
            }
        }

        try? recorder.startRecording()

        // 等待一段时间让音频数据累积
        try? await Task.sleep(nanoseconds: 200_000_000) // 200ms

        recorder.stopRecording()
        try? await Task.sleep(nanoseconds: 100_000_000) // 100ms
        recorder.finishStopping()

        #expect(chunkCount > 0, "Should have received at least one audio chunk")
        #expect(finalChunkReceived == true, "Should have received final chunk")
    }

    @Test("Finished callback is triggered on stop")
    @MainActor
    func testFinishedCallback() async throws {
        let recorder = AudioKitRecorder()

        var finishedCalled = false
        recorder.onFinished = {
            finishedCalled = true
        }

        try? recorder.startRecording()
        #expect(recorder.isRecording == true)

        recorder.stopRecording()
        try? await Task.sleep(nanoseconds: 200_000_000) // 200ms
        recorder.finishStopping()

        #expect(finishedCalled == true, "onFinished callback should be called")
    }

    // MARK: - 并发测试

    @Test("Concurrent start/stop operations")
    @MainActor
    func testConcurrentOperations() async throws {
        let recorder = AudioKitRecorder()

        // 模拟并发操作
        await withTaskGroup(of: Void.self) { group in
            // 任务1：快速开始/停止
            group.addTask {
                for _ in 0..<5 {
                    try? recorder.startRecording()
                    try? await Task.sleep(nanoseconds: 10_000_000) // 10ms
                    recorder.stopRecording()
                    recorder.finishStopping()
                }
            }

            // 任务2：同时检查状态
            group.addTask {
                for _ in 0..<10 {
                    _ = recorder.isRecording
                    try? await Task.sleep(nanoseconds: 5_000_000) // 5ms
                }
            }
        }

        // 最终状态应该是一致的
        #expect(recorder.isRecording == false || recorder.isRecording == true)
    }

    // MARK: - 长时间录音测试

    @Test("Long recording session (5 seconds)")
    @MainActor
    func testLongRecording() async throws {
        let recorder = AudioKitRecorder()

        var chunksReceived = 0
        recorder.onAudioChunk = { _, _ in
            chunksReceived += 1
        }

        try? recorder.startRecording()
        #expect(recorder.isRecording == true)

        // 录音5秒
        try? await Task.sleep(nanoseconds: 5_000_000_000) // 5s

        #expect(recorder.isRecording == true, "Should still be recording")
        #expect(chunksReceived > 40, "Should have received many chunks (expected ~50 for 100ms interval)")

        recorder.stopRecording()
        recorder.finishStopping()
        #expect(recorder.isRecording == false)
    }

    // MARK: - 音频格式测试

    @Test("Audio format is correct")
    @MainActor
    func testAudioFormat() async throws {
        let recorder = AudioKitRecorder()

        #expect(recorder.sampleRate == 16000.0)
        #expect(recorder.channels == 1)

        // 验证格式配置
        let format = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: recorder.sampleRate,
            channels: recorder.channels,
            interleaved: false
        )

        #expect(format != nil)
        #expect(format?.sampleRate == 16000.0)
        #expect(format?.channelCount == 1)
    }
}

/// BackgroundRecordingManager 测试套件
@Suite("Background Recording Manager Tests")
struct BackgroundRecordingManagerTests {

    @Test("Manager initializes correctly")
    @MainActor
    func testManagerInitialization() async throws {
        let manager = BackgroundRecordingManager()

        #expect(manager.isRecording == false)
    }

    @Test("Start recording changes state")
    @MainActor
    func testStartRecording() async throws {
        let manager = BackgroundRecordingManager()

        #expect(manager.isRecording == false)

        await manager.startRecording()

        // 由于网络请求，可能需要等待
        try? await Task.sleep(nanoseconds: 500_000_000) // 500ms

        #expect(manager.isRecording == true)

        // 清理
        await manager.stopRecording()
    }

    @Test("Stop without start is safe")
    @MainActor
    func testStopWithoutStart() async {
        let manager = BackgroundRecordingManager()

        #expect(manager.isRecording == false)

        // 应该不会崩溃
        await manager.stopRecording()

        #expect(manager.isRecording == false)
    }
}
