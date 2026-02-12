#!/usr/bin/env python3
"""
性能测试脚本 - 统计语音识别全流程耗时
"""

import time
import sys
import numpy as np

sys.path.insert(0, 'src')

def benchmark_pipeline():
    """测试完整流程耗时"""
    print("=" * 60)
    print("🚀 SenseVoice 全流程性能测试")
    print("=" * 60)
    print()

    # 1. 模型加载时间
    print("📦 1. 模型加载...")
    start = time.perf_counter()
    from asr import get_asr_model
    model = get_asr_model()
    load_time = time.perf_counter() - start
    print(f"   耗时: {load_time:.3f}s")
    print(f"   模型: {type(model).__name__}")
    print()

    # 2. 生成测试音频 (10秒)
    duration = 10.0
    sample_rate = 16000
    samples = int(duration * sample_rate)
    print(f"🎙️  2. 生成测试音频 ({duration}s)...")
    # 生成模拟语音信号（带有一些变化）
    t = np.linspace(0, duration, samples)
    # 模拟语音: 多个频率组合 + 一些噪声
    audio = (
        0.3 * np.sin(2 * np.pi * 440 * t) +      # 基频
        0.2 * np.sin(2 * np.pi * 880 * t) +      # 2次谐波
        0.1 * np.sin(2 * np.pi * 1320 * t) +     # 3次谐波
        0.05 * np.random.randn(samples)          # 噪声
    )
    audio = audio.astype(np.float32)
    print(f"   采样率: {sample_rate}Hz")
    print(f"   样本数: {samples}")
    print()

    # 3. 音频预处理 (VAD + 增强)
    print("🎛️  3. 音频预处理 (VAD + 增强)...")
    from asr.audio_pipeline import AudioPipeline
    pipeline = AudioPipeline(vad_threshold=0.5, enable_enhancement=True, enable_vad=True)

    start = time.perf_counter()
    processed_segments, stats = pipeline.process(audio)
    pipeline_time = time.perf_counter() - start

    print(f"   耗时: {pipeline_time:.3f}s")
    print(f"   分段数: {stats['segments']}")
    print(f"   移除静音: {stats['silence_removed'] / sample_rate:.2f}s")
    print()

    # 4. ASR 转录
    print("📝 4. ASR 转录 (SenseVoice)...")
    total_transcribe_time = 0
    for i, segment in enumerate(processed_segments):
        start = time.perf_counter()
        result = model.transcribe(segment, language="zh")
        segment_time = time.perf_counter() - start
        total_transcribe_time += segment_time
        print(f"   段{i+1}: {segment_time*1000:.1f}ms | 结果: '{result[:30]}...'")

    print(f"   总转录耗时: {total_transcribe_time:.3f}s")
    print(f"   平均每段: {total_transcribe_time/len(processed_segments)*1000:.1f}ms")
    print()

    # 5. 后处理 (标点和字典)
    print("✨ 5. 后处理 (标点 + 字典)...")
    from postprocess.processor import TextProcessor
    from postprocess.dictionary import personal_dictionary

    processor = TextProcessor()
    test_text = "统计一下目前这个整体整个流程下来的耗时是多少"

    start = time.perf_counter()
    corrected = processor.punctuation_corrector.correct(test_text)
    dict_applied = personal_dictionary.apply(corrected)
    postprocess_time = time.perf_counter() - start

    print(f"   耗时: {postprocess_time*1000:.1f}ms")
    print(f"   输入: '{test_text}'")
    print(f"   输出: '{dict_applied}'")
    print()

    # 总结
    print("=" * 60)
    print("📊 性能统计汇总")
    print("=" * 60)
    print()
    print(f"{'阶段':<30} {'耗时':>15}")
    print("-" * 60)
    print(f"{'模型加载':<30} {load_time:>14.3f}s")
    print(f"{'音频预处理 (VAD+增强)':<30} {pipeline_time:>14.3f}s")
    print(f"{'ASR 转录':<30} {total_transcribe_time:>14.3f}s")
    print(f"{'后处理 (标点+字典)':<30} {postprocess_time:>14.3f}s")
    print("-" * 60)

    total_time = pipeline_time + total_transcribe_time + postprocess_time
    print(f"{'总计 (不含加载)':<30} {total_time:>14.3f}s")
    print()
    print(f"🎯 处理速度比: {duration/total_time:.1f}x 实时")
    print(f"   (10秒音频处理耗时 {total_time:.2f}秒)")
    print()

    # SenseVoice 特性
    print("=" * 60)
    print("📌 SenseVoice 特性")
    print("=" * 60)
    print()
    print("理论性能:")
    print("  • 模型大小: 228MB (vs Whisper 3GB)")
    print("  • 理论速度: ~70ms/10s 音频 (15x 实时)")
    print("  • 语言支持: 中/英/日/韩/粤")
    print()
    print("实际测试:")
    print(f"  • 你的实际速度: {total_transcribe_time/duration*1000:.0f}ms/10s")
    print(f"  • 实时倍率: {duration/total_transcribe_time:.1f}x")
    print()

if __name__ == "__main__":
    benchmark_pipeline()
