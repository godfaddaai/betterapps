import SwiftUI

struct JudgingView: View {
    @State private var analysisProgress: Double = 0
    @State private var criteriaRevealed: [Bool] = [false, false, false, false]
    @State private var aiThinking: Bool = false
    @State private var processingDots: Int = 0
    
    private let analysisSteps = [
        "Analyzing argument structure...",
        "Evaluating evidence quality...",
        "Assessing rhetorical effectiveness...",
        "Detecting logical fallacies...",
        "Calculating final scores..."
    ]
    
    @State private var currentStep: Int = 0
    
    var body: some View {
        ZStack {
            // Sophisticated broadcast background
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.7)
            
            // Animated grid pattern
            GeometryReader { geo in
                ForEach(0..<20) { row in
                    ForEach(0..<10) { col in
                        RoundedRectangle(cornerRadius: 1)
                            .fill(BroadcastTheme.neonCyan.opacity(0.03))
                            .frame(width: 2, height: 20)
                            .position(
                                x: CGFloat(col) * (geo.size.width / 10) + 20,
                                y: CGFloat(row) * (geo.size.height / 20) + 10
                            )
                            .opacity(aiThinking ? Double.random(in: 0.1...0.3) : 0.1)
                            .animation(
                                .easeInOut(duration: Double.random(in: 0.5...1.5))
                                .repeatForever(),
                                value: aiThinking
                            )
                    }
                }
            }
            .opacity(0.3)
            
            VStack(spacing: 0) {
                // Header
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(BroadcastTheme.broadcastRed)
                            .frame(width: 6, height: 6)
                            .scaleEffect(aiThinking ? 1.3 : 1.0)
                            .animation(
                                .easeInOut(duration: 0.5)
                                .repeatForever(autoreverses: true),
                                value: aiThinking
                            )
                        
                        Text("AI JUDGE")
                            .font(.system(size: 10, weight: .black, design: .monospaced))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                            .tracking(2)
                    }
                    
                    Spacer()
                    
                    Text("ANALYZING DEBATE")
                        .font(.system(size: 10, weight: .black, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.4))
                        .tracking(3)
                }
                .padding(.horizontal, 24)
                .padding(.top, 60)
                
                Spacer()
                
                // Main content
                VStack(spacing: 32) {
                    // AI Avatar
                    ZStack {
                        // Outer ring
                        Circle()
                            .stroke(
                                LinearGradient(
                                    colors: [
                                        BroadcastTheme.neonCyan.opacity(0.3),
                                        BroadcastTheme.stageAmber.opacity(0.3)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 2
                            )
                            .frame(width: 120, height: 120)
                            .rotationEffect(.degrees(aiThinking ? 360 : 0))
                            .animation(
                                .linear(duration: 4)
                                .repeatForever(autoreverses: false),
                                value: aiThinking
                            )
                        
                        // Inner glow
                        Circle()
                            .fill(
                                RadialGradient(
                                    colors: [
                                        BroadcastTheme.neonCyan.opacity(0.3),
                                        .clear
                                    ],
                                    center: .center,
                                    startRadius: 0,
                                    endRadius: 50
                                )
                            )
                            .frame(width: 100, height: 100)
                            .blur(radius: 10)
                            .scaleEffect(aiThinking ? 1.2 : 1.0)
                            .animation(
                                .easeInOut(duration: 1.5)
                                .repeatForever(autoreverses: true),
                                value: aiThinking
                            )
                        
                        // AI Icon
                        Image(systemName: "brain")
                            .font(.system(size: 40, weight: .medium))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [BroadcastTheme.neonCyan, BroadcastTheme.stageAmber],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                    }
                    
                    // Processing status
                    VStack(spacing: 16) {
                        HStack(spacing: 4) {
                            Text("PROCESSING")
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundStyle(.white.opacity(0.8))
                                .tracking(2)
                            
                            ForEach(0..<3) { dot in
                                Text(".")
                                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                                    .foregroundStyle(.white.opacity(0.8))
                                    .opacity(dot < processingDots ? 1 : 0.2)
                            }
                        }
                        
                        Text(analysisSteps[min(currentStep, analysisSteps.count - 1)])
                            .font(.system(.caption))
                            .foregroundStyle(BroadcastTheme.neonCyan.opacity(0.8))
                            .transition(.opacity)
                    }
                    
                    // Progress bar
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("ANALYSIS PROGRESS")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .foregroundStyle(.white.opacity(0.5))
                                .tracking(1)
                            
                            Spacer()
                            
                            Text("\(Int(analysisProgress * 100))%")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .foregroundStyle(BroadcastTheme.neonCyan)
                                .contentTransition(.numericText())
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
                                                BroadcastTheme.stageAmber
                                            ],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        )
                                    )
                                    .frame(width: geo.size.width * analysisProgress)
                                
                                // Animated shimmer
                                if analysisProgress > 0 && analysisProgress < 1 {
                                    RoundedRectangle(cornerRadius: 2)
                                        .fill(
                                            LinearGradient(
                                                colors: [
                                                    .clear,
                                                    .white.opacity(0.3),
                                                    .clear
                                                ],
                                                startPoint: .leading,
                                                endPoint: .trailing
                                            )
                                        )
                                        .frame(width: 50)
                                        .offset(x: geo.size.width * analysisProgress - 25)
                                }
                            }
                        }
                        .frame(height: 6)
                    }
                    .padding(.horizontal, 40)
                    
                    // Analysis criteria
                    VStack(spacing: 12) {
                        AnalysisCriterionView(
                            icon: "chart.line.uptrend.xyaxis",
                            label: "LOGIC & STRUCTURE",
                            revealed: criteriaRevealed[0]
                        )
                        
                        AnalysisCriterionView(
                            icon: "doc.text.magnifyingglass",
                            label: "EVIDENCE QUALITY",
                            revealed: criteriaRevealed[1]
                        )
                        
                        AnalysisCriterionView(
                            icon: "waveform",
                            label: "RHETORICAL POWER",
                            revealed: criteriaRevealed[2]
                        )
                        
                        AnalysisCriterionView(
                            icon: "exclamationmark.triangle",
                            label: "FALLACY DETECTION",
                            revealed: criteriaRevealed[3]
                        )
                    }
                    .padding(.horizontal, 40)
                }
                
                Spacer()
                
                // Footer message
                VStack(spacing: 8) {
                    Text("PLEASE WAIT")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.4))
                        .tracking(2)
                    
                    Text("Our AI judge is carefully evaluating all arguments")
                        .font(.system(.caption2))
                        .foregroundStyle(.white.opacity(0.3))
                }
                .padding(.bottom, 60)
            }
            
            // Scanlines
            ScanlineOverlay()
                .ignoresSafeArea()
                .allowsHitTesting(false)
        }
        .onAppear {
            aiThinking = true
            startAnalysis()
            animateProcessingDots()
        }
    }
    
    private func startAnalysis() {
        // Animate progress
        withAnimation(.easeInOut(duration: 3)) {
            analysisProgress = 1.0
        }
        
        // Reveal criteria one by one
        for i in 0..<4 {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.6 + 0.5) {
                withAnimation(.spring(response: 0.5, dampingFraction: 0.7)) {
                    criteriaRevealed[i] = true
                }
            }
        }
        
        // Update analysis steps
        Timer.scheduledTimer(withTimeInterval: 0.8, repeats: true) { timer in
            if currentStep < analysisSteps.count - 1 {
                withAnimation {
                    currentStep += 1
                }
            } else {
                timer.invalidate()
            }
        }
    }
    
    private func animateProcessingDots() {
        Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
            processingDots = (processingDots + 1) % 4
        }
    }
}

struct AnalysisCriterionView: View {
    let icon: String
    let label: String
    let revealed: Bool
    
    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(BroadcastTheme.neonCyan.opacity(0.1))
                    .frame(width: 32, height: 32)
                
                Image(systemName: revealed ? "checkmark.circle.fill" : icon)
                    .font(.system(size: 14))
                    .foregroundStyle(
                        revealed ? BroadcastTheme.success : .white.opacity(0.3)
                    )
            }
            
            Text(label)
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .foregroundStyle(revealed ? .white : .white.opacity(0.3))
                .tracking(1)
            
            Spacer()
            
            if revealed {
                Text("COMPLETE")
                    .font(.system(size: 8, weight: .bold, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.success)
                    .tracking(1)
                    .transition(.scale.combined(with: .opacity))
            } else {
                ProgressView()
                    .scaleEffect(0.6)
                    .tint(.white.opacity(0.3))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(revealed ? .white.opacity(0.03) : .clear)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(revealed ? BroadcastTheme.success.opacity(0.2) : .white.opacity(0.1), lineWidth: 0.5)
        )
    }
}

#Preview {
    JudgingView()
}