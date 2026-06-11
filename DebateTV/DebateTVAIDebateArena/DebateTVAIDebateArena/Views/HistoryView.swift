import SwiftUI
import Combine

struct HistoryView: View {
    @StateObject private var viewModel = HistoryViewModel()
    @State private var selectedFilter: HistoryFilter = .all
    @State private var searchText = ""
    
    var body: some View {
        NavigationView {
            VStack {
                // Filter Tabs
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(HistoryFilter.allCases, id: \.self) { filter in
                            FilterTab(
                                title: filter.title,
                                isSelected: selectedFilter == filter
                            ) {
                                selectedFilter = filter
                                viewModel.filterDebates(by: filter)
                            }
                        }
                    }
                    .padding(.horizontal)
                }
                .padding(.vertical, 8)
                
                // Search Bar
                if !searchText.isEmpty || !viewModel.filteredDebates.isEmpty {
                    HStack {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.gray)
                        TextField("Search debates...", text: $searchText)
                            .textFieldStyle(PlainTextFieldStyle())
                    }
                    .padding(12)
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(10)
                    .padding(.horizontal)
                    .onChange(of: searchText) { _, newValue in
                        viewModel.searchDebates(query: newValue)
                    }
                }
                
                // Content
                Group {
                    if viewModel.isLoading {
                        LoadingView()
                    } else if viewModel.filteredDebates.isEmpty {
                        EmptyStateView(filter: selectedFilter)
                    } else {
                        DebatesList(debates: viewModel.filteredDebates)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .background(BroadcastTheme.background)
            .navigationTitle("History")
            .navigationBarTitleDisplayMode(.large)
            .refreshable {
                await viewModel.loadDebates()
            }
        }
        .onAppear {
            Task {
                await viewModel.loadDebates()
            }
        }
    }
}

struct FilterTab: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(.medium))
                .foregroundColor(isSelected ? .white : BroadcastTheme.text)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(
                    Capsule()
                        .fill(isSelected ? BroadcastTheme.primary : BroadcastTheme.surface)
                )
        }
        .buttonStyle(.plain)
    }
}

struct DebatesList: View {
    let debates: [DebateSession]
    
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(debates) { debate in
                    DebateHistoryRow(debate: debate)
                        .onTapGesture {
                            // Navigate to debate details
                        }
                }
            }
            .padding()
        }
    }
}

struct DebateHistoryRow: View {
    let debate: DebateSession
    
    var body: some View {
        HStack {
            // Result Indicator
            VStack {
                Circle()
                    .fill(debate.result.color)
                    .frame(width: 12, height: 12)
                
                Rectangle()
                    .fill(BroadcastTheme.text.opacity(0.1))
                    .frame(width: 1, height: 40)
            }
            
            VStack(alignment: .leading, spacing: 8) {
                // Header
                HStack {
                    Text(debate.topic)
                        .font(.headline)
                        .foregroundColor(BroadcastTheme.text)
                        .lineLimit(2)
                    
                    Spacer()
                    
                    Text(debate.createdAt.formatted(date: .abbreviated, time: .omitted))
                        .font(.caption)
                        .foregroundColor(BroadcastTheme.text.opacity(0.6))
                }
                
                // Opponent & Duration
                HStack {
                    HStack(spacing: 4) {
                        Image(systemName: "person")
                        Text(debate.opponent)
                    }
                    .font(.subheadline)
                    .foregroundColor(BroadcastTheme.text.opacity(0.7))
                    
                    Spacer()
                    
                    HStack(spacing: 4) {
                        Image(systemName: "clock")
                        Text(debate.duration)
                    }
                    .font(.subheadline)
                    .foregroundColor(BroadcastTheme.text.opacity(0.7))
                }
                
                // Result & Score
                HStack {
                    ResultBadge(result: debate.result)
                    
                    Spacer()
                    
                    if let score = debate.aiScore {
                        HStack(spacing: 4) {
                            Image(systemName: "star.fill")
                                .foregroundColor(.yellow)
                            Text("\(score, specifier: "%.1f")")
                                .font(.subheadline.weight(.medium))
                                .foregroundColor(BroadcastTheme.text)
                        }
                    }
                }
                
                // Key Arguments Preview
                if !debate.keyArguments.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Key Arguments:")
                            .font(.caption.weight(.medium))
                            .foregroundColor(BroadcastTheme.text.opacity(0.8))
                        
                        ForEach(Array(debate.keyArguments.prefix(2)), id: \.self) { argument in
                            Text("• \(argument)")
                                .font(.caption)
                                .foregroundColor(BroadcastTheme.text.opacity(0.6))
                                .lineLimit(1)
                        }
                    }
                    .padding(.top, 4)
                }
            }
            .padding(.leading, 8)
        }
        .padding()
        .background(BroadcastTheme.surface)
        .cornerRadius(16)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(debate.result.color.opacity(0.2), lineWidth: 1)
        )
    }
}

struct ResultBadge: View {
    let result: DebateResult
    
    var body: some View {
        Text(result.displayName)
            .font(.caption.weight(.medium))
            .foregroundColor(result.color)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(result.color.opacity(0.1))
            .cornerRadius(8)
    }
}

struct EmptyStateView: View {
    let filter: HistoryFilter
    @State private var tvStatic: Double = 0
    @State private var signalBars: [Bool] = [false, false, false, false, false]
    @State private var scanlineOffset: CGFloat = -100
    @State private var textGlitch: Bool = false
    
    var body: some View {
        ZStack {
            // TV static effect background
            TVStaticNoise()
                .opacity(0.03)
            
            VStack(spacing: 30) {
                // Broadcast signal indicator
                BroadcastSignalIndicator(signalStrength: 1)
                    .frame(width: 140, height: 100)
                
                // Glitchy text effect
                VStack(spacing: 12) {
                    Text(filter.emptyStateTitle)
                        .font(.system(size: 22, weight: .black, design: .monospaced))
                        .foregroundStyle(.white)
                        .tracking(textGlitch ? 3 : 1)
                        .shadow(color: BroadcastTheme.broadcastRed.opacity(textGlitch ? 0.5 : 0), radius: 10)
                    
                    Text(filter.emptyStateMessage)
                        .font(.system(size: 14, weight: .medium, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.6))
                        .multilineTextAlignment(.center)
                        .offset(x: textGlitch ? 2 : 0)
                }
                
                // Animated broadcast button
                if filter == .all {
                    BroadcastActionButton(title: "START FIRST DEBATE", icon: "play.fill") {
                        // Navigate to home/debate creation
                    }
                }
            }
        }
        .onAppear {
            // Glitch effect timer
            Timer.scheduledTimer(withTimeInterval: 2.5, repeats: true) { _ in
                withAnimation(.easeInOut(duration: 0.1)) {
                    textGlitch = true
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
                    textGlitch = false
                }
            }
        }
    }
}

struct LoadingView: View {
    @State private var rotation: Double = 0
    @State private var scale: Double = 0.8
    @State private var glowOpacity: Double = 0
    
    var body: some View {
        ZStack {
            // Animated broadcast rings
            ForEach(0..<3) { index in
                Circle()
                    .stroke(
                        LinearGradient(
                            colors: [
                                BroadcastTheme.broadcastRed.opacity(0.6),
                                BroadcastTheme.neonCyan.opacity(0.3)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 2
                    )
                    .frame(width: CGFloat(60 + index * 30), height: CGFloat(60 + index * 30))
                    .rotationEffect(.degrees(rotation + Double(index * 120)))
                    .scaleEffect(scale)
                    .opacity(1.0 - Double(index) * 0.3)
            }
            
            // Center broadcast icon
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(
                    LinearGradient(
                        colors: [BroadcastTheme.broadcastRed, BroadcastTheme.neonCyan],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .scaleEffect(scale * 1.1)
                .shadow(color: BroadcastTheme.broadcastRed, radius: glowOpacity * 20)
            
            // Pulsing glow
            Circle()
                .fill(BroadcastTheme.broadcastRed.opacity(0.2))
                .frame(width: 120, height: 120)
                .blur(radius: 30)
                .opacity(glowOpacity)
        }
        .frame(height: 200)
        .overlay(
            Text("RETRIEVING BROADCAST ARCHIVES")
                .font(.system(size: 12, weight: .black, design: .monospaced))
                .foregroundStyle(.white.opacity(0.7))
                .tracking(2)
                .offset(y: 100)
        )
        .onAppear {
            withAnimation(.linear(duration: 8).repeatForever(autoreverses: false)) {
                rotation = 360
            }
            withAnimation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true)) {
                scale = 1.1
                glowOpacity = 0.8
            }
        }
    }
}

@MainActor
class HistoryViewModel: ObservableObject {
    @Published var debates: [DebateSession] = []
    @Published var filteredDebates: [DebateSession] = []
    @Published var isLoading = false
    
    private var currentFilter: HistoryFilter = .all
    private var searchQuery = ""
    
    func loadDebates() async {
        isLoading = true
        defer { isLoading = false }
        
        // Load debates from backend/local storage
        // This would integrate with your backend service
        
        // Mock data for preview
        debates = [
            DebateSession(
                id: "1",
                topic: "Should artificial intelligence replace human judges?",
                opponent: "AI Advocate",
                result: .won,
                aiScore: 8.5,
                duration: "15:30",
                createdAt: Date().addingTimeInterval(-86400),
                keyArguments: ["Human judgment is irreplaceable", "AI lacks emotional intelligence"]
            ),
            DebateSession(
                id: "2",
                topic: "Climate change: Individual vs Corporate responsibility",
                opponent: "EcoWarrior",
                result: .lost,
                aiScore: 6.2,
                duration: "22:15",
                createdAt: Date().addingTimeInterval(-172800),
                keyArguments: ["Corporate accountability is key", "Individual actions matter too"]
            )
        ]
        
        applyCurrentFilters()
    }
    
    func filterDebates(by filter: HistoryFilter) {
        currentFilter = filter
        applyCurrentFilters()
    }
    
    func searchDebates(query: String) {
        searchQuery = query
        applyCurrentFilters()
    }
    
    private func applyCurrentFilters() {
        var filtered = debates
        
        // Apply filter
        switch currentFilter {
        case .all:
            break
        case .won:
            filtered = filtered.filter { $0.result == .won }
        case .lost:
            filtered = filtered.filter { $0.result == .lost }
        case .draw:
            filtered = filtered.filter { $0.result == .draw }
        case .recent:
            let oneWeekAgo = Date().addingTimeInterval(-604800)
            filtered = filtered.filter { $0.createdAt >= oneWeekAgo }
        }
        
        // Apply search
        if !searchQuery.isEmpty {
            filtered = filtered.filter { debate in
                debate.topic.localizedCaseInsensitiveContains(searchQuery) ||
                debate.opponent.localizedCaseInsensitiveContains(searchQuery) ||
                debate.keyArguments.contains { $0.localizedCaseInsensitiveContains(searchQuery) }
            }
        }
        
        // Sort by date (most recent first)
        filtered.sort { $0.createdAt > $1.createdAt }
        
        filteredDebates = filtered
    }
}

enum HistoryFilter: CaseIterable {
    case all, won, lost, draw, recent
    
    var title: String {
        switch self {
        case .all: return "All"
        case .won: return "Won"
        case .lost: return "Lost"
        case .draw: return "Draw"
        case .recent: return "Recent"
        }
    }
    
    var emptyStateIcon: String {
        switch self {
        case .all: return "calendar"
        case .won: return "trophy"
        case .lost: return "xmark.circle"
        case .draw: return "equal.circle"
        case .recent: return "clock"
        }
    }
    
    var emptyStateTitle: String {
        switch self {
        case .all: return "No Debates Yet"
        case .won: return "No Wins Yet"
        case .lost: return "No Losses"
        case .draw: return "No Draws"
        case .recent: return "No Recent Debates"
        }
    }
    
    var emptyStateMessage: String {
        switch self {
        case .all: return "Start debating to see your history here"
        case .won: return "Keep practicing to earn your first victory!"
        case .lost: return "Great! You haven't lost any debates yet"
        case .draw: return "No tied debates in your history"
        case .recent: return "Start a new debate to see recent activity"
        }
    }
}

// DebateResult extensions are defined in DebateModels.swift

#Preview {
    HistoryView()
}