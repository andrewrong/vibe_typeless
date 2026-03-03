import Foundation
import os.log

/// Unified logger for TypelessApp
/// Controls log levels and reduces noise in production
enum LogLevel: Int {
    case error = 0
    case info = 1
    case debug = 2

    var osLogType: OSLogType {
        switch self {
        case .error: return .error
        case .info: return .info
        case .debug: return .debug
        }
    }
}

/// Global log level - change this to control output
#if DEBUG
let currentLogLevel: LogLevel = .debug
#else
let currentLogLevel: LogLevel = .info
#endif

/// Unified logging function
/// - Parameters:
///   - level: Log level
///   - message: Message to log
///   - file: Source file (auto)
///   - function: Function name (auto)
///   - line: Line number (auto)
func TLog(_ level: LogLevel,
          _ message: String,
          file: String = #file,
          function: String = #function,
          line: Int = #line) {
    guard level.rawValue <= currentLogLevel.rawValue else { return }

    let fileName = (file as NSString).lastPathComponent
    let prefix: String

    switch level {
    case .error:
        prefix = "❌"
    case .info:
        prefix = "ℹ️"
    case .debug:
        prefix = "🔍"
    }

    // Use NSLog for now, can be replaced with os.log later
    NSLog("\(prefix) [\(fileName):\(line)] \(message)")
}

/// Convenience methods
func TLogError(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
    TLog(.error, message, file: file, function: function, line: line)
}

func TLogInfo(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
    TLog(.info, message, file: file, function: function, line: line)
}

func TLogDebug(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
    TLog(.debug, message, file: file, function: function, line: line)
}
