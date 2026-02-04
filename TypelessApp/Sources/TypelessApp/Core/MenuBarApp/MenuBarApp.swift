import AppKit
import SwiftUI

/// Menu bar app for background recording control
@MainActor
class MenuBarApp: NSObject {
    // MARK: - Properties

    private var statusItem: NSStatusItem?
    private var backgroundManager: BackgroundRecordingManager?
    var isRecording = false

    // MARK: - Initialization

    override init() {
        super.init()

        setupMenuBar()
        backgroundManager = BackgroundRecordingManager()
    }

    // MARK: - Setup

    private func setupMenuBar() {
        // Create status item in menu bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        // Set icon
        let idleIcon = NSImage(systemSymbolName: "mic.circle", accessibilityDescription: "Typeless")
        statusItem?.button?.image = idleIcon
        statusItem?.button?.imagePosition = .imageLeft

        // Set tooltip
        statusItem?.button?.toolTip = "Typeless - Press Right Control to record, ESC to cancel"

        // Create menu
        let menu = NSMenu()

        // Start/Stop Recording menu item
        let toggleItem = NSMenuItem(
            title: "Start Recording",
            action: #selector(toggleRecording),
            keyEquivalent: ""
        )
        toggleItem.target = self
        menu.addItem(toggleItem)

        // Cancel Recording menu item (hidden by default)
        let cancelItem = NSMenuItem(
            title: "Cancel Recording (ESC)",
            action: #selector(cancelRecordingMenu),
            keyEquivalent: ""
        )
        cancelItem.target = self
        cancelItem.isHidden = true
        cancelItem.tag = 999  // Tag to find this item later
        menu.addItem(cancelItem)

        // Separator
        menu.addItem(NSMenuItem.separator())

        // Show Window menu item
        let showWindowItem = NSMenuItem(
            title: "Show Window",
            action: #selector(showWindow),
            keyEquivalent: ""
        )
        showWindowItem.target = self
        menu.addItem(showWindowItem)

        // Separator
        menu.addItem(NSMenuItem.separator())

        // Quit menu item
        let quitItem = NSMenuItem(
            title: "Quit Typeless",
            action: #selector(terminate),
            keyEquivalent: "q"
        )
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem?.menu = menu

        print("✅ Menu bar setup complete with Right Control (toggle) and ESC (cancel) shortcuts")
    }

    // MARK: - Actions

    @objc func toggleRecording() {
        isRecording.toggle()

        Task { @MainActor in
            if isRecording {
                startRecording()
            } else {
                stopRecording()
            }
        }
    }

    @objc func cancelRecordingMenu() {
        Task {
            await cancelRecording()
        }
    }

    func cancelRecording() async {
        print("⚠️ [MenuBar] Cancelling recording...")
        isRecording = false
        updateStatus(recording: false)

        await backgroundManager?.cancelRecording()
    }

    private func startRecording() {
        print("🎙️ [MenuBar] Starting recording...")
        updateStatus(recording: true)

        Task { @MainActor in
            await backgroundManager?.startRecording()
        }
    }

    private func stopRecording() {
        print("⏹️ [MenuBar] Stopping recording...")
        updateStatus(recording: false)

        Task { @MainActor in
            await backgroundManager?.stopRecording()
        }
    }

    @objc private func showWindow() {
        // Bring main window to front
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc private func terminate() {
        NSApplication.shared.terminate(nil)
    }

    // MARK: - Helper Methods

    private func updateStatus(recording: Bool) {
        let recordingIcon = NSImage(systemSymbolName: "record.circle.fill", accessibilityDescription: "Recording")
        let idleIcon = NSImage(systemSymbolName: "mic.circle", accessibilityDescription: "Idle")

        statusItem?.button?.image = recording ? recordingIcon : idleIcon

        if recording {
            statusItem?.button?.toolTip = "Stop: Right Control | Cancel: ESC"
            if let menu = statusItem?.menu {
                // Update first item
                if let item = menu.items.first {
                    item.title = "Stop Recording (Right Control)"
                }
                // Show cancel item (tag 999)
                if let cancelItem = menu.items.first(where: { $0.tag == 999 }) {
                    cancelItem.isHidden = false
                }
            }
        } else {
            statusItem?.button?.toolTip = "Start Recording (Right Control)"
            if let menu = statusItem?.menu {
                // Update first item
                if let item = menu.items.first {
                    item.title = "Start Recording (Right Control)"
                }
                // Hide cancel item (tag 999)
                if let cancelItem = menu.items.first(where: { $0.tag == 999 }) {
                    cancelItem.isHidden = true
                }
            }
        }
    }
}

