import AppKit
import Cocoa
import SwiftUI

/// App delegate for background operation
class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarApp: MenuBarApp?
    private var eventMonitor: Any?
    private var monitorFlags: Any?
    private var wasRightControlDown = false  // Track previous state

    func applicationDidFinishLaunching(_ notification: Notification) {
        print("🚀 Application launched in background mode")

        // Initialize menu bar app (which also handles global hotkey via menu items)
        menuBarApp = MenuBarApp()

        // Set activation policy to run as regular app with menu bar
        NSApp.setActivationPolicy(.regular)

        // Set up Right Control key monitoring for toggle
        setupRightControlMonitor()

        // Set up ESC key monitoring for cancel
        setupEscapeMonitor()

        print("✅ Background service ready with Right Control (toggle) and ESC (cancel) hotkeys")
    }

    func setupRightControlMonitor() {
        // Monitor for Right Control key using modifier flags
        eventMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.flagsChanged]) { [weak self] event in
            guard let self = self else { return }

            // Right Control key code is 62 (0x3E)
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

    func setupEscapeMonitor() {
        // Monitor for ESC key to cancel recording
        // ESC key code is 53 (0x35)
        monitorFlags = NSEvent.addGlobalMonitorForEvents(matching: [.keyDown]) { [weak self] event in
            guard let self = self else { return }

            if event.keyCode == 53 {  // ESC key
                // Check if recording is active
                let menuBar = self.menuBarApp
                Task { @MainActor in
                    if menuBar?.isRecording == true {
                        NSLog("⚠️ ESC pressed - cancelling recording")
                        await menuBar?.cancelRecording()
                    }
                }
            }
        }

        print("✅ ESC (cancel) hotkey registered")
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Remove event monitors
        if let monitor = eventMonitor {
            NSEvent.removeMonitor(monitor)
        }
        if let monitor = monitorFlags {
            NSEvent.removeMonitor(monitor)
        }
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        // Allow termination
        return .terminateNow
    }
}
