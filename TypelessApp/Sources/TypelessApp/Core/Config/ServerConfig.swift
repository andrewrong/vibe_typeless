import Foundation

/// Server configuration management
class ServerConfig {
    static let shared = ServerConfig()

    private let defaults = UserDefaults.standard
    private let serverURLKey = "typeless.serverURL"

    /// Default local server URL
    static let defaultServerURL = "http://127.0.0.1:28111"

    /// Get the configured server URL
    var serverURL: String {
        get {
            return defaults.string(forKey: serverURLKey) ?? ServerConfig.defaultServerURL
        }
        set {
            defaults.set(newValue, forKey: serverURLKey)
        }
    }

    /// Check if using remote server (not localhost)
    var isRemoteServer: Bool {
        let url = serverURL.lowercased()
        return !url.contains("127.0.0.1") && !url.contains("localhost")
    }

    /// Validate server URL format
    func validateURL(_ urlString: String) -> Bool {
        guard let url = URL(string: urlString),
              url.scheme?.hasPrefix("http") == true,
              url.host != nil else {
            return false
        }
        return true
    }

    /// Test connection to server
    func testConnection() async -> Bool {
        guard let url = URL(string: serverURL) else { return false }
        let healthURL = url.appendingPathComponent("/health")

        do {
            let (_, response) = try await URLSession.shared.data(from: healthURL)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}
