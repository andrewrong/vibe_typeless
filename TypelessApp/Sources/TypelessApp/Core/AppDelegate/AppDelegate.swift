import AppKit
import Cocoa
import SwiftUI

/// App delegate for background operation
class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarApp: MenuBarApp?
    private var eventMonitor: Any?
    private var wasRightControlDown = false  // Track previous state

    func applicationDidFinishLaunching(_ notification: Notification) {
        print("🚀 Application launched in background mode")

        // Initialize menu bar app (which also handles global hotkey via menu items)
        menuBarApp = MenuBarApp()

        // Set activation policy to run as regular app with menu bar
        NSApp.setActivationPolicy(.regular)

        // Set up Right Control key monitoring
        setupRightControlMonitor()

        print("✅ Background service ready with Right Control hotkey")
    }

    func setupRightControlMonitor() {
        // Monitor for Right Control key using modifier flags
        eventMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.flagsChanged]) { [weak self] event in
            guard let self = self else { return }

            // Right Control key code is 62 (0x3E)
            // We check both keyCode and modifierFlags
            if event.keyCode == 62 {
                let isRightControlDown = event.modifierFlags.contains(.control)

                // Only trigger on key down (not up) - transition from false to true
                if isRightControlDown && !self.wasRightControlDown {
                    NSLog("🎯 Right Control pressed - toggling recording")
                    let menuBar = self.menuBarApp
                    Task { @MainActor in
                        menuBar?.toggleRecording()
                    }
                }

                // Update state
                self.wasRightControlDown = isRightControlDown
            }
        }

        print("✅ Right Control hotkey registered")
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Remove event monitor
        if let monitor = eventMonitor {
            NSEvent.removeMonitor(monitor)
        }
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        // Allow termination
        return .terminateNow
    }
}
