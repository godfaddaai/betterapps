import SwiftUI


struct MatchmakingView: View {
    let progress: Double
    let opponentName: String
    let onCancel: () -> Void
    @State private var ringRotation: Double = 0
    @State private var pulseScale: Double = 1.0
    @State private var glowIntensity: Double = 0.3
    @State private var scanPhase: Double = 0
    @State private var matchFound: Bool = false


    var body: some View {
        ZStack {
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.7)

            VStack(spacing: 20) {
                Spacer()
                
                ZStack {
                    Circle()
                        .stroke(BroadcastTheme.broadcastRed.opacity(0.2), lineWidth: 4)
                        .frame(width: 160, height: 160)
                        
                    Circle()
                        .trim(from: 0, to: progress)
                        .stroke(BroadcastTheme.broadcastRed, lineWidth: 4)
                        .frame(width: 160, height: 160)
                        .rotationEffect(.degrees(-90))
                        
                    Text("Finding Match...")
                        .foregroundColor(.white)
                }
                
                Spacer()
            }
        }
    }
}