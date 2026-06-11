import SwiftUI


struct ScanlineOverlay: View {
    var body: some View {
        Canvas { context, size in
            for y in stride(from: 0, to: size.height, by: 3) {
                let rect = CGRect(x: 0, y: y, width: size.width, height: 1)
                context.fill(Path(rect), with: .color(.black.opacity(0.04)))
            }
        }
        .allowsHitTesting(false)
    }
}


struct VignetteOverlay: View {
    var intensity: Double = 0.6


    var body: some View {
        RadialGradient(
            colors: [.clear, .black.opacity(intensity)],
            center: .center,
            startRadius: 150,
            endRadius: 550
        )
        .ignoresSafeArea()
        .allowsHitTesting(false)
    }
}


struct BroadcastBackground: View {
    var body: some View {
        ZStack {
            BroadcastTheme.deepBlack.ignoresSafeArea()
            BroadcastTheme.stageLighting.ignoresSafeArea()
            BroadcastTheme.redSpotlight.ignoresSafeArea()
            BroadcastTheme.amberSpotlight.ignoresSafeArea()
        }
    }
}