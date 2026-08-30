import SwiftUI

struct AtlasChromeView: View {
    let url: URL
    let onFailure: (String) -> Void
    let onThemeChange: (String, String) -> Void
    let palette: AtlasPalette

    var body: some View {
        ZStack(alignment: .top) {
            palette.tint.ignoresSafeArea()

            VStack(spacing: 0) {
                AtlasWebView(url: url, onFailure: onFailure, onThemeChange: onThemeChange)
                    .background(palette.tint)
                    .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .stroke(palette.accent.opacity(0.24), lineWidth: 1)
                    }
            }
            .padding(.top, 0)
            .padding(.horizontal, 24)
            .padding(.bottom, 12)

            if #available(macOS 15.0, *) {
                Color.clear
                    .frame(height: 12)
                    .frame(maxWidth: .infinity, alignment: .top)
                    .contentShape(Rectangle())
                    .gesture(WindowDragGesture())
                    .allowsWindowActivationEvents(true)
            }
        }
        .frame(minWidth: 1100, minHeight: 720)
    }
}
