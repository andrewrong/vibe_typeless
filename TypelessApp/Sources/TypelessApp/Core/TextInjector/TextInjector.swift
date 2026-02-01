import AppKit

/// Text injection errors
enum TextInjectorError: Error {
    case noFocusedElement
    case injectionFailed
    case accessDenied
}

/// Text injector for inserting text at cursor position
@MainActor
class TextInjector {

    // MARK: - Injection

    /// Inject text at current cursor position
    func inject(text: String) async throws {
        guard !text.isEmpty else { return }

        // Copy to clipboard
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)

        // Simulate Cmd+V to paste
        simulatePaste()

        // Wait for paste to complete
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds
    }

    /// Get currently focused application
    func getFocusedApplication() -> NSRunningApplication? {
        let workspace = NSWorkspace.shared
        return workspace.frontmostApplication
    }

    // MARK: - Helpers

    /// Simulate paste command (Cmd+V)
    private func simulatePaste() {
        let source = CGEventSource(stateID: .hidSystemState)

        // Cmd key down
        let cmdDown = CGEvent(keyboardEventSource: source, virtualKey: 0x37, keyDown: true)
        cmdDown?.flags = .maskCommand
        cmdDown?.post(tap: .cghidEventTap)

        // V key down
        let vDown = CGEvent(keyboardEventSource: source, virtualKey: 0x09, keyDown: true)
        vDown?.flags = .maskCommand
        vDown?.post(tap: .cghidEventTap)

        // V key up
        let vUp = CGEvent(keyboardEventSource: source, virtualKey: 0x09, keyDown: false)
        vUp?.flags = .maskCommand
        vUp?.post(tap: .cghidEventTap)

        // Cmd key up
        let cmdUp = CGEvent(keyboardEventSource: source, virtualKey: 0x37, keyDown: false)
        cmdUp?.post(tap: .cghidEventTap)
    }
}
