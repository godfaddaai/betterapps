import SwiftUI
import Combine

struct ProfileView: View {
    @StateObject private var viewModel = ProfileViewModel()
    @State private var showingSettings = false
    @State private var editingUsername = false
    @State private var draftUsername = ""

    var body: some View {
        NavigationStack {
            ZStack {
                BroadcastBackground()

                ScrollView {
                    VStack(spacing: 24) {
                        profileHeader
                        statsRow
                        recentActivity
                    }
                    .padding(.bottom, 40)
                }
                .scrollIndicators(.hidden)
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(BroadcastTheme.background, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { showingSettings = true }) {
                        Image(systemName: "gearshape")
                            .foregroundColor(BroadcastTheme.primary)
                    }
                }
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView()
        }
        .alert("Edit Username", isPresented: $editingUsername) {
            TextField("Username", text: $draftUsername)
            Button("Save") {
                viewModel.saveUsername(draftUsername)
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This name shows up on your verdict cards.")
        }
        .onAppear {
            viewModel.loadProfile()
        }
    }

    // MARK: - Header

    private var profileHeader: some View {
        VStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(BroadcastTheme.primary.opacity(0.12))
                    .frame(width: 110, height: 110)
                    .blur(radius: 12)

                Circle()
                    .fill(BroadcastTheme.surface)
                    .frame(width: 96, height: 96)

                Circle()
                    .stroke(BroadcastTheme.primaryGradient, lineWidth: 2)
                    .frame(width: 96, height: 96)

                Text(String(viewModel.username.prefix(1)).uppercased())
                    .font(.system(size: 38, weight: .black, design: .monospaced))
                    .foregroundStyle(BroadcastTheme.primary)
            }

            HStack(spacing: 8) {
                Text(viewModel.username)
                    .font(.title2.bold())
                    .foregroundColor(BroadcastTheme.text)

                Button {
                    draftUsername = viewModel.username
                    editingUsername = true
                } label: {
                    Image(systemName: "pencil")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(BroadcastTheme.primary)
                        .padding(6)
                        .background(BroadcastTheme.primary.opacity(0.12))
                        .clipShape(Circle())
                }
            }

            Text("ON THE RECORD SINCE \(viewModel.joinYear)")
                .font(.system(size: 9, weight: .black, design: .monospaced))
                .foregroundStyle(BroadcastTheme.textSecondary.opacity(0.8))
                .tracking(2)
        }
        .padding(.top, 24)
    }

    // MARK: - Stats

    private var statsRow: some View {
        HStack(spacing: 12) {
            StatCard(title: "Debates", value: "\(viewModel.stats.totalDebates)")
            StatCard(title: "Wins", value: "\(viewModel.stats.wins)", accent: BroadcastTheme.success)
            StatCard(title: "Win Rate", value: "\(viewModel.stats.winRate)%")
        }
        .padding(.horizontal, 20)
    }

    // MARK: - Recent Activity

    private var recentActivity: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("RECENT ACTIVITY")
                .font(.system(size: 10, weight: .black, design: .monospaced))
                .foregroundStyle(BroadcastTheme.textSecondary.opacity(0.8))
                .tracking(2)
                .padding(.horizontal, 20)

            if viewModel.recentDebates.isEmpty {
                VStack(spacing: 10) {
                    Image(systemName: "mic.slash.fill")
                        .font(.system(size: 28))
                        .foregroundStyle(BroadcastTheme.primary.opacity(0.4))
                    Text("No debates on the record yet")
                        .font(.system(.caption, weight: .medium))
                        .foregroundStyle(BroadcastTheme.textSecondary)
                    Text("Win one and it shows up here.")
                        .font(.system(.caption2))
                        .foregroundStyle(BroadcastTheme.textSecondary.opacity(0.7))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 28)
            } else {
                LazyVStack(spacing: 8) {
                    ForEach(viewModel.recentDebates) { debate in
                        DebateHistoryCard(debate: debate)
                    }
                }
                .padding(.horizontal, 20)
            }
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    var accent: Color = BroadcastTheme.primary

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(.title2, design: .monospaced).weight(.black))
                .foregroundColor(accent)
            Text(title)
                .font(.caption)
                .foregroundColor(BroadcastTheme.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 16)
        .background(BroadcastTheme.surface.opacity(0.85))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(accent.opacity(0.18), lineWidth: 0.5)
        )
    }
}

struct DebateHistoryCard: View {
    let debate: DebateSession

    private var resultColor: Color {
        switch debate.result {
        case .won: return BroadcastTheme.success
        case .lost: return BroadcastTheme.error
        case .draw: return BroadcastTheme.warning
        }
    }

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(debate.topic)
                    .font(.subheadline.weight(.medium))
                    .foregroundColor(BroadcastTheme.text)
                    .lineLimit(2)

                Text("vs \(debate.opponent)")
                    .font(.caption)
                    .foregroundColor(BroadcastTheme.textSecondary)

                Text(debate.createdAt.formatted(date: .abbreviated, time: .omitted))
                    .font(.caption2)
                    .foregroundColor(BroadcastTheme.textSecondary.opacity(0.6))
            }

            Spacer()

            VStack(spacing: 4) {
                Circle()
                    .fill(resultColor)
                    .frame(width: 8, height: 8)
                    .shadow(color: resultColor.opacity(0.6), radius: 4)

                Text(debate.result.rawValue.capitalized)
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                    .foregroundColor(resultColor)
            }
        }
        .padding()
        .background(BroadcastTheme.surface.opacity(0.7))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(BroadcastTheme.primary.opacity(0.1), lineWidth: 0.5)
        )
    }
}

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("Account") {
                    HStack {
                        Image(systemName: "person")
                            .foregroundStyle(BroadcastTheme.primary)
                        Text("Edit Profile")
                    }

                    HStack {
                        Image(systemName: "bell")
                            .foregroundStyle(BroadcastTheme.primary)
                        Text("Notifications")
                    }
                }
                .listRowBackground(BroadcastTheme.surface)

                Section("About") {
                    HStack {
                        Image(systemName: "info.circle")
                            .foregroundStyle(BroadcastTheme.primary)
                        Text("About DebateTV")
                    }

                    HStack {
                        Image(systemName: "questionmark.circle")
                            .foregroundStyle(BroadcastTheme.primary)
                        Text("Help & Support")
                    }
                }
                .listRowBackground(BroadcastTheme.surface)
            }
            .scrollContentBackground(.hidden)
            .background(BroadcastTheme.backgroundGradient.ignoresSafeArea())
            .foregroundStyle(BroadcastTheme.text)
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(BroadcastTheme.background, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundStyle(BroadcastTheme.primary)
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}

// MARK: - ViewModel

@MainActor
class ProfileViewModel: ObservableObject {
    @Published var username: String = ProfileStore.loadUsername()
    @Published var stats = UserStats()
    @Published var recentDebates: [DebateSession] = []

    var joinYear: String {
        String(Calendar.current.component(.year, from: ProfileStore.loadJoinDate()))
    }

    func loadProfile() {
        username = ProfileStore.loadUsername()
        stats = ProfileStore.loadStats()
        recentDebates = ProfileStore.loadRecentSessions()
    }

    func saveUsername(_ name: String) {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        username = trimmed
        ProfileStore.saveUsername(trimmed)
    }
}

// MARK: - Local Persistence (UserDefaults)

/// Lightweight local profile persistence. Fed by `DebateService.addDebateToHistory`
/// every time a debate completes, read by `ProfileViewModel`.
enum ProfileStore {
    private static let usernameKey = "profile.username"
    private static let statsKey = "profile.stats"
    private static let sessionsKey = "profile.recentSessions"
    private static let joinDateKey = "profile.joinDate"
    private static let maxStoredSessions = 25

    static func loadUsername() -> String {
        UserDefaults.standard.string(forKey: usernameKey) ?? "DebateUser"
    }

    static func saveUsername(_ name: String) {
        UserDefaults.standard.set(name, forKey: usernameKey)
    }

    static func loadJoinDate() -> Date {
        if let date = UserDefaults.standard.object(forKey: joinDateKey) as? Date {
            return date
        }
        let now = Date()
        UserDefaults.standard.set(now, forKey: joinDateKey)
        return now
    }

    static func loadStats() -> UserStats {
        guard let data = UserDefaults.standard.data(forKey: statsKey),
              let stats = try? JSONDecoder().decode(UserStats.self, from: data) else {
            return UserStats()
        }
        return stats
    }

    static func loadRecentSessions() -> [DebateSession] {
        guard let data = UserDefaults.standard.data(forKey: sessionsKey),
              let sessions = try? JSONDecoder().decode([DebateSession].self, from: data) else {
            return []
        }
        return sessions
    }

    /// Record a completed debate: bump stats + prepend to the recent list (newest first).
    static func record(_ session: DebateSession) {
        var stats = loadStats()
        stats.totalDebates += 1
        switch session.result {
        case .won: stats.wins += 1
        case .lost: stats.losses += 1
        case .draw: stats.draws += 1
        }
        if let data = try? JSONEncoder().encode(stats) {
            UserDefaults.standard.set(data, forKey: statsKey)
        }

        var sessions = loadRecentSessions()
        sessions.insert(session, at: 0)
        if sessions.count > maxStoredSessions {
            sessions = Array(sessions.prefix(maxStoredSessions))
        }
        if let data = try? JSONEncoder().encode(sessions) {
            UserDefaults.standard.set(data, forKey: sessionsKey)
        }

        _ = loadJoinDate() // ensure join date exists from the first recorded debate
    }
}

struct UserStats: Codable {
    var totalDebates: Int = 0
    var wins: Int = 0
    var losses: Int = 0
    var draws: Int = 0

    var winRate: Int {
        guard totalDebates > 0 else { return 0 }
        return Int((Double(wins) / Double(totalDebates)) * 100)
    }
}

#Preview {
    ProfileView()
}
