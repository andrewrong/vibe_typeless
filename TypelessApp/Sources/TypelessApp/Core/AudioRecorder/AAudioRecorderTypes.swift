import AVFoundation
import Foundation

/// Audio recording errors
enum AudioRecorderError: Error {
    case notAuthorized
    case configurationFailed
    case recordingFailed(Error)
}

/// Audio recorder delegate - supports any recorder type
@MainActor
protocol AudioRecorderDelegate: AnyObject {
    func audioRecorder(_ recorder: AnyObject, didOutputAudioBuffer buffer: AVAudioBuffer, data: Data, isFinal: Bool)
    func audioRecorder(_ recorder: AnyObject, didEncounterError error: AudioRecorderError)
    /// Called when the final audio chunk has been sent
    func audioRecorderDidFinishSendingFinalChunk(_ recorder: AnyObject)
}
