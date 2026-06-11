import SwiftUI

struct MatchmakingView: View {
    @Bindable var viewModel: DebateViewModel
    @State private var pulseScale: Bool = false
    @State private var radarRotation: Double = 0
    @State private var connectionEstablished: Bool = false
    @State private var signalStrength: Double = 0
    
    var body: some View {
        ZStack {
            // Broadcast TV production background
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.7)
            
            VStack(spacing: 0) {
                // Broadcast header
                HStack(spacing: 8) {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(BroadcastTheme.broadcastRed)
                            .frame(width: 6, height: 6)
                        Text("LIVE")
                            .font(.system(size: 10, weight: .black, design: .monospaced))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                            .tracking(2)
                    }
                    
                    Spacer()
                    
                    Text("MATCHMAKING")
                        .font(.system(size: 10, weight: .black, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.4))
                        .tracking(3)
                }
                .padding(.horizontal, 24)
                .padding(.top, 60)
                
                Spacer()
                
                // Matchmaking visualization
                ZStack {
                    // Radar effect
                    ForEach(0..<3) { ring in
                        Circle()
                            .stroke(
                                LinearGradient(
                                    colors: [
                                        BroadcastTheme.neonCyan.opacity(0.3),
                                        BroadcastTheme.neonCyan.opacity(0.05)
                                    ],
                                    startPoint: .top,
                                    endPoint: .bottom
                                ),
                                lineWidth: 1
                            )
                            .frame(width: CGFloat(150 + ring * 60), height: CGFloat(150 + ring * 60))
                            .scaleEffect(pulseScale ? 1.1 : 1.0)
                            .opacity(pulseScale ? 0.5 : 0.8)
                            .animation(
                                .easeInOut(duration: 2)
                                .repeatForever(autoreverses: true)
                                .delay(Double(ring) * 0.3),
                                value: pulseScale
                            )
                    }
                    
                    // Scanning line
                    RadarScanLine()
                        .frame(width: 270, height: 270)
                        .rotationEffect(.degrees(radarRotation))
                        .animation(
                            .linear(duration: 3)
                            .repeatForever(autoreverses: false),
                            value: radarRotation
                        )
                    
                    // Center profiles
                    HStack(spacing: 60) {
                        // User profile
                        VStack(spacing: 8) {
                            ZStack {
                                Circle()
                                    .fill(BroadcastTheme.neonCyan.opacity(0.1))
                                    .frame(width: 80, height: 80)
                                
                                Circle()
                                    .stroke(BroadcastTheme.neonCyan.opacity(0.5), lineWidth: 2)
                                    .frame(width: 80, height: 80)
                                
                                Image(systemName: "person.fill")
                                    .font(.system(size: 32))
                                    .foregroundStyle(BroadcastTheme.neonCyan)
                            }
                            
                            Text("YOU")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundStyle(BroadcastTheme.neonCyan)
                                .tracking(1)
                        }
                        
                        // Connection indicator
                        HStack(spacing: 4) {
                            ForEach(0..<3) { dot in
                                Circle()
                                    .fill(connectionEstablished ? BroadcastTheme.success : .white.opacity(0.3))
                                    .frame(width: 4, height: 4)
                                    .scaleEffect(connectionEstablished ? 1.0 : 0.6)
                                    .animation(
                                        .spring(response: 0.3, dampingFraction: 0.6)
                                        .delay(Double(dot) * 0.1),
                                        value: connectionEstablished
                                    )
                            }
                        }
                        
                        // Opponent profile
                        VStack(spacing: 8) {
                            ZStack {
                                Circle()
                                    .fill(BroadcastTheme.stageAmber.opacity(0.1))
                                    .frame(width: 80, height: 80)
                                
                                Circle()
                                    .stroke(BroadcastTheme.stageAmber.opacity(connectionEstablished ? 0.8 : 0.3), lineWidth: 2)
                                    .frame(width: 80, height: 80)
                                
                                if connectionEstablished {
                                    Image(systemName: "person.fill")
                                        .font(.system(size: 32))
                                        .foregroundStyle(BroadcastTheme.stageAmber)
                                        .transition(.scale.combined(with: .opacity))
                                } else {
                                    Image(systemName: "questionmark")
                                        .font(.system(size: 32))
                                        .foregroundStyle(.white.opacity(0.3))
                                }
                            }
                            
                            Text(connectionEstablished ? viewModel.opponentName.uppercased() : "SEARCHING")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundStyle(connectionEstablished ? BroadcastTheme.stageAmber : .white.opacity(0.4))
                                .tracking(1)
                                .animation(.none, value: connectionEstablished)
                        }
                        .opacity(viewModel.matchmakingProgress > 0.3 ? 1 : 0.3)
                    }
                }
                .frame(height: 350)
                
                Spacer()
                
                // Progress section
                VStack(spacing: 20) {
                    // Progress bar
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("FINDING OPPONENT")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .foregroundStyle(.white.opacity(0.5))
                                .tracking(1)
                            
                            Spacer()
                            
                            Text("\(Int(viewModel.matchmakingProgress * 100))%")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .foregroundStyle(BroadcastTheme.neonCyan)
                        }
                        
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(.white.opacity(0.1))
                                
                                RoundedRectangle(cornerRadius: 2)
                                    .fill(
                                        LinearGradient(
                                            colors: [
                                                BroadcastTheme.neonCyan,
                                                BroadcastTheme.neonCyan.opacity(0.6)
                                            ],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        )
                                    )
                                    .frame(width: geo.size.width * viewModel.matchmakingProgress)
                            }
                        }
                        .frame(height: 4)
                    }
                    
                    // Signal strength
                    HStack(spacing: 16) {
                        SignalStrengthIndicator(strength: signalStrength)
                        
                        Text("SIGNAL: \(signalStrength > 0.7 ? "EXCELLENT" : signalStrength > 0.4 ? "GOOD" : "SEARCHING")")
                            .font(.system(size: 8, weight: .bold, design: .monospaced))
                            .foregroundStyle(.white.opacity(0.4))
                            .tracking(1)
                    }
                    
                    // Status messages
                    VStack(spacing: 6) {
                        if viewModel.matchmakingProgress < 0.3 {
                            StatusMessage(text: "Initializing debate arena...", icon: "antenna.radiowaves.left.and.right")
                        } else if viewModel.matchmakingProgress < 0.6 {
                            StatusMessage(text: "Scanning for opponents...", icon: "magnifyingglass")
                        } else if viewModel.matchmakingProgress < 0.9 {
                            StatusMessage(text: "Establishing connection...", icon: "link")
                        } else {
                            StatusMessage(text: "Match found!", icon: "checkmark.circle.fill")
                                .foregroundStyle(BroadcastTheme.success)
                        }
                    }
                    .frame(height: 30)
                    
                    // Cancel button
                    Button {
                        viewModel.reset()
                    } label: {
                        Text("CANCEL")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundStyle(.white.opacity(0.5))
                            .tracking(2)
                            .padding(.horizontal, 24)
                            .padding(.vertical, 10)
                            .background(.white.opacity(0.05))
                            .clipShape(Capsule())
                            .overlay(
                                Capsule()
                                    .stroke(.white.opacity(0.1), lineWidth: 1)
                            )
                    }
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 60)
            }
            
            // Scanlines overlay
            ScanlineOverlay()
                .ignoresSafeArea()
                .allowsHitTesting(false)
        }
        .onAppear {
            pulseScale = true
            radarRotation = 360
            
            // Simulate connection establishment
            withAnimation(.easeInOut(duration: 2).delay(1.5)) {
                connectionEstablished = viewModel.matchmakingProgress > 0.8
                signalStrength = min(viewModel.matchmakingProgress * 1.2, 1.0)
            }
        }
        .onChange(of: viewModel.matchmakingProgress) { _, newValue in
            withAnimation(.easeInOut(duration: 0.5)) {
                connectionEstablished = newValue > 0.8
                signalStrength = min(newValue * 1.2, 1.0)
            }
        }
    }
}

struct RadarScanLine: View {
    var body: some View {
        GeometryReader { geo in
            Path { path in
                path.move(to: CGPoint(x: geo.size.width / 2, y: geo.size.height / 2))
                path.addLine(to: CGPoint(x: geo.size.width / 2, y: 0))
            }
            .stroke(
                LinearGradient(
                    colors: [
                        BroadcastTheme.neonCyan.opacity(0.8),
                        BroadcastTheme.neonCyan.opacity(0.0)
                    ],
                    startPoint: .center,
                    endPoint: .top
                ),
                lineWidth: 2
            )
            .blur(radius: 1)
        }
    }
}

struct SignalStrengthIndicator: View {
    let strength: Double
    
    var body: some View {
        HStack(spacing: 3) {
            ForEach(0..<4) { bar in
                RoundedRectangle(cornerRadius: 1)
                    .fill(
                        strength > Double(bar) / 4.0 ?
                        BroadcastTheme.success :
                        .white.opacity(0.2)
                    )
                    .frame(width: 3, height: CGFloat(6 + bar * 3))
            }
        }
    }
}

struct StatusMessage: View {
    let text: String
    let icon: String
    
    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 12))
            
            Text(text)
                .font(.system(size: 11, weight: .medium))
        }
        .foregroundStyle(.white.opacity(0.6))
    }
}

#Preview {
    MatchmakingView(viewModel: DebateViewModel(
        debateService: DebateService(),
        judgeService: AIJudgeService()
    ))
}