// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ShapeNoteAtlasApp",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "ShapeNoteAtlas", targets: ["ShapeNoteAtlas"])
    ],
    targets: [
        .executableTarget(
            name: "ShapeNoteAtlas",
            path: "Sources/ShapeNoteAtlas"
        )
    ]
)
