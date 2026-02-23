import AppKit
import SwiftUI

/// Menu bar app for background recording control
@MainActor
class MenuBarApp: NSObject {
    // MARK: - Properties

    private var statusItem: NSStatusItem?
    private var backgroundManager: BackgroundRecordingManager?
    var isRecording = false

    enum RecordingState {
        case idle
        case preparing
        case recording
    }

    // MARK: - Initialization

    override init() {
        super.init()

        setupMenuBar()
        backgroundManager = BackgroundRecordingManager(menuBarApp: self)
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
        let state: RecordingState = recording ? .recording : .idle
        updateMenuBarState(state)
    }

    private var currentState: RecordingState = .idle

    var isRecordingState: Bool {
        return currentState == .recording
    }

    func updateMenuBarState(_ state: RecordingState) {
        currentState = state
        var iconName: String
        var color: NSColor
        var tooltip: String
        var menuTitle: String

        switch state {
        case .idle:
            iconName = "mic.circle"
            color = .systemGray
            tooltip = "Start Recording (Right Control)"
            menuTitle = "Start Recording (Right Control)"
            NSLog("📱 State: idle")
        case .preparing:
            iconName = "mic.circle.fill"
            color = .systemOrange
            tooltip = "Preparing... (please wait)"
            menuTitle = "Preparing..."
            NSLog("📱 State: preparing")
        case .recording:
            iconName = "mic.circle.fill"
            color = .systemGreen
            tooltip = "Recording... (Right Control to stop, ESC to cancel)"
            menuTitle = "Stop Recording (Right Control)"
            NSLog("📱 State: recording")
        }

        // Update icon with color
        if let image = NSImage(systemSymbolName: iconName, accessibilityDescription: nil) {
            let config = NSImage.SymbolConfiguration(paletteColors: [color])
            statusItem?.button?.image = image.withSymbolConfiguration(config)
        }

        statusItem?.button?.toolTip = tooltip

        // Update menu
        if let menu = statusItem?.menu {
            if let item = menu.items.first {
                item.title = menuTitle
            }
            if let cancelItem = menu.items.first(where: { $0.tag == 999 }) {
                cancelItem.isHidden = (state != .recording)
            }
        }
    }
}

