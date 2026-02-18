import Foundation

/// Typeless App Version Information
enum Version {
    /// Semantic version (e.g., "0.2.0")
    static let version = "0.2.0"

    /// Build date (e.g., "20250218")
    static let build = "20250218"

    /// Git commit hash (short)
    static let commit = "03612b5"

    /// Service name
    static let service = "typeless-swift"

    /// Full version string (e.g., "0.2.0+20250218 (03612b5)")
    static var fullVersion: String {
        "\(version)+\(build) (\(commit))"
    }

    /// Version info dictionary for API
    static var info: [String: String] {
        [
            "version": version,
            "build": build,
            "commit": commit,
            "service": service
        ]
    }
}
