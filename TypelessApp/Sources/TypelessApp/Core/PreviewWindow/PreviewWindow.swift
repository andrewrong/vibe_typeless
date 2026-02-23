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

    func setRecordingState(_ state: RecordingState) {
        viewModel.setRecordingState(state)
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

enum RecordingState {
    case idle
    case preparing
    case recording
}

@MainActor
class PreviewViewModel: ObservableObject {
    @Published var previewText: String = ""
    @Published var recordingState: RecordingState = .idle

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

    func setRecordingState(_ state: RecordingState) {
        self.recordingState = state
        NSLog("Recording state changed: \(state)")
    }
}

struct PreviewView: View {
    @ObservedObject var viewModel: PreviewViewModel

    var statusText: String {
        switch viewModel.recordingState {
        case .idle:
            return ""
        case .preparing:
            return "准备中..."
        case .recording:
            return "录音中..."
        }
    }

    var statusColor: Color {
        switch viewModel.recordingState {
        case .idle:
            return .secondary
        case .preparing:
            return .orange
        case .recording:
            return .green
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "waveform")
                    .font(.system(size: 16))
                    .foregroundColor(statusColor)

                Text("Live Preview")
                    .font(.headline)

                Spacer()

                Text(statusText)
                    .font(.caption)
                    .foregroundColor(statusColor)
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
