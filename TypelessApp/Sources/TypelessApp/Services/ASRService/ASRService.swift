import Foundation

/// ASR Service errors
enum ASRError: Error {
    case invalidURL
    case networkError(Error)
    case serverError(Int, String)
    case noTranscript
    case encodingFailed
    case invalidResponse
}

// MARK: - Response Models

struct SessionStartResponse: Decodable {
    let sessionId: String
    let status: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case status
    }
}

struct AudioTranscriptResponse: Decodable {
    let partialTranscript: String
    let isFinal: Bool

    enum CodingKeys: String, CodingKey {
        case partialTranscript = "partial_transcript"
        case isFinal = "is_final"
    }
}

struct SessionStopResponse: Decodable {
    let sessionId: String
    let status: String
    let finalTranscript: String
    let totalChunks: Int

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case status
        case finalTranscript = "final_transcript"
        case totalChunks = "total_chunks"
    }
}

/// ASR Service for connecting to Python backend
@MainActor
class ASRService: NSObject {
    // MARK: - Properties

    private let baseURL: String
    private var session: URLSession

    private(set) var isConnected = false

    // MARK: - Initialization

    init(baseURL: String = "http://127.0.0.1:8000") {
        self.baseURL = baseURL

        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: configuration)
    }

    // MARK: - HTTP API

    /// Send audio data for transcription
    func transcribe(audioData: Data) async throws -> String {
        let url = URL(string: "\(baseURL)/api/asr/transcribe")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.upload(for: request, from: audioData)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ASRError.networkError(URLError(.badServerResponse))
        }

        guard httpResponse.statusCode == 200 else {
            throw ASRError.serverError(httpResponse.statusCode, "HTTP error")
        }

        // Parse response
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let transcript = json["transcript"] as? String else {
            throw ASRError.noTranscript
        }

        return transcript
    }

    /// Check if backend is reachable
    func checkConnection() async -> Bool {
        let url = URL(string: "\(baseURL)/health")!
        var request = URLRequest(url: url)
        request.timeoutInterval = 5

        do {
            let (_, response) = try await session.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    // MARK: - Streaming API

    /// Start a new ASR session
    func startSession() async throws -> String {
        let url = URL(string: "\(baseURL)/api/asr/start")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ASRError.networkError(URLError(.badServerResponse))
        }

        guard httpResponse.statusCode == 200 else {
            throw ASRError.serverError(httpResponse.statusCode, "Failed to start session")
        }

        let result = try JSONDecoder().decode(SessionStartResponse.self, from: data)
        return result.sessionId
    }

    /// Send audio chunk for transcription
    func sendAudio(sessionId: String, audioData: Data) async throws -> String {
        let url = URL(string: "\(baseURL)/api/asr/audio/\(sessionId)")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.upload(for: request, from: audioData)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ASRError.networkError(URLError(.badServerResponse))
        }

        guard httpResponse.statusCode == 200 else {
            throw ASRError.serverError(httpResponse.statusCode, "Failed to send audio")
        }

        let result = try JSONDecoder().decode(AudioTranscriptResponse.self, from: data)
        return result.partialTranscript
    }

    /// Stop ASR session and get final transcript
    func stopSession(sessionId: String) async throws -> SessionStopResponse {
        let url = URL(string: "\(baseURL)/api/asr/stop/\(sessionId)")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            NSLog("❌ [ASR] Stop session: not HTTP response")
            throw ASRError.networkError(URLError(.badServerResponse))
        }

        guard httpResponse.statusCode == 200 else {
            let responseString = String(data: data, encoding: .utf8) ?? "no data"
            NSLog("❌ [ASR] Stop session failed: \(httpResponse.statusCode)")
            NSLog("❌ [ASR] Response body: \(responseString)")
            throw ASRError.serverError(httpResponse.statusCode, "Failed to stop session")
        }

        NSLog("✅ [ASR] Stop session successful, parsing response...")
        do {
            let result = try JSONDecoder().decode(SessionStopResponse.self, from: data)
            NSLog("✅ [ASR] Parsed transcript: '\(result.finalTranscript)'")
            return result
        } catch {
            NSLog("❌ [ASR] Failed to decode response: \(error)")
            let responseString = String(data: data, encoding: .utf8) ?? "no data"
            NSLog("❌ [ASR] Response was: \(responseString)")
            throw error
        }
    }
}
