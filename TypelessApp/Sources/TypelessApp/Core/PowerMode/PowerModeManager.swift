import Foundation
import AppKit

/// Application category for Power Mode
enum AppCategory {
    case coding       // Xcode, VS Code, etc.
    case writing      // Notion, Word, etc.
    case chat         // WeChat, Slack, etc.
    case browser      // Chrome, Safari, etc.
    case terminal     // Terminal, iTerm2
    case general      // Default

    /// Get category from bundle identifier
    static func from(bundleId: String) -> AppCategory {
        // Coding apps
        if bundleId.contains("com.apple.dt.Xcode") ||
           bundleId.contains("com.microsoft.VSCode") ||
           bundleId.contains("com.jetbrains") ||
           bundleId.contains("com.sublimetext") {
            return .coding
        }

        // Writing apps
        if bundleId.contains("notion.id") ||
           bundleId.contains("com.microsoft.Word") ||
           bundleId.contains("com.apple.iWork.Pages") {
            return .writing
        }

        // Chat apps
        if bundleId.contains("com.tencent.xinWeChat") ||
           bundleId.contains("com.tencent.WeChatMac") ||
           bundleId.contains("com.hnc.Discord") ||
           bundleId.contains("com.tinyspeck.slackmacgap") {
            return .chat
        }

        // Browser apps
        if bundleId.contains("com.google.Chrome") ||
           bundleId.contains("com.apple.Safari") ||
           bundleId.contains("org.mozilla.firefox") {
            return .browser
        }

        // Terminal apps
        if bundleId.contains("com.apple.Terminal") ||
           bundleId.contains("com.googlecode.iterm2") ||
           bundleId.contains("co.zendesk.GitHub") {
            return .terminal
        }

        return .general
    }
}

/// Transcription configuration for each app category
struct TranscriptionConfig {
    var addPunctuation: Bool = true
    var preserveFormatting: Bool = false
    var preserveCase: Bool = false
    var technicalTerms: Bool = false
    var removeFillers: Bool = false
    var casualMode: Bool = false

    /// Get default config for app category
    static func forCategory(_ category: AppCategory) -> TranscriptionConfig {
        switch category {
        case .coding:
            return TranscriptionConfig(
                addPunctuation: false,        // Code doesn't need punctuation
                preserveFormatting: true,     // Keep spacing and structure
                preserveCase: true,           // Keep variable names case
                technicalTerms: true,         // Recognize tech terms
                removeFillers: true,          // Remove um, uh, etc.
                casualMode: false
            )

        case .writing:
            return TranscriptionConfig(
                addPunctuation: true,         // Add proper punctuation
                preserveFormatting: true,     // Keep paragraphs
                preserveCase: false,          // Normalize capitalization
                technicalTerms: false,
                removeFillers: true,
                casualMode: false
            )

        case .chat:
            return TranscriptionConfig(
                addPunctuation: true,         // Casual punctuation
                preserveFormatting: false,
                preserveCase: false,
                technicalTerms: false,
                removeFillers: false,         // Keep natural speech pattern
                casualMode: true              // More casual style
            )

        case .browser:
            return TranscriptionConfig(
                addPunctuation: true,
                preserveFormatting: false,
                preserveCase: false,
                technicalTerms: false,
                removeFillers: true,
                casualMode: false
            )

        case .terminal:
            return TranscriptionConfig(
                addPunctuation: false,        // Commands don't need punctuation
                preserveFormatting: true,
                preserveCase: true,           // Commands are case-sensitive
                technicalTerms: true,
                removeFillers: true,
                casualMode: false
            )

        case .general:
            return TranscriptionConfig(
                addPunctuation: true,
                preserveFormatting: false,
                preserveCase: false,
                technicalTerms: false,
                removeFillers: true,
                casualMode: false
            )
        }
    }
}

/// Power Mode Manager - detects app and applies optimized settings
@MainActor
class PowerModeManager {
    private var currentCategory: AppCategory = .general
    private var currentConfig: TranscriptionConfig = TranscriptionConfig.forCategory(.general)

    /// Detect current frontmost app and update config
    func detectAndUpdate() -> TranscriptionConfig {
        guard let bundleId = NSWorkspace.shared.frontmostApplication?.bundleIdentifier else {
            return currentConfig
        }

        let category = AppCategory.from(bundleId: bundleId)
        currentCategory = category
        currentConfig = TranscriptionConfig.forCategory(category)

        NSLog("📱 Power Mode: \(bundleId) → \(category)")
        NSLog("   Config: punctuation=\(currentConfig.addPunctuation), technical=\(currentConfig.technicalTerms)")

        return currentConfig
    }

    /// Get current config
    func getConfig() -> TranscriptionConfig {
        return currentConfig
    }

    /// Get current category
    func getCategory() -> AppCategory {
        return currentCategory
    }
}
