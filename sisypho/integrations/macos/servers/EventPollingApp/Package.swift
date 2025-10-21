// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EventPollingAppCLI",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "event-polling-cli",
            targets: ["EventPollingAppCLI"]
        )
    ],
    targets: [
        .executableTarget(
            name: "EventPollingAppCLI",
            path: "EventPollingApp",
            exclude: [
                "EventPollingApp.swift",
                "AppDelegate.swift",
                "Assets.xcassets",
                "EventPollingApp.entitlements"
            ],
            sources: [
                "main.swift",
                "EventQueue.swift",
                "UserEvent.swift",
                "ElementInfo.swift",
                "EventPollingMonitor.swift",
                "EventServer.swift"
            ]
        )
    ]
)
