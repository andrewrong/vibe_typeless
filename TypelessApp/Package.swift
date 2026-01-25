// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "TypelessApp",
    targets: [
        .executableTarget(
            name: "TypelessApp"
        ),
        .testTarget(
            name: "TypelessAppTests",
            dependencies: ["TypelessApp"]
        ),
    ]
)
