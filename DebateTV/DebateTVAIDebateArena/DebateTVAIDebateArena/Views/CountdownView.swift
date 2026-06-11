import SwiftUI

struct CountdownView: View {
    @Bindable var viewModel: DebateViewModel
    @State private var scale: Double = 0.5
    @State private var opacity: Double = 0
    @State private var ringScale: Double = 0
    @State private var chromaOffset: Double = 0
    
    var body: some View {
        ZStack {
            backgroundContent
            mainContent
            ScanlineOverlay()
                .ignoresSafeArea()
                .allowsHitTesting(false)
        }
        .onChange(of: viewModel.countdownValue) { oldValue, newValue in
            animateCountdownChange(newValue)
        }
        .onAppear {
            animateOnAppear()
        }
    }
    
    @ViewBuilder
    private var backgroundContent: some View {
        AnimatedMeshBackground()
        VignetteOverlay(intensity: 0.9)
        
        // Dramatic stage lights
        ZStack {
                StageLight(color: BroadcastTheme.broadcastRed, angle: .degrees(-45), intensity: 0.8)
                    .opacity(viewModel.countdownValue == 1 ? 1 : 0.3)
                
                StageLight(color: BroadcastTheme.stageAmber, angle: .degrees(45), intensity: 0.8)
                    .opacity(viewModel.countdownValue == 2 ? 1 : 0.3)
                
                StageLight(color: BroadcastTheme.neonCyan, angle: .degrees(0), intensity: 0.8)
                    .opacity(viewModel.countdownValue == 3 ? 1 : 0.3)
            }
            .animation(.easeInOut(duration: 0.3), value: viewModel.countdownValue)
        
        // TV static noise for dramatic effect
        if viewModel.countdownValue == 1 {
            TVStaticNoise()
                .opacity(0.05)
        }
    }
    
    @ViewBuilder
    private var mainContent: some View {
        VStack {
                // Broadcast header
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(BroadcastTheme.broadcastRed)
                            .frame(width: 6, height: 6)
                            .scaleEffect(viewModel.countdownValue == 1 ? 1.5 : 1.0)
                            .animation(.spring(response: 0.3), value: viewModel.countdownValue)
                        
                        Text("GOING LIVE")
                            .font(.system(size: 10, weight: .black, design: .monospaced))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                            .tracking(2)
                    }
                    
                    Spacer()
                    
                    Text("DEBATE ARENA")
                        .font(.system(size: 10, weight: .black, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.4))
                        .tracking(3)
                }
                .padding(.horizontal, 24)
                .padding(.top, 60)
                
                Spacer()
                
                // Countdown display
                ZStack {
                    // Animated rings
                    ForEach(0..<3, id: \.self) { ring in
                        Circle()
                            .stroke(
                                LinearGradient(
                                    colors: [
                                        countdownColor.opacity(0.3),
                                        countdownColor.opacity(0.05)
                                    ],
                                    startPoint: .top,
                                    endPoint: .bottom
                                ),
                                lineWidth: 2
                            )
                            .frame(width: CGFloat(200 + ring * 50), height: CGFloat(200 + ring * 50))
                            .scaleEffect(ringScale)
                            .opacity(1.0 - (ringScale * 0.3))
                            .animation(
                                .easeOut(duration: 1.0)
                                .delay(Double(ring) * 0.1),
                                value: ringScale
                            )
                    }
                    
                    // Main countdown number with chromatic effect overlay
                    ZStack {
                        ChromaticAberrationEffect(offset: chromaOffset)
                        
                        Text("\(viewModel.countdownValue)")
                            .font(.system(size: 180, weight: .black, design: .monospaced))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [countdownColor, countdownColor.opacity(0.8)],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                            .scaleEffect(scale)
                            .opacity(opacity)
                    }
                    
                    // Additional glow effect
                    Text("\(viewModel.countdownValue)")
                        .font(.system(size: 180, weight: .black, design: .monospaced))
                        .foregroundStyle(countdownColor)
                        .blur(radius: 20)
                        .opacity(0.5)
                        .scaleEffect(scale * 1.1)
                }
                
                Spacer()
                
                // Status messages
                VStack(spacing: 16) {
                    Text(countdownMessage)
                        .font(.system(size: 14, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.8))
                        .tracking(2)
                        .transition(.scale.combined(with: .opacity))
                    
                    // Participants ready indicator
                    HStack(spacing: 32) {
                        ParticipantStatus(
                            name: "YOU",
                            color: BroadcastTheme.neonCyan,
                            isReady: true
                        )
                        
                        ParticipantStatus(
                            name: viewModel.opponentName.uppercased(),
                            color: BroadcastTheme.stageAmber,
                            isReady: viewModel.countdownValue < 3
                        )
                    }
                    
                    // Connection quality
                    HStack(spacing: 12) {
                        Image(systemName: "wifi")
                            .font(.system(size: 12))
                            .foregroundStyle(BroadcastTheme.success)
                        
                        Text("CONNECTION: EXCELLENT")
                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                            .foregroundStyle(.white.opacity(0.4))
                            .tracking(1)
                        
                        HStack(spacing: 2) {
                            ForEach(0..<5) { bar in
                                RoundedRectangle(cornerRadius: 1)
                                    .fill(BroadcastTheme.success)
                                    .frame(width: 2, height: CGFloat(4 + bar * 2))
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)
                    .background(.white.opacity(0.05))
                    .clipShape(Capsule())
                }
                .padding(.bottom, 80)
        }
    }
    
    private func animateCountdownChange(_ newValue: Int) {
        // Reset and animate for each countdown number
        scale = 0.5
        opacity = 0
        ringScale = 0
        chromaOffset = 5
        
        withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
            scale = 1.0
            opacity = 1.0
        }
        
        withAnimation(.easeOut(duration: 0.8)) {
            ringScale = 1.5
        }
        
        withAnimation(.easeOut(duration: 0.5)) {
            chromaOffset = 0
        }
        
        // Pulse effect on 1
        if newValue == 1 {
            withAnimation(.easeInOut(duration: 0.3).repeatCount(3, autoreverses: true)) {
                scale = 1.1
            }
        }
    }
    
    private func animateOnAppear() {
        scale = 0.5
        opacity = 0
        
        withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
            scale = 1.0
            opacity = 1.0
        }
        
        withAnimation(.easeOut(duration: 0.8)) {
            ringScale = 1.5
        }
    }
    
    private var countdownColor: Color {
        switch viewModel.countdownValue {
        case 3: return BroadcastTheme.neonCyan
        case 2: return BroadcastTheme.stageAmber
        case 1: return BroadcastTheme.broadcastRed
        default: return .white
        }
    }
    
    private var countdownMessage: String {
        switch viewModel.countdownValue {
        case 3: return "PREPARE YOURSELF"
        case 2: return "CAMERAS ROLLING"
        case 1: return "GOING LIVE!"
        default: return ""
        }
    }
}

struct ParticipantStatus: View {
    let name: String
    let color: Color
    let isReady: Bool
    
    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 6) {
                Circle()
                    .fill(isReady ? BroadcastTheme.success : .white.opacity(0.3))
                    .frame(width: 6, height: 6)
                
                Text(name)
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundStyle(color)
                    .tracking(1)
            }
            
            Text(isReady ? "READY" : "WAITING")
                .font(.system(size: 8, weight: .medium, design: .monospaced))
                .foregroundStyle(isReady ? BroadcastTheme.success : .white.opacity(0.3))
        }
    }
}

#Preview {
    CountdownView(viewModel: {
        let vm = DebateViewModel(
            debateService: DebateService(),
            judgeService: AIJudgeService()
        )
        vm.countdownValue = 3
        vm.opponentName = "DebatePro"
        return vm
    }())
}