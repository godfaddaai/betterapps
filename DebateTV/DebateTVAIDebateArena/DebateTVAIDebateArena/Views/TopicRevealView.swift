import SwiftUI

struct TopicRevealView: View {
    @Bindable var viewModel: DebateViewModel
    @State private var revealed: Bool = false
    @State private var positionRevealed: Bool = false
    @State private var glowAnimation: Bool = false
    
    var body: some View {
        ZStack {
            // Dramatic broadcast background
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.8)
            
            // Stage lights effect
            ZStack {
                StageLight(color: BroadcastTheme.broadcastRed, angle: .degrees(-30), intensity: 0.7)
                StageLight(color: BroadcastTheme.stageAmber, angle: .degrees(30), intensity: 0.7)
            }
            .opacity(revealed ? 1 : 0)
            .animation(.easeInOut(duration: 1.5), value: revealed)
            
            VStack(spacing: 0) {
                // Broadcast header
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(BroadcastTheme.broadcastRed)
                            .frame(width: 6, height: 6)
                        Text("LIVE DEBATE")
                            .font(.system(size: 10, weight: .black, design: .monospaced))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                            .tracking(2)
                    }
                    
                    Spacer()
                    
                    Text("TOPIC REVEAL")
                        .font(.system(size: 10, weight: .black, design: .monospaced))
                        .foregroundStyle(BroadcastTheme.stageAmber.opacity(0.8))
                        .tracking(3)
                }
                .padding(.horizontal, 24)
                .padding(.top, 60)
                
                Spacer()
                
                // Main content
                VStack(spacing: 40) {
                    // Topic announcement
                    VStack(spacing: 16) {
                        Text("TONIGHT'S DEBATE")
                            .font(.system(size: 14, weight: .black, design: .monospaced))
                            .foregroundStyle(.white.opacity(0.5))
                            .tracking(3)
                            .opacity(revealed ? 1 : 0)
                            .animation(.easeOut(duration: 0.5), value: revealed)
                        
                        // Topic card
                        VStack(spacing: 20) {
                            if let topic = viewModel.currentTopic {
                                VStack(spacing: 12) {
                                    // Category badge
                                    HStack(spacing: 8) {
                                        Image(systemName: topic.category.icon)
                                            .font(.system(size: 14))
                                        Text(topic.category.rawValue.uppercased())
                                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                                            .tracking(1)
                                    }
                                    .foregroundStyle(topic.category.color)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 6)
                                    .background(topic.category.color.opacity(0.15))
                                    .clipShape(Capsule())
                                    .overlay(
                                        Capsule()
                                            .stroke(topic.category.color.opacity(0.3), lineWidth: 1)
                                    )
                                    
                                    // Topic title
                                    Text(topic.title)
                                        .font(.system(.title, weight: .bold))
                                        .foregroundStyle(.white)
                                        .multilineTextAlignment(.center)
                                        .padding(.horizontal, 32)
                                    
                                    // Topic description
                                    Text(topic.description)
                                        .font(.system(.subheadline))
                                        .foregroundStyle(.white.opacity(0.6))
                                        .multilineTextAlignment(.center)
                                        .padding(.horizontal, 40)
                                    
                                    // Difficulty indicator
                                    HStack(spacing: 4) {
                                        ForEach(0..<5) { star in
                                            Image(systemName: star < topic.difficulty ? "star.fill" : "star")
                                                .font(.system(size: 12))
                                                .foregroundStyle(
                                                    star < topic.difficulty ?
                                                    BroadcastTheme.warning :
                                                    .white.opacity(0.2)
                                                )
                                        }
                                        
                                        Text("DIFFICULTY")
                                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                                            .foregroundStyle(.white.opacity(0.4))
                                            .tracking(1)
                                            .padding(.leading, 8)
                                    }
                                }
                            }
                        }
                        .padding(32)
                        .background(
                            ZStack {
                                RoundedRectangle(cornerRadius: 20)
                                    .fill(.black.opacity(0.3))
                                
                                RoundedRectangle(cornerRadius: 20)
                                    .stroke(
                                        LinearGradient(
                                            colors: [
                                                BroadcastTheme.neonCyan.opacity(0.5),
                                                BroadcastTheme.stageAmber.opacity(0.5)
                                            ],
                                            startPoint: .topLeading,
                                            endPoint: .bottomTrailing
                                        ),
                                        lineWidth: 1
                                    )
                                
                                if glowAnimation {
                                    RoundedRectangle(cornerRadius: 20)
                                        .stroke(BroadcastTheme.neonCyan.opacity(0.3), lineWidth: 3)
                                        .blur(radius: 10)
                                }
                            }
                        )
                        .scaleEffect(revealed ? 1 : 0.8)
                        .opacity(revealed ? 1 : 0)
                    }
                    
                    // Position assignment
                    if positionRevealed {
                        VStack(spacing: 16) {
                            Text("YOUR POSITION")
                                .font(.system(size: 11, weight: .black, design: .monospaced))
                                .foregroundStyle(.white.opacity(0.5))
                                .tracking(2)
                            
                            HStack(spacing: 20) {
                                // User position
                                PositionCard(
                                    label: "YOU",
                                    position: Bool.random() ? "FOR" : "AGAINST",
                                    color: BroadcastTheme.neonCyan,
                                    isUser: true
                                )
                                
                                Text("VS")
                                    .font(.system(size: 14, weight: .black, design: .monospaced))
                                    .foregroundStyle(.white.opacity(0.3))
                                
                                // Opponent position
                                PositionCard(
                                    label: viewModel.opponentName.uppercased(),
                                    position: Bool.random() ? "FOR" : "AGAINST",
                                    color: BroadcastTheme.stageAmber,
                                    isUser: false
                                )
                            }
                        }
                        .transition(.scale.combined(with: .opacity))
                    }
                }
                
                Spacer()
                
                // Get ready message
                if positionRevealed {
                    VStack(spacing: 12) {
                        Text("GET READY")
                            .font(.system(size: 16, weight: .black, design: .monospaced))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                            .tracking(3)
                        
                        Text("Debate begins in moments...")
                            .font(.system(.caption))
                            .foregroundStyle(.white.opacity(0.4))
                    }
                    .padding(.bottom, 60)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            
            // Scanlines
            ScanlineOverlay()
                .ignoresSafeArea()
                .allowsHitTesting(false)
        }
        .onAppear {
            withAnimation(.spring(response: 0.8, dampingFraction: 0.7).delay(0.3)) {
                revealed = true
            }
            
            withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                glowAnimation = true
            }
            
            withAnimation(.spring(response: 0.6, dampingFraction: 0.8).delay(1.5)) {
                positionRevealed = true
            }
        }
    }
}

struct PositionCard: View {
    let label: String
    let position: String
    let color: Color
    let isUser: Bool
    
    var body: some View {
        VStack(spacing: 12) {
            Text(label)
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundStyle(color.opacity(0.8))
                .tracking(1)
            
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(color.opacity(0.1))
                    .frame(width: 100, height: 100)
                
                RoundedRectangle(cornerRadius: 12)
                    .stroke(color.opacity(0.5), lineWidth: 2)
                    .frame(width: 100, height: 100)
                
                VStack(spacing: 8) {
                    Image(systemName: position == "FOR" ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(color)
                    
                    Text(position)
                        .font(.system(size: 14, weight: .black, design: .monospaced))
                        .foregroundStyle(color)
                        .tracking(2)
                }
            }
        }
    }
}

#Preview {
    TopicRevealView(viewModel: {
        let vm = DebateViewModel(
            debateService: DebateService(),
            judgeService: AIJudgeService()
        )
        vm.currentTopic = DebateTopic(
            id: "1",
            title: "Should AI replace human decision-making?",
            description: "Exploring the role of AI in critical sectors",
            category: .technology,
            difficulty: 3
        )
        vm.opponentName = "DebateMaster"
        return vm
    }())
}