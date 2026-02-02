import AppKit
import SwiftUI

/// Real-time transcription preview window
/// Shows partial transcripts during recording
class PreviewWindow: NSWindow {
    private var viewModel: PreviewViewModel

    init() {
        let viewModel = PreviewViewModel()
        self.viewModel = viewModel

        // Create the content view
        let contentView = PreviewView(viewModel: viewModel)

        // Initialize window
        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 400, height: 200),
            styleMask: [.titled, .closable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )

        self.title = "Typeless - 实时预览"
        self.contentViewController = NSHostingController(rootView: contentView)
        self.center()
        self.level = .floating  // Keep above other windows

        // Appearance
        self.backgroundColor = NSColor.windowBackgroundColor
        self.isMovableByWindowBackground = false

        NSLog("✅ Preview window created")
    }

    /// Update preview text
    func updateText(_ text: String) {
        viewModel.updateText(text)
    }

    /// Clear preview text
    func clear() {
        viewModel.clear()
    }

    /// Show window
    func show() {
        self.makeKeyAndOrderFront(nil)
        NSLog("📺 Preview window shown")
    }

    /// Hide window
    func hide() {
        self.orderOut(nil)
        NSLog("📺 Preview window hidden")
    }
}

/// Preview view model
@MainActor
class PreviewViewModel: ObservableObject {
    @Published var previewText: String = ""
    @Published var isVisible: Bool = false

    func updateText(_ text: String) {
        // Append new text (don't overwrite)
        if !text.isEmpty && text != previewText {
            self.previewText = text
            NSLog("📝 Preview updated: '\(text.prefix(50))...'")
        }
    }

    func clear() {
        self.previewText = ""
        NSLog("🧹 Preview cleared")
    }
}

/// SwiftUI preview view
struct PreviewView: View {
    @ObservedObject var viewModel: PreviewViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Image(systemName: "waveform")
                    .font(.system(size: 16))
                    .foregroundColor(.accentColor)

                Text("实时转录预览")
                    .font(.headline)

                Spacer()

                Text("录音中...")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)
            .padding(.top, 8)

            // Preview text
            ScrollView {
                Text(viewModel.previewText)
                    .font(.system(size: 14))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
            .background(Color(NSColor.controlBackgroundColor))
            .cornerRadius(8)
        }
        .frame(minHeight: 150)
        .padding()
    }
}
