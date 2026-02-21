// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TypelessApp",
    platforms: [
        .macOS(.v14)
    ],
    dependencies: [
        .package(
            url: "https://github.com/apple/swift-testing.git",
            from: "0.10.0"
        ),
    ],
    targets: [
        .executableTarget(
            name: "TypelessApp",
            dependencies: [],
            linkerSettings: [
                .linkedFramework("SwiftUI"),
                .linkedFramework("AppKit"),
                .linkedFramework("AVFoundation"),
                .linkedFramework("Foundation"),
                .linkedFramework("Carbon")
            ]
        ),
        .testTarget(
            name: "TypelessAppTests",
            dependencies: [
                "TypelessApp",
                .product(name: "Testing", package: "swift-testing"),
            ]
        ),
    ]
)
