import Foundation

/// Execute an async operation with a timeout
/// - Parameters:
///   - seconds: Timeout duration in seconds
///   - operation: The async operation to execute
/// - Returns: The result of the operation, or nil if timed out
func withTimeout<T>(seconds: TimeInterval, operation: @escaping () async -> T?) async -> T? {
    await withTaskGroup(of: T?.self) { group -> T? in
        // Add the actual operation
        group.addTask {
            await operation()
        }

        // Add timeout task
        group.addTask {
            try? await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
            return nil
        }

        // Return the first to complete
        let result = await group.next()
        group.cancelAll()
        // Flatten T?? to T?
        if let result = result {
            return result
        }
        return nil
    }
}
