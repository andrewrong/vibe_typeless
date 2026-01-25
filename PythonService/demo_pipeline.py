#!/usr/bin/env python3
"""
Comprehensive ASR + Post-Processing Pipeline Demo
Demonstrates the full speech-to-text workflow with realistic examples
"""

import httpx
import json

BASE_URL = "http://127.0.0.1:8000"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(label, data):
    """Print formatted result"""
    print(f"\n{label}:")
    if isinstance(data, dict):
        print(json.dumps(data, indent=2))
    else:
        print(f"  {data}")


def demo_full_pipeline():
    """Demonstrate the complete ASR + post-processing pipeline"""

    print_section("Typeless Speech-to-Text Pipeline Demo")

    # Scenario 1: Meeting transcription
    print("\n📝 SCENARIO 1: Meeting Transcription")
    print("-" * 70)

    meeting_text = "Um so like we should discuss the quarterly results uh I think that we need to review the sales figures first step is to look at the revenue second step is to analyze the costs and third step is to project future growth"

    print(f"\n🎤 Raw Speech Transcript:")
    print(f"  '{meeting_text}'")

    response = httpx.post(
        f"{BASE_URL}/api/postprocess/text",
        json={"text": meeting_text, "use_cloud_llm": False}
    )
    result = response.json()

    print(f"\n✨ Post-Processed Output:")
    print(f"  '{result['processed']}'")

    print(f"\n📊 Processing Statistics:")
    print(f"  • Fillers removed: {result['stats']['fillers_removed']} characters")
    print(f"  • Duplicates removed: {result['stats']['duplicates_removed']} characters")
    print(f"  • Total improvements: {result['stats']['total_changes']} characters")

    # Scenario 2: Presentation notes
    print("\n\n📝 SCENARIO 2: Presentation Notes")
    print("-" * 70)

    presentation_text = "Um first slide covers our product features uh second slide shows pricing models and third slide displays customer testimonials actually the third slide has client feedback"

    print(f"\n🎤 Raw Speech Transcript:")
    print(f"  '{presentation_text}'")

    response = httpx.post(
        f"{BASE_URL}/api/postprocess/text",
        json={"text": presentation_text, "use_cloud_llm": False}
    )
    result = response.json()

    print(f"\n✨ Post-Processed Output:")
    print(f"  '{result['processed']}'")

    print(f"\n📊 Processing Statistics:")
    print(f"  • Fillers removed: {result['stats']['fillers_removed']} characters")
    print(f"  • Duplicates removed: {result['stats']['duplicates_removed']} characters")

    # Scenario 3: Voice command with self-correction
    print("\n\n📝 SCENARIO 3: Voice Command with Self-Correction")
    print("-" * 70)

    command_text = "Set the background color to red no wait make it blue and increase the font size"

    print(f"\n🎤 Raw Speech Transcript:")
    print(f"  '{command_text}'")

    response = httpx.post(
        f"{BASE_URL}/api/postprocess/text",
        json={"text": command_text, "use_cloud_llm": False}
    )
    result = response.json()

    print(f"\n✨ Post-Processed Output:")
    print(f"  '{result['processed']}'")

    print(f"\n💡 Note: The 'no wait' self-correction pattern is detected")

    # Scenario 4: ASR Session Workflow
    print_section("Full ASR Session Workflow")

    print("\n1️⃣  Starting Transcription Session...")
    response = httpx.post(f"{BASE_URL}/api/asr/start")
    session = response.json()
    print(f"   ✓ Session ID: {session['session_id']}")
    print(f"   ✓ Status: {session['status']}")

    print("\n2️⃣  Checking Session Status...")
    response = httpx.get(f"{BASE_URL}/api/asr/status/{session['session_id']}")
    status = response.json()
    print(f"   ✓ Status: {status['status']}")
    print(f"   ✓ Audio chunks received: {status['audio_chunks_received']}")

    print("\n3️⃣  Stopping Session...")
    response = httpx.post(f"{BASE_URL}/api/asr/stop/{session['session_id']}")
    final = response.json()
    print(f"   ✓ Final transcript: '{final['final_transcript']}'")
    print(f"   ✓ Total chunks: {final['total_chunks']}")

    # Scenario 5: Custom configuration
    print_section("Custom Configuration Demo")

    print("\n🔧 Adding Custom Filler Words...")
    response = httpx.post(
        f"{BASE_URL}/api/postprocess/config",
        json={
            "mode": "rules",
            "provider": "claude",
            "custom_fillers": ["habitual", "phrase", "expression"],
            "enable_corrections": True,
            "enable_formatting": True
        }
    )
    config_result = response.json()
    print(f"   ✓ {config_result['status']}")
    print(f"   ✓ Custom fillers added: {config_result['custom_fillers_count']}")

    print("\n📋 Testing with Custom Fillers...")
    test_text = "This is a habitual phrase that I use frequently"
    response = httpx.post(
        f"{BASE_URL}/api/postprocess/text",
        json={"text": test_text, "use_cloud_llm": False}
    )
    result = response.json()
    print(f"   Original: '{test_text}'")
    print(f"   Processed: '{result['processed']}'")

    # Summary
    print_section("Pipeline Summary")

    print("\n✅ Pipeline Components:")
    print("   1. ASR Session Management")
    print("      • Start/stop sessions")
    print("      • Send audio chunks")
    print("      • Get session status")
    print("      • Direct file transcription")

    print("\n   2. Text Post-Processing")
    print("      • Rule-based cleaning")
    print("      • Filler word removal")
    print("      • Duplicate elimination")
    print("      • Self-correction detection")
    print("      • Auto-formatting")

    print("\n   3. Configuration")
    print("      • Custom filler words")
    print("      • Processing mode selection")
    print("      • Provider selection")

    print("\n🎯 Use Cases:")
    print("   • Meeting transcription and summarization")
    print("   • Voice command processing")
    print("   • Presentation note-taking")
    print("   • Dictation and documentation")

    print("\n📡 API Endpoints:")
    print("   • POST /api/asr/start - Start transcription")
    print("   • POST /api/asr/audio/{id} - Send audio")
    print("   • POST /api/asr/stop/{id} - Stop session")
    print("   • GET  /api/asr/status/{id} - Get status")
    print("   • POST /api/asr/transcribe - Full transcription")
    print("   • POST /api/postprocess/text - Process text")
    print("   • GET  /api/postprocess/config - Get config")
    print("   • POST /api/postprocess/config - Update config")
    print("   • GET  /api/postprocess/status - Get capabilities")

    print("\n" + "=" * 70)
    print("  Demo Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        demo_full_pipeline()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
