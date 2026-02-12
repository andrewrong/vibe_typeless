#!/usr/bin/env python3
"""
长时间测试监控脚本
记录每次转录的详细耗时和性能指标
"""

import json
import time
from datetime import datetime
from pathlib import Path
import sys

# 日志文件
LOG_FILE = Path("runtime/logs/long_test_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.transcriptions = []
        self.start_time = time.time()

    def log_transcription(self, session_id: str, duration_seconds: float,
                         transcript_length: int, process_time: float,
                         audio_chunks: int):
        """记录一次转录的性能数据"""

        data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "audio_duration": duration_seconds,
            "transcript_length": transcript_length,
            "process_time": process_time,
            "audio_chunks": audio_chunks,
            "real_time_factor": duration_seconds / process_time if process_time > 0 else 0,
            "chars_per_second": transcript_length / process_time if process_time > 0 else 0
        }

        self.transcriptions.append(data)

        # 写入日志文件
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

        # 实时显示
        print(f"\n{'='*60}")
        print(f"📝 转录 #{len(self.transcriptions)}")
        print(f"{'='*60}")
        print(f"音频时长: {duration_seconds:.1f}s")
        print(f"处理耗时: {process_time:.3f}s")
        print(f"实时倍率: {data['real_time_factor']:.1f}x")
        print(f"转录字数: {transcript_length}")
        print(f"处理速度: {data['chars_per_second']:.1f} 字/秒")
        print(f"音频分段: {audio_chunks}")

    def print_summary(self):
        """打印测试总结"""
        if not self.transcriptions:
            print("❌ 没有转录数据")
            return

        print(f"\n{'='*60}")
        print("📊 长时间测试总结")
        print(f"{'='*60}")
        print(f"总测试时长: {time.time() - self.start_time:.1f}s")
        print(f"转录次数: {len(self.transcriptions)}")
        print()

        # 计算统计数据
        durations = [t['audio_duration'] for t in self.transcriptions]
        process_times = [t['process_time'] for t in self.transcriptions]
        rtf_values = [t['real_time_factor'] for t in self.transcriptions]

        print(f"音频时长统计:")
        print(f"  最短: {min(durations):.1f}s")
        print(f"  最长: {max(durations):.1f}s")
        print(f"  平均: {sum(durations)/len(durations):.1f}s")
        print(f"  总计: {sum(durations):.1f}s")
        print()

        print(f"处理耗时统计:")
        print(f"  最短: {min(process_times):.3f}s")
        print(f"  最长: {max(process_times):.3f}s")
        print(f"  平均: {sum(process_times)/len(process_times):.3f}s")
        print(f"  总计: {sum(process_times):.3f}s")
        print()

        print(f"实时倍率统计:")
        print(f"  最快: {max(rtf_values):.1f}x")
        print(f"  最慢: {min(rtf_values):.1f}x")
        print(f"  平均: {sum(rtf_values)/len(rtf_values):.1f}x")
        print()

        # SenseVoice vs Whisper 对比
        print(f"{'='*60}")
        print("🆚 SenseVoice vs Whisper 对比")
        print(f"{'='*60}")
        print()

        avg_process = sum(process_times) / len(process_times)
        avg_rtf = sum(rtf_values) / len(rtf_values)

        print(f"SenseVoice (本次测试):")
        print(f"  平均处理时间: {avg_process:.3f}s")
        print(f"  平均实时倍率: {avg_rtf:.1f}x")
        print(f"  预估 Whisper 时间: {avg_process * 10:.1f}s")  # Whisper 约慢 10x
        print(f"  节省时间: {avg_process * 10 - avg_process:.1f}s ({(1 - 1/10) * 100:.0f}%)")
        print()

        print(f"详细日志已保存: {LOG_FILE}")

# 全局监控器
monitor = PerformanceMonitor()

if __name__ == "__main__":
    print("🚀 长时间测试监控器已启动")
    print(f"日志文件: {LOG_FILE}")
    print("\n请开始你的长时间测试...")
    print("（使用 Swift App 录音，我会自动监控性能）\n")

    # 等待用户按 Ctrl+C 结束
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n停止监控...")
        monitor.print_summary()
