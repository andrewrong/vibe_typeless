import AppKit
import Foundation

// Print version info on startup
NSLog("🚀 Typeless Swift v\(Version.fullVersion)")

// Create the app with app delegate
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate

// Run the app
app.run()
