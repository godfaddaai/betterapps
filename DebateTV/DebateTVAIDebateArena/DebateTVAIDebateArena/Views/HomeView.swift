import SwiftUI

struct HomeView: View {
    let debateService: DebateService
    let onStartDebate: (DebateCategory?) -> Void
    let onStartWithTopic: (DebateTopic) -> Void
    @State private var selectedCategory: DebateCategory?
    @State private var showProfile: Bool = false
    @State private var showHistory: Bool = false
    @State private var appeared: Bool = false
    @State private var heroGlow: Bool = false
    
    private var greeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        if hour < 12 { return "Good morning" }
        if hour < 17 { return "Good afternoon" }
        return "Good evening"
    }
    
    private var featuredTopic: DebateTopic {
        let dayIndex = Calendar.current.ordinality(of: .day, in: .year, for: Date()) ?? 0
        return DebateTopic.samples[dayIndex % DebateTopic.samples.count]
    }
    
    private var filteredTopics: [DebateTopic] {
        if let cat = selectedCategory {
            return DebateTopic.samples.filter { $0.category == cat }
        }
        return DebateTopic.samples
    }
    
    var body: some View {
        ZStack {
            BroadcastBackground()
            VignetteOverlay(intensity: 0.4)
            
            ScrollView {
                VStack(spacing: 0) {
                    headerBar
                        .padding(.top, 8)
                    
                    quickMatchHero
                        .padding(.top, 16)
                    
                    featuredTopicCard
                        .padding(.top, 24)
                    
                    categoryFilter
                        .padding(.top, 28)
                    
                    topicBrowser
                        .padding(.top, 14)
                    
                    recentMatchesSection
                        .padding(.top, 28)
                }
                .padding(.bottom, 60)
            }
            .scrollIndicators(.hidden)
        }
        .sheet(isPresented: $showProfile) {
            ProfileView()
        }
        .sheet(isPresented: $showHistory) {
            HistoryView()
        }
        .onAppear {
            withAnimation(.spring(response: 0.6).delay(0.1)) {
                appeared = true
            }
            withAnimation(.easeInOut(duration: 3).repeatForever(autoreverses: true)) {
                heroGlow = true
            }
        }
    }
    
    private var headerBar: some View {
        HStack(spacing: 12) {
            Button { showProfile = true } label: {
                HStack(spacing: 10) {
                    ZStack {
                        Circle()
                            .fill(BroadcastTheme.rankColor(debateService.profile.rank).opacity(0.08))
                            .frame(width: 44, height: 44)
                        Circle()
                            .stroke(BroadcastTheme.rankColor(debateService.profile.rank).opacity(0.25), lineWidth: 1.5)
                            .frame(width: 44, height: 44)
                        Text(debateService.profile.avatarEmoji)
                            .font(.system(size: 22))
                    }
                    VStack(alignment: .leading, spacing: 3) {
                        Text(greeting)
                            .font(.system(.caption2))
                            .foregroundStyle(.white.opacity(0.35))
                        Text(debateService.profile.username)
                            .font(.system(.subheadline, weight: .bold))
                            .foregroundStyle(.white)
                    }
                }
            }
            
            Spacer()
            
            HStack(spacing: 18) {
                Button { showHistory = true } label: {
                    Image(systemName: "clock.fill")
                        .font(.system(size: 18))
                        .foregroundStyle(.white.opacity(0.5))
                }
                
                Image(systemName: "bell.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(.white.opacity(0.3))
            }
        }
        .padding(.horizontal, 20)
        .opacity(appeared ? 1 : 0)
        .offset(y: appeared ? 0 : -10)
    }
    
    private var quickMatchHero: some View {
        Button {
            onStartDebate(nil)
        } label: {
            ZStack {
                RoundedRectangle(cornerRadius: 20)
                    .fill(
                        LinearGradient(
                            colors: [
                                BroadcastTheme.broadcastRed.opacity(0.12),
                                BroadcastTheme.stageAmber.opacity(0.08)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                
                RoundedRectangle(cornerRadius: 20)
                    .stroke(
                        LinearGradient(
                            colors: [
                                BroadcastTheme.broadcastRed.opacity(0.3),
                                BroadcastTheme.stageAmber.opacity(0.2)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
                
                if heroGlow {
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(BroadcastTheme.broadcastRed.opacity(0.2), lineWidth: 3)
                        .blur(radius: 8)
                }
                
                HStack(spacing: 0) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("QUICK MATCH")
                            .font(.system(size: 12, weight: .black, design: .monospaced))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                            .tracking(2)
                        
                        Text("Start Debating")
                            .font(.system(.title3, weight: .bold))
                            .foregroundStyle(.white)
                        
                        Text("Find an opponent in seconds")
                            .font(.system(.caption))
                            .foregroundStyle(.white.opacity(0.5))
                    }
                    
                    Spacer()
                    
                    ZStack {
                        Circle()
                            .fill(BroadcastTheme.broadcastRed.opacity(0.1))
                            .frame(width: 56, height: 56)
                        
                        Image(systemName: "play.fill")
                            .font(.system(size: 20))
                            .foregroundStyle(BroadcastTheme.broadcastRed)
                    }
                }
                .padding(24)
            }
            .frame(height: 120)
        }
        .padding(.horizontal, 20)
        .scaleEffect(appeared ? 1 : 0.95)
        .opacity(appeared ? 1 : 0)
    }
    
    private var featuredTopicCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("FEATURED TOPIC")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.stageAmber.opacity(0.8))
                    .tracking(2)
                
                Spacer()
                
                HStack(spacing: 4) {
                    Circle()
                        .fill(BroadcastTheme.stageAmber)
                        .frame(width: 5, height: 5)
                    Text("HOT")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundStyle(BroadcastTheme.stageAmber)
                }
            }
            
            Button {
                onStartWithTopic(featuredTopic)
            } label: {
                VStack(alignment: .leading, spacing: 10) {
                    Text(featuredTopic.title)
                        .font(.system(.headline, weight: .semibold))
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.leading)
                    
                    HStack(spacing: 12) {
                        Label(featuredTopic.category.rawValue, systemImage: "tag.fill")
                            .font(.system(.caption2))
                            .foregroundStyle(featuredTopic.category.color)
                        
                        Label("\(featuredTopic.difficulty) difficulty", systemImage: "gauge.medium")
                            .font(.system(.caption2))
                            .foregroundStyle(.white.opacity(0.4))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
                .background(.white.opacity(0.03))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(.white.opacity(0.05), lineWidth: 0.5)
                )
            }
        }
        .padding(.horizontal, 20)
        .opacity(appeared ? 1 : 0)
    }
    
    private var categoryFilter: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("CATEGORIES")
                .font(.system(size: 10, weight: .black, design: .monospaced))
                .foregroundStyle(.white.opacity(0.4))
                .tracking(2)
                .padding(.horizontal, 20)
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach([nil] + DebateCategory.allCases.map { $0 as DebateCategory? }, id: \.self) { category in
                        categoryChip(category)
                    }
                }
                .padding(.horizontal, 20)
            }
        }
        .opacity(appeared ? 1 : 0)
    }
    
    private func categoryChip(_ category: DebateCategory?) -> some View {
        Button {
            withAnimation(.snappy) {
                selectedCategory = category
            }
        } label: {
            Text(category?.rawValue ?? "All")
                .font(.system(.caption, weight: .semibold))
                .foregroundStyle(
                    selectedCategory == category ? .black : .white.opacity(0.7)
                )
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(
                    selectedCategory == category ?
                    AnyShapeStyle(category?.color ?? Color.white) :
                    AnyShapeStyle(.white.opacity(0.1))
                )
                .clipShape(Capsule())
                .overlay(
                    Capsule()
                        .stroke(
                            selectedCategory == category ?
                            Color.clear :
                            Color.white.opacity(0.1),
                            lineWidth: 0.5
                        )
                )
        }
    }
    
    private var topicBrowser: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("BROWSE TOPICS")
                .font(.system(size: 10, weight: .black, design: .monospaced))
                .foregroundStyle(.white.opacity(0.4))
                .tracking(2)
                .padding(.horizontal, 20)
            
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 10) {
                    ForEach(filteredTopics) { topic in
                        topicRow(topic)
                    }
                }
                .padding(.horizontal, 20)
            }
            .frame(height: 250)
        }
        .opacity(appeared ? 1 : 0)
    }
    
    private func topicRow(_ topic: DebateTopic) -> some View {
        Button {
            onStartWithTopic(topic)
        } label: {
            HStack(spacing: 12) {
                Circle()
                    .fill(topic.category.color.opacity(0.15))
                    .frame(width: 36, height: 36)
                    .overlay(
                        Image(systemName: topic.category.icon)
                            .font(.system(size: 16))
                            .foregroundStyle(topic.category.color)
                    )
                
                VStack(alignment: .leading, spacing: 4) {
                    Text(topic.title)
                        .font(.system(.footnote, weight: .medium))
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.leading)
                    
                    HStack(spacing: 8) {
                        Text(topic.category.rawValue)
                            .font(.system(size: 10))
                            .foregroundStyle(topic.category.color.opacity(0.8))
                        
                        Circle()
                            .fill(.white.opacity(0.2))
                            .frame(width: 3, height: 3)
                        
                        HStack(spacing: 2) {
                            ForEach(0..<topic.difficulty, id: \.self) { _ in
                                Image(systemName: "star.fill")
                                    .font(.system(size: 8))
                                    .foregroundStyle(.yellow.opacity(0.6))
                            }
                        }
                    }
                }
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .font(.system(size: 12))
                    .foregroundStyle(.white.opacity(0.2))
            }
            .padding(12)
            .background(.white.opacity(0.03))
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
    }
    
    private var recentMatchesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("RECENT MATCHES")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(.white.opacity(0.4))
                    .tracking(2)
                
                Spacer()
                
                Button { showHistory = true } label: {
                    Text("VIEW ALL")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(BroadcastTheme.neonCyan)
                }
            }
            .padding(.horizontal, 20)
            
            if debateService.debateHistory.isEmpty {
                emptyMatchesView
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(debateService.debateHistory.prefix(3)) { session in
                            recentMatchCard(sessionToResult(session))
                        }
                    }
                    .padding(.horizontal, 20)
                }
            }
        }
        .opacity(appeared ? 1 : 0)
    }
    
    private var emptyMatchesView: some View {
        VStack(spacing: 12) {
            Image(systemName: "tray.fill")
                .font(.system(size: 32))
                .foregroundStyle(.white.opacity(0.2))
            
            Text("No debates yet")
                .font(.system(.caption, weight: .medium))
                .foregroundStyle(.white.opacity(0.4))
            
            Text("Start your first debate above!")
                .font(.system(.caption2))
                .foregroundStyle(.white.opacity(0.3))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 32)
        .padding(.horizontal, 20)
    }
    
    private func recentMatchCard(_ debate: DebateResultStruct) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Circle()
                    .fill(outcomeColor(debate.outcome))
                    .frame(width: 8, height: 8)
                
                Text(debate.outcome.rawValue.uppercased())
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                    .foregroundStyle(outcomeColor(debate.outcome))
                
                Spacer()
                
                Text(formatDate(debate.date))
                    .font(.system(size: 9))
                    .foregroundStyle(.white.opacity(0.3))
            }
            
            Text(debate.topic.title)
                .font(.system(.caption, weight: .medium))
                .foregroundStyle(.white)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
            
            HStack {
                Label("\(debate.userScore)", systemImage: "person.fill")
                    .font(.system(size: 11))
                    .foregroundStyle(.white.opacity(0.5))
                
                Text("vs")
                    .font(.system(size: 10))
                    .foregroundStyle(.white.opacity(0.3))
                
                Label("\(debate.opponentScore)", systemImage: "person.2.fill")
                    .font(.system(size: 11))
                    .foregroundStyle(.white.opacity(0.5))
            }
        }
        .padding(14)
        .frame(width: 200)
        .background(.white.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(.white.opacity(0.05), lineWidth: 0.5)
        )
    }
    
    private func outcomeColor(_ outcome: DebateOutcome) -> Color {
        switch outcome {
        case .win: return BroadcastTheme.success
        case .loss: return BroadcastTheme.error
        case .draw: return BroadcastTheme.warning
        }
    }
    
    private func formatDate(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }
    
    private func sessionToResult(_ session: DebateSession) -> DebateResultStruct {
        DebateResultStruct(
            id: session.id,
            topic: DebateTopic(
                id: UUID().uuidString,
                title: session.topic,
                description: "",
                category: session.category ?? .technology,
                difficulty: 3
            ),
            userScore: Int(session.aiScore ?? 75),
            opponentScore: Int.random(in: 65...85),
            outcome: session.result == .won ? .win : session.result == .lost ? .loss : .draw,
            reasoning: "",
            strongestArgument: session.keyArguments.first ?? "",
            opponentStrongestArgument: "",
            fallaciesSpotted: [],
            date: session.createdAt,
            opponentName: session.opponent
        )
    }
}

// Extension to add rankColor to BroadcastTheme
extension BroadcastTheme {
    static func rankColor(_ rank: DebateRank) -> Color {
        switch rank {
        case .bronze: return Color(red: 0.8, green: 0.5, blue: 0.2)
        case .silver: return Color(red: 0.75, green: 0.75, blue: 0.75)
        case .gold: return Color(red: 1.0, green: 0.84, blue: 0.0)
        case .platinum: return Color(red: 0.9, green: 0.9, blue: 1.0)
        case .diamond: return Color(red: 0.73, green: 0.9, blue: 1.0)
        case .master: return Color(red: 0.58, green: 0.0, blue: 0.83)
        }
    }
}

// Add DebateRank enum
enum DebateRank: String, Codable, CaseIterable {
    case bronze = "Bronze"
    case silver = "Silver"
    case gold = "Gold"
    case platinum = "Platinum"
    case diamond = "Diamond"
    case master = "Master"
}

// Add UserProfile struct
struct UserProfile: Codable {
    var username: String
    var avatarEmoji: String
    var rank: DebateRank
    var wins: Int
    var losses: Int
    var draws: Int
    var streak: Int
    var bestStreak: Int
    var totalDebates: Int
    var averageScore: Double
    var joinDate: Date
    var hasCompletedOnboarding: Bool
    
    var winRate: Double {
        guard totalDebates > 0 else { return 0 }
        return Double(wins) / Double(totalDebates) * 100
    }
}

// Add DebateTopic extension for samples
extension DebateTopic {
    static let samples: [DebateTopic] = [
        DebateTopic(id: "1", title: "Is AI consciousness possible?", description: "Can artificial intelligence achieve true consciousness?", category: .technology, difficulty: 3),
        DebateTopic(id: "2", title: "Should voting be mandatory?", description: "Should democratic nations require citizens to vote?", category: .politics, difficulty: 2),
        DebateTopic(id: "3", title: "Does free will exist?", description: "Are our choices predetermined or do we have free will?", category: .philosophy, difficulty: 3),
        DebateTopic(id: "4", title: "Is privacy a right or a privilege?", description: "In the digital age, is privacy fundamental or earned?", category: .ethics, difficulty: 2),
        DebateTopic(id: "5", title: "Should space exploration be privatized?", description: "Should private companies lead space exploration?", category: .science, difficulty: 2),
        DebateTopic(id: "6", title: "Is social media a net positive?", description: "Do social media platforms help or harm society?", category: .social, difficulty: 1),
        DebateTopic(id: "7", title: "Should UBI replace welfare?", description: "Is universal basic income better than traditional welfare?", category: .economics, difficulty: 3),
    ]
}