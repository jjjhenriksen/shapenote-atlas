import SwiftUI

struct AtlasPalette {
    let accent: Color
    let tint: Color
    let ink: Color
    let muted: Color
}

enum AtlasTheme {
    static let fallback = AtlasPalette(
        accent: Color(red: 0.835, green: 0.706, blue: 0.431),
        tint: Color(red: 0.047, green: 0.090, blue: 0.075),
        ink: Color(red: 0.945, green: 0.918, blue: 0.863),
        muted: Color(red: 0.682, green: 0.733, blue: 0.690)
    )

    static func palette(bookId: String, mode: String) -> AtlasPalette {
        let dark = mode == "dark"
        switch bookId {
        case "sh1991":
            return dark
                ? AtlasPalette(accent: Color(red: 0.851, green: 0.706, blue: 0.427), tint: Color(red: 0.137, green: 0.063, blue: 0.075), ink: Color(red: 0.980, green: 0.937, blue: 0.886), muted: Color(red: 0.824, green: 0.737, blue: 0.706))
                : AtlasPalette(accent: Color(red: 0.773, green: 0.631, blue: 0.353), tint: Color(red: 0.965, green: 0.906, blue: 0.847), ink: Color(red: 0.165, green: 0.090, blue: 0.082), muted: Color(red: 0.467, green: 0.349, blue: 0.333))
        case "sh2025":
            return dark
                ? AtlasPalette(accent: Color(red: 0.890, green: 0.769, blue: 0.514), tint: Color(red: 0.063, green: 0.094, blue: 0.082), ink: Color(red: 0.929, green: 0.949, blue: 0.914), muted: Color(red: 0.718, green: 0.769, blue: 0.737))
                : AtlasPalette(accent: Color(red: 0.831, green: 0.690, blue: 0.416), tint: Color(red: 0.933, green: 0.949, blue: 0.906), ink: Color(red: 0.078, green: 0.125, blue: 0.094), muted: Color(red: 0.333, green: 0.384, blue: 0.345))
        case "shcooper2012":
            return dark
                ? AtlasPalette(accent: Color(red: 0.769, green: 0.812, blue: 0.867), tint: Color(red: 0.067, green: 0.094, blue: 0.141), ink: Color(red: 0.918, green: 0.945, blue: 0.984), muted: Color(red: 0.698, green: 0.749, blue: 0.816))
                : AtlasPalette(accent: Color(red: 0.620, green: 0.698, blue: 0.784), tint: Color(red: 0.949, green: 0.922, blue: 0.875), ink: Color(red: 0.094, green: 0.153, blue: 0.224), muted: Color(red: 0.400, green: 0.451, blue: 0.518))
        case "ch7":
            return dark
                ? AtlasPalette(accent: Color(red: 0.843, green: 0.765, blue: 0.608), tint: Color(red: 0.098, green: 0.086, blue: 0.075), ink: Color(red: 0.949, green: 0.925, blue: 0.886), muted: Color(red: 0.792, green: 0.741, blue: 0.659))
                : AtlasPalette(accent: Color(red: 0.310, green: 0.263, blue: 0.200), tint: Color(red: 0.969, green: 0.945, blue: 0.898), ink: Color(red: 0.125, green: 0.106, blue: 0.086), muted: Color(red: 0.404, green: 0.373, blue: 0.314))
        case "shenandoah":
            return dark
                ? AtlasPalette(accent: Color(red: 0.843, green: 0.745, blue: 0.561), tint: Color(red: 0.094, green: 0.078, blue: 0.063), ink: Color(red: 0.953, green: 0.929, blue: 0.898), muted: Color(red: 0.812, green: 0.745, blue: 0.651))
                : AtlasPalette(accent: Color(red: 0.561, green: 0.455, blue: 0.310), tint: Color(red: 0.949, green: 0.918, blue: 0.863), ink: Color(red: 0.133, green: 0.106, blue: 0.082), muted: Color(red: 0.435, green: 0.376, blue: 0.310))
        case "southernharmony":
            return dark
                ? AtlasPalette(accent: Color(red: 0.867, green: 0.725, blue: 0.553), tint: Color(red: 0.094, green: 0.067, blue: 0.047), ink: Color(red: 0.957, green: 0.918, blue: 0.863), muted: Color(red: 0.816, green: 0.737, blue: 0.667))
                : AtlasPalette(accent: Color(red: 0.482, green: 0.306, blue: 0.173), tint: Color(red: 0.961, green: 0.914, blue: 0.824), ink: Color(red: 0.133, green: 0.086, blue: 0.047), muted: Color(red: 0.435, green: 0.349, blue: 0.278))
        case "kentucky":
            return dark
                ? AtlasPalette(accent: Color(red: 0.867, green: 0.706, blue: 0.529), tint: Color(red: 0.094, green: 0.071, blue: 0.051), ink: Color(red: 0.957, green: 0.918, blue: 0.875), muted: Color(red: 0.816, green: 0.749, blue: 0.682))
                : AtlasPalette(accent: Color(red: 0.545, green: 0.365, blue: 0.220), tint: Color(red: 0.957, green: 0.902, blue: 0.812), ink: Color(red: 0.141, green: 0.090, blue: 0.051), muted: Color(red: 0.439, green: 0.341, blue: 0.271))
        case "mnharmony":
            return dark
                ? AtlasPalette(accent: Color(red: 0.604, green: 0.824, blue: 0.816), tint: Color(red: 0.059, green: 0.090, blue: 0.094), ink: Color(red: 0.929, green: 0.965, blue: 0.957), muted: Color(red: 0.722, green: 0.816, blue: 0.812))
                : AtlasPalette(accent: Color(red: 0.184, green: 0.435, blue: 0.455), tint: Color(red: 0.918, green: 0.953, blue: 0.937), ink: Color(red: 0.078, green: 0.145, blue: 0.149), muted: Color(red: 0.349, green: 0.443, blue: 0.443))
        case "sacredharptunes":
            return dark
                ? AtlasPalette(accent: Color(red: 0.725, green: 0.796, blue: 0.937), tint: Color(red: 0.063, green: 0.082, blue: 0.125), ink: Color(red: 0.933, green: 0.953, blue: 0.984), muted: Color(red: 0.741, green: 0.788, blue: 0.875))
                : AtlasPalette(accent: Color(red: 0.306, green: 0.435, blue: 0.682), tint: Color(red: 0.933, green: 0.949, blue: 0.984), ink: Color(red: 0.086, green: 0.129, blue: 0.208), muted: Color(red: 0.361, green: 0.404, blue: 0.506))
        case "trumpet":
            return dark
                ? AtlasPalette(accent: Color(red: 0.882, green: 0.690, blue: 0.490), tint: Color(red: 0.090, green: 0.067, blue: 0.051), ink: Color(red: 0.953, green: 0.922, blue: 0.890), muted: Color(red: 0.816, green: 0.733, blue: 0.659))
                : AtlasPalette(accent: Color(red: 0.639, green: 0.357, blue: 0.122), tint: Color(red: 0.969, green: 0.922, blue: 0.867), ink: Color(red: 0.157, green: 0.094, blue: 0.055), muted: Color(red: 0.451, green: 0.341, blue: 0.267))
        default:
            return fallback
        }
    }
}

enum ShapeNoteKind: String, CaseIterable, Identifiable {
    case fa
    case sol
    case la
    case mi

    var id: String { rawValue }

    var label: String { rawValue.uppercased() }

    var color: Color {
        switch self {
        case .fa: AtlasTheme.fallback.accent
        case .sol: Color(red: 0.298, green: 0.757, blue: 0.737)
        case .la: Color(red: 0.820, green: 0.565, blue: 0.357)
        case .mi: Color(red: 0.620, green: 0.357, blue: 0.318)
        }
    }

    var description: String {
        switch self {
        case .fa: "triangle"
        case .sol: "oval"
        case .la: "rectangle"
        case .mi: "diamond"
        }
    }
}

struct ShapeNoteShape: Shape {
    let kind: ShapeNoteKind

    func path(in rect: CGRect) -> Path {
        switch kind {
        case .fa:
            var path = Path()
            path.move(to: CGPoint(x: rect.midX, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
            path.closeSubpath()
            return path
        case .sol:
            return Path(ellipseIn: rect)
        case .la:
            return Path(rect)
        case .mi:
            var path = Path()
            path.move(to: CGPoint(x: rect.midX, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
            path.addLine(to: CGPoint(x: rect.midX, y: rect.maxY))
            path.addLine(to: CGPoint(x: rect.minX, y: rect.midY))
            path.closeSubpath()
            return path
        }
    }
}

struct ShapeNoteSymbol: View {
    let kind: ShapeNoteKind
    var size: CGFloat = 14

    var body: some View {
        ShapeNoteShape(kind: kind)
            .fill(kind.color)
            .overlay {
                ShapeNoteShape(kind: kind)
                    .stroke(AtlasTheme.fallback.ink.opacity(0.38), lineWidth: 0.8)
            }
            .frame(width: size, height: size)
            .accessibilityLabel("\(kind.label), \(kind.description)")
    }
}
