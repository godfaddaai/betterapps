// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "DebateTVAIDebateArena",
    platforms: [
        .macOS(.v14), .iOS(.v17)
    ],
    products: [
        .executable(name: "DebateTVAIDebateArenaApp", targets: ["App"])
    ],
    targets: [
        .executableTarget(
            name: "App",
            path: "Sources/App"
        )
    ]
)
