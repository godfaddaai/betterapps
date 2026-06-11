import SwiftUI

struct VerdictView: View {
    let result: DebateResult
    let onRematch: () -> Void
    let onHome: () -> Void
    @State private var revealed: Bool = false
    @State private var scoreAnimated: Bool = false
    @State private var detailsRevealed: Bool = false
    @State private var buttonsRevealed: Bool = false

    var body: some View {
        ZStack {
            // Broadcast TV production background
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.6)
            
            ScrollView {
                VStack(spacing: 0) {
                    verdictHeader
                    if let fullResult = createMockFullResult() {
                        scorecard(fullResult)
                        breakdownBars(fullResult)
                        analysisSection(fullResult)
                    }
                    actionButtons
                }
                .padding(.bottom, 44)
            }
            .scrollIndicators(.hidden)
            
            ScanlineOverlay()
                .ignoresSafeArea()
                .allowsHitTesting(false)
        }
        .onAppear {
            withAnimation(.spring(response: 0.6, dampingFraction: 0.65).delay(0.3)) {
                revealed = true
            }
            withAnimation(.spring(response: 0.8, dampingFraction: 0.6).delay(0.9)) {
                scoreAnimated = true
            }
            withAnimation(.spring(response: 0.5).delay(1.5)) {
                detailsRevealed = true
            }
            withAnimation(.spring(response: 0.5).delay(1.8)) {
                buttonsRevealed = true
            }
        }
    }
    
    private var verdictHeader: some View {
        VStack(spacing: 16) {
            HStack(spacing: 8) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(BroadcastTheme.broadcastRed)
                        .frame(width: 5, height: 5)
                    Text("DEBATE TV")
                        .font(.system(size: 9, weight: .black, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.3))
                        .tracking(3)
                }
                Spacer()
                Text("FINAL VERDICT")
                    .font(.system(size: 9, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.primary.opacity(0.8))
                    .tracking(2)
            }
            .padding(.horizontal, 20)
            .padding(.top, 24)
            
            VStack(spacing: 14) {
                ZStack {
                    Circle()
                        .fill(outcomeColor.opacity(0.06))
                        .frame(width: 140, height: 140)
                        .blur(radius: 25)
                    
                    Circle()
                        .stroke(outcomeColor.opacity(0.15), lineWidth: 1)
                        .frame(width: 120, height: 120)
                    
                    VStack(spacing: 4) {
                        Image(systemName: outcomeIcon)
                            .font(.system(size: 36))
                            .foregroundStyle(outcomeColor)
                        Text(outcomeTitle)
                            .font(.system(size: 28, weight: .black, design: .monospaced))
                            .foregroundStyle(outcomeColor)
                            .tracking(2)
                    }
                }
                .scaleEffect(revealed ? 1 : 0.5)
                .opacity(revealed ? 1 : 0)
                
                Text(createMockFullResult()?.topic.title ?? "")
                    .font(.system(.subheadline, weight: .medium))
                    .foregroundStyle(.white.opacity(0.4))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
                    .opacity(revealed ? 1 : 0)
            }
        }
    }
    
    private var outcomeColor: Color {
        switch result {
        case .won: return BroadcastTheme.success
        case .lost: return BroadcastTheme.error
        case .draw: return BroadcastTheme.warning
        }
    }
    
    private var outcomeTitle: String {
        switch result {
        case .won: return "VICTORY"
        case .lost: return "DEFEAT"
        case .draw: return "DRAW"
        }
    }
    
    private var outcomeIcon: String {
        switch result {
        case .won: return "trophy.fill"
        case .lost: return "xmark.shield.fill"
        case .draw: return "equal.circle.fill"
        }
    }
    
    private func scorecard(_ fullResult: DebateResultStruct) -> some View {
        HStack(spacing: 0) {
            // Agree-green side: YOU — exactly like the content verdict cards
            VStack(spacing: 6) {
                Text("YOU")
                    .font(.system(size: 9, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.success)
                    .tracking(2)
                Text("\(scoreAnimated ? fullResult.userScore : 0)")
                    .font(.system(size: 52, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.success)
                    .contentTransition(.numericText())
                    .shadow(color: BroadcastTheme.success.opacity(0.4), radius: 12)
            }
            .frame(maxWidth: .infinity)

            VStack(spacing: 6) {
                Text("VS")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.textSecondary.opacity(0.7))
                Rectangle()
                    .fill(.white.opacity(0.06))
                    .frame(width: 1, height: 30)
            }

            // Wrong-red side: THEM
            VStack(spacing: 6) {
                Text(fullResult.opponentName.prefix(8).uppercased())
                    .font(.system(size: 9, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.error)
                    .tracking(1)
                    .lineLimit(1)
                Text("\(scoreAnimated ? fullResult.opponentScore : 0)")
                    .font(.system(size: 52, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.error.opacity(0.85))
                    .contentTransition(.numericText())
                    .shadow(color: BroadcastTheme.error.opacity(0.3), radius: 12)
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.vertical, 24)
        .padding(.horizontal, 16)
        .background(
            HStack(spacing: 0) {
                BroadcastTheme.success.opacity(0.05)
                BroadcastTheme.error.opacity(0.05)
            }
        )
        .background(BroadcastTheme.surface.opacity(0.45))
        .clipShape(.rect(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(BroadcastTheme.primary.opacity(0.14), lineWidth: 0.5)
        )
        .overlay(
            Rectangle().fill(outcomeColor.opacity(0.25)).frame(height: 2),
            alignment: .top
        )
        .padding(.horizontal, 16)
        .padding(.top, 20)
        .opacity(scoreAnimated ? 1 : 0.2)
    }
    
    private func breakdownBars(_ fullResult: DebateResultStruct) -> some View {
        VStack(spacing: 10) {
            breakdownBar(label: "LOGIC", userScore: Double(fullResult.userScore) / 100 * 0.9, oppScore: Double(fullResult.opponentScore) / 100 * 0.85)
            breakdownBar(label: "EVIDENCE", userScore: Double(fullResult.userScore) / 100 * 0.85, oppScore: Double(fullResult.opponentScore) / 100 * 0.9)
            breakdownBar(label: "RHETORIC", userScore: Double(fullResult.userScore) / 100 * 0.95, oppScore: Double(fullResult.opponentScore) / 100 * 0.8)
        }
        .padding(.horizontal, 20)
        .padding(.top, 16)
        .opacity(detailsRevealed ? 1 : 0)
        .offset(y: detailsRevealed ? 0 : 10)
    }
    
    private func breakdownBar(label: String, userScore: Double, oppScore: Double) -> some View {
        VStack(spacing: 6) {
            HStack {
                Text(label)
                    .font(.system(size: 8, weight: .bold, design: .monospaced))
                    .foregroundStyle(.white.opacity(0.3))
                    .tracking(1)
                Spacer()
            }
            GeometryReader { geo in
                HStack(spacing: 2) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(
                            LinearGradient(
                                colors: [BroadcastTheme.success.opacity(0.8), BroadcastTheme.success.opacity(0.25)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geo.size.width * 0.48 * userScore)

                    Spacer(minLength: 0)

                    RoundedRectangle(cornerRadius: 2)
                        .fill(
                            LinearGradient(
                                colors: [BroadcastTheme.error.opacity(0.25), BroadcastTheme.error.opacity(0.8)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geo.size.width * 0.48 * oppScore)
                }
            }
            .frame(height: 4)
        }
    }
    
    private func analysisSection(_ fullResult: DebateResultStruct) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 10))
                        .foregroundStyle(BroadcastTheme.primary)
                    Text("AI JUDGE ANALYSIS")
                        .font(.system(size: 9, weight: .black, design: .monospaced))
                        .foregroundStyle(BroadcastTheme.primary)
                        .tracking(2)
                }

                Text(fullResult.reasoning)
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(BroadcastTheme.textSecondary)
                    .lineSpacing(6)
            }

            VStack(alignment: .leading, spacing: 12) {
                argumentBox(title: "YOUR STRONGEST", argument: fullResult.strongestArgument, color: BroadcastTheme.success)
                argumentBox(title: "OPPONENT'S STRONGEST", argument: fullResult.opponentStrongestArgument, color: BroadcastTheme.error)
            }

            if !fullResult.fallaciesSpotted.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("FALLACIES DETECTED")
                        .font(.system(size: 9, weight: .black, design: .monospaced))
                        .foregroundStyle(BroadcastTheme.error.opacity(0.8))
                        .tracking(1)

                    ForEach(fullResult.fallaciesSpotted, id: \.self) { fallacy in
                        HStack(spacing: 8) {
                            Circle()
                                .fill(BroadcastTheme.error.opacity(0.5))
                                .frame(width: 3, height: 3)
                            Text(fallacy)
                                .font(.system(size: 12))
                                .foregroundStyle(BroadcastTheme.textSecondary.opacity(0.85))
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(BroadcastTheme.primary.opacity(0.06))
        .clipShape(.rect(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(BroadcastTheme.primary.opacity(0.22), lineWidth: 0.5)
        )
        .padding(.horizontal, 16)
        .padding(.top, 20)
        .opacity(detailsRevealed ? 1 : 0)
        .offset(y: detailsRevealed ? 0 : 20)
    }
    
    private func argumentBox(title: String, argument: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 8, weight: .bold, design: .monospaced))
                .foregroundStyle(color.opacity(0.8))
                .tracking(1)
            Text(argument)
                .font(.system(size: 12))
                .foregroundStyle(.white.opacity(0.5))
                .lineSpacing(4)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(color.opacity(0.05))
        .clipShape(.rect(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(color.opacity(0.1), lineWidth: 0.5)
        )
    }
    
    private var actionButtons: some View {
        HStack(spacing: 12) {
            Button(action: onHome) {
                HStack(spacing: 8) {
                    Image(systemName: "house.fill")
                        .font(.system(size: 14))
                    Text("HOME")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .tracking(1)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(.white.opacity(0.05))
                .foregroundStyle(.white.opacity(0.7))
                .clipShape(.rect(cornerRadius: 12))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(.white.opacity(0.1), lineWidth: 0.5)
                )
            }
            
            Button(action: onRematch) {
                HStack(spacing: 8) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 14))
                    Text("REMATCH")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .tracking(1)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(BroadcastTheme.primaryGradient)
                .foregroundStyle(.white)
                .clipShape(.rect(cornerRadius: 12))
                .shadow(color: BroadcastTheme.primary.opacity(0.4), radius: 12, y: 5)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 24)
        .opacity(buttonsRevealed ? 1 : 0)
        .offset(y: buttonsRevealed ? 0 : 20)
    }
    
    private func createMockFullResult() -> DebateResultStruct? {
        let topic = DebateTopic(
            id: "1",
            title: "Should artificial intelligence replace human decision-making in critical sectors?",
            description: "Exploring the role of AI in healthcare, justice, and governance",
            category: .technology,
            difficulty: .advanced
        )
        
        let outcome: DebateOutcome
        let userScore: Int
        let opponentScore: Int
        let reasoning: String
        let strongestArgument: String
        let opponentStrongestArgument: String
        
        switch result {
        case .won:
            outcome = .win
            userScore = 85
            opponentScore = 72
            reasoning = "You demonstrated superior logical consistency and effectively countered your opponent's main points. Your evidence was well-researched and presented clearly."
            strongestArgument = "AI lacks the emotional intelligence and ethical reasoning required for critical human decisions."
            opponentStrongestArgument = "AI can process vast amounts of data without bias or fatigue."
        case .lost:
            outcome = .loss
            userScore = 68
            opponentScore = 81
            reasoning = "While you made some valid points, your opponent's arguments were more structured and supported by stronger evidence. Consider developing your rebuttals more thoroughly."
            strongestArgument = "Human oversight is essential for accountability in critical decisions."
            opponentStrongestArgument = "AI has already proven superior performance in specific domains like medical diagnosis."
        case .draw:
            outcome = .draw
            userScore = 75
            opponentScore = 75
            reasoning = "Both debaters presented equally compelling arguments with solid evidence. The debate showed high-quality reasoning on both sides without a clear winner."
            strongestArgument = "The complexity of human values cannot be reduced to algorithms."
            opponentStrongestArgument = "AI consistency eliminates human error and emotional bias."
        }
        
        return DebateResultStruct(
            id: UUID().uuidString,
            topic: topic,
            userScore: userScore,
            opponentScore: opponentScore,
            outcome: outcome,
            reasoning: reasoning,
            strongestArgument: strongestArgument,
            opponentStrongestArgument: opponentStrongestArgument,
            fallaciesSpotted: ["Appeal to emotion", "Slippery slope"],
            date: Date(),
            opponentName: "DebateMaster"
        )
    }
}

// Views like AnimatedMeshBackground, VignetteOverlay, and ScanlineOverlay 
// are defined in BroadcastComponents.swift

#Preview {
    VerdictView(
        result: .won,
        onRematch: {},
        onHome: {}
    )
}