import SwiftUI
import Combine

struct ProfileView: View {
    @StateObject private var viewModel = ProfileViewModel()
    @State private var showingSettings = false
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Profile Header
                    VStack(spacing: 12) {
                        AsyncImage(url: URL(string: viewModel.user?.profileImageURL ?? "")) { image in
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Circle()
                                .fill(BroadcastTheme.primary.opacity(0.3))
                                .overlay(
                                    Image(systemName: "person.fill")
                                        .font(.system(size: 30))
                                        .foregroundColor(BroadcastTheme.primary)
                                )
                        }
                        .frame(width: 100, height: 100)
                        .clipShape(Circle())
                        
                        Text(viewModel.user?.displayName ?? "Anonymous")
                            .font(.title2.bold())
                            .foregroundColor(BroadcastTheme.text)
                        
                        Text("@\(viewModel.user?.username ?? "user")")
                            .font(.subheadline)
                            .foregroundColor(BroadcastTheme.text.opacity(0.7))
                    }
                    .padding(.top, 20)
                    
                    // Stats Section
                    HStack(spacing: 30) {
                        StatCard(title: "Debates", value: "\(viewModel.stats.totalDebates)")
                        StatCard(title: "Wins", value: "\(viewModel.stats.wins)")
                        StatCard(title: "Win Rate", value: "\(viewModel.stats.winRate)%")
                    }
                    .padding(.horizontal)
                    
                    // Recent Activity
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Recent Activity")
                            .font(.headline)
                            .foregroundColor(BroadcastTheme.text)
                            .padding(.horizontal)
                        
                        LazyVStack(spacing: 8) {
                            ForEach(viewModel.recentDebates) { debate in
                                DebateHistoryCard(debate: debate)
                            }
                        }
                        .padding(.horizontal)
                    }
                }
            }
            .background(BroadcastTheme.background)
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
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
        .onAppear {
            viewModel.loadProfile()
        }
    }
}

struct StatCard: View {
    let title: String
    let value: String
    
    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title2.bold())
                .foregroundColor(BroadcastTheme.primary)
            Text(title)
                .font(.caption)
                .foregroundColor(BroadcastTheme.text.opacity(0.7))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 16)
        .background(BroadcastTheme.surface)
        .cornerRadius(12)
    }
}

struct DebateHistoryCard: View {
    let debate: DebateSession
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(debate.topic)
                    .font(.subheadline.weight(.medium))
                    .foregroundColor(BroadcastTheme.text)
                    .lineLimit(2)
                
                Text(debate.opponent)
                    .font(.caption)
                    .foregroundColor(BroadcastTheme.text.opacity(0.7))
                
                Text(debate.createdAt.formatted(date: .abbreviated, time: .omitted))
                    .font(.caption2)
                    .foregroundColor(BroadcastTheme.text.opacity(0.5))
            }
            
            Spacer()
            
            VStack(spacing: 4) {
                Circle()
                    .fill(debate.result == .won ? Color.green : debate.result == .lost ? Color.red : Color.orange)
                    .frame(width: 8, height: 8)
                
                Text(debate.result.rawValue.capitalized)
                    .font(.caption2)
                    .foregroundColor(BroadcastTheme.text.opacity(0.7))
            }
        }
        .padding()
        .background(BroadcastTheme.surface)
        .cornerRadius(12)
    }
}

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            List {
                Section("Account") {
                    HStack {
                        Image(systemName: "person")
                        Text("Edit Profile")
                    }
                    
                    HStack {
                        Image(systemName: "bell")
                        Text("Notifications")
                    }
                }
                
                Section("About") {
                    HStack {
                        Image(systemName: "info.circle")
                        Text("About DebateTV")
                    }
                    
                    HStack {
                        Image(systemName: "questionmark.circle")
                        Text("Help & Support")
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

@MainActor
class ProfileViewModel: ObservableObject {
    @Published var user: User?
    @Published var stats = UserStats()
    @Published var recentDebates: [DebateSession] = []
    
    func loadProfile() {
        // Load user profile and stats
        // This would integrate with your backend service
    }
}

struct UserStats {
    var totalDebates: Int = 0
    var wins: Int = 0
    var losses: Int = 0
    var draws: Int = 0
    
    var winRate: Int {
        guard totalDebates > 0 else { return 0 }
        return Int((Double(wins) / Double(totalDebates)) * 100)
    }
}

struct User {
    let id: String
    let username: String
    let displayName: String
    let profileImageURL: String?
}

#Preview {
    ProfileView()
}