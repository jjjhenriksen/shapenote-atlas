import SwiftUI

struct AtlasContentView: View {
    @ObservedObject var model: AtlasAppModel

    var body: some View {
        Group {
            if let errorMessage = model.errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.title)
                        .foregroundStyle(model.palette.accent)
                    Text("The Shape-Note Atlas")
                        .font(.title2.weight(.semibold))
                    Text(errorMessage)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                    Button("Try Again") {
                        model.retry()
                    }
                    .keyboardShortcut(.defaultAction)
                }
                .padding(40)
            } else if let url = model.url {
                AtlasChromeView(
                    url: url,
                    onFailure: { message in
                        model.pageLoadFailed(message)
                    },
                    onThemeChange: { bookId, mode in
                        model.updateTheme(bookId: bookId, mode: mode)
                    },
                    palette: model.palette
                )
            } else {
                ProgressView("Opening the atlas…")
                    .controlSize(.regular)
            }
        }
        .task { model.start() }
        .background(WindowBehaviorBridge().frame(width: 1, height: 1))
    }
}
