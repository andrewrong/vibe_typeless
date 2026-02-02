import AppKit
import SwiftUI

/// Real-time transcription preview window
class PreviewWindow: NSWindow {
    private var viewModel: PreviewViewModel

    init() {
        viewModel = PreviewViewModel()

        let contentView = PreviewView(viewModel: viewModel)

        super.init(
            contentRect: NSRect(x: 0, y: 0, width: 400, height: 200),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )

        self.title = "Typeless - Live Preview"
        self.contentViewController = NSHostingController(rootView: contentView)
        self.center()
        self.level = .floating

        NSLog("Preview window created")
    }

    func updateText(_ text: String) {
        viewModel.updateText(text)
    }

    func clear() {
        viewModel.clear()
    }

    func show() {
        self.makeKeyAndOrderFront(nil)
        NSLog("Preview window shown")
    }

    func hide() {
        self.orderOut(nil)
        NSLog("Preview window hidden")
    }
}

@MainActor
class PreviewViewModel: ObservableObject {
    @Published var previewText: String = ""

    func updateText(_ text: String) {
        if !text.isEmpty && text != previewText {
            self.previewText = text
            NSLog("Preview updated")
        }
    }

    func clear() {
        self.previewText = ""
        NSLog("Preview cleared")
    }
}

struct PreviewView: View {
    @ObservedObject var viewModel: PreviewViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "waveform")
                    .font(.system(size: 16))
                    .foregroundColor(.accentColor)

                Text("Live Preview")
                    .font(.headline)

                Spacer()

                Text("Recording...")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)
            .padding(.top, 8)

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
