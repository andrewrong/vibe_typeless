import AppKit
import SwiftUI
import Carbon

/// Hotkey manager for global hotkey control
@MainActor
class HotkeyManager: NSObject {
    // MARK: - Properties

    private var eventHotKeyRef: EventHotKeyRef?
    private var hotkeyAction: (() async -> Void)?

    // MARK: - Public Methods

    /// Register global hotkey using Carbon API
    func registerHotkey(keyCode: UInt32, modifiers: UInt32, action: @escaping () async -> Void) throws {
        self.hotkeyAction = action

        var eventType = EventTypeSpec(eventClass: OSType(kEventClassKeyboard),
                                        eventKind: UInt32(kEventHotKeyPressed))

        let userData = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())

        let hotkeyID = EventHotKeyID(signature: OSType(0x5459504C), id: 1) // 'TYPL'

        var error = InstallEventHandler(GetApplicationEventTarget(), { (nextHandler, theEvent, userData) -> OSStatus in
            guard let userData = userData else { return noErr }
            let manager = Unmanaged<HotkeyManager>.fromOpaque(userData).takeUnretainedValue()

            Task { @MainActor in
                await manager.hotkeyAction?()
            }

            return noErr
        }, 1, &eventType, userData, nil)

        if error != noErr {
            throw HotkeyError.failedToInstallHandler
        }

        error = RegisterEventHotKey(keyCode, modifiers, hotkeyID, GetApplicationEventTarget(), 0, &eventHotKeyRef)

        if error != noErr {
            throw HotkeyError.failedToRegisterHotkey
        }

        print("✅ Global hotkey registered: keyCode=\(keyCode), modifiers=\(modifiers)")
    }

    /// Register Right Control key as global hotkey
    func registerRightControlHotkey(action: @escaping () async -> Void) throws {
        self.hotkeyAction = action

        var eventType = EventTypeSpec(eventClass: OSType(kEventClassKeyboard),
                                        eventKind: UInt32(kEventHotKeyReleased))

        let userData = UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque())

        let hotkeyID = EventHotKeyID(signature: OSType(0x5459504C), id: 1) // 'TYPL'

        // Right Control key (kbd.control, which is 0x36)
        // Use 0 as modifier to detect just the key press without other modifiers
        var error = InstallEventHandler(GetApplicationEventTarget(), { (nextHandler, theEvent, userData) -> OSStatus in
            guard let userData = userData else { return noErr }
            let manager = Unmanaged<HotkeyManager>.fromOpaque(userData).takeUnretainedValue()

            Task { @MainActor in
                await manager.hotkeyAction?()
            }

            return noErr
        }, 1, &eventType, userData, nil)

        if error != noErr {
            throw HotkeyError.failedToInstallHandler
        }

        // Register Right Control (0x36) with no modifiers
        error = RegisterEventHotKey(0x36, 0, hotkeyID, GetApplicationEventTarget(), 0, &eventHotKeyRef)

        if error != noErr {
            throw HotkeyError.failedToRegisterHotkey
        }

        print("✅ Right Control hotkey registered")
    }

    /// Unregister hotkey
    func unregisterHotkey() {
        if let hotKeyRef = eventHotKeyRef {
            UnregisterEventHotKey(hotKeyRef)
            eventHotKeyRef = nil
        }
    }

    // MARK: - Error Types

    enum HotkeyError: Error {
        case failedToInstallHandler
        case failedToRegisterHotkey
    }
}
