import SwiftUI

struct ShapeLegend: View {
    @State private var activeShape: ShapeNoteKind = .fa

    var body: some View {
        legendContent
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                guard !Task.isCancelled else { return }
                if let next = ShapeNoteKind.allCases[(ShapeNoteKind.allCases.firstIndex(of: activeShape)! + 1) % ShapeNoteKind.allCases.count] as ShapeNoteKind? {
                    activeShape = next
                }
            }
        }
    }

    private var legendContent: some View {
        HStack(spacing: 9) {
            Text("SHAPES")
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .tracking(1.3)
                .foregroundStyle(.secondary)

            ForEach(ShapeNoteKind.allCases) { kind in
                HStack(spacing: 5) {
                    ShapeNoteSymbol(kind: kind, size: 12)
                    Text(kind.label)
                        .font(.system(size: 10, weight: .semibold, design: .rounded))
                        .foregroundStyle(kind == activeShape ? .primary : .secondary)
                }
                .padding(.horizontal, 5)
                .padding(.vertical, 4)
                .background(kind == activeShape ? kind.color.opacity(0.16) : .clear, in: Capsule())
                .overlay {
                    if kind == activeShape {
                        Capsule().stroke(kind.color.opacity(0.52), lineWidth: 0.8)
                    }
                }
                .animation(.easeInOut(duration: 0.3), value: activeShape)
                .accessibilityElement(children: .combine)
                .accessibilityLabel("\(kind.label), \(kind.description)")
            }
        }
    }
}
