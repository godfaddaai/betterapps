import Foundation


@Observable
final class DebateService {
    var profile: UserProfile = .initial
    var debateHistory: [DebateResult] = []


    private let profileKey = "user_profile"
    private let historyKey = "debate_history"


    init() {
        loadProfile()
        loadHistory()
    }


    func loadProfile() {
        guard let data = UserDefaults.standard.data(forKey: profileKey),
              let decoded = try? JSONDecoder().decode(UserProfile.self, from: data) else { return }
        profile = decoded
    }


    func saveProfile() {
        guard let data = try? JSONEncoder().encode(profile) else { return }
        UserDefaults.standard.set(data, forKey: profileKey)
    }


    func loadHistory() {
        guard let data = UserDefaults.standard.data(forKey: historyKey),
              let decoded = try? JSONDecoder().decode([DebateResult].self, from: data) else { return }
        debateHistory = decoded
    }


    func saveHistory() {
        guard let data = try? JSONEncoder().encode(debateHistory) else { return }
        UserDefaults.standard.set(data, forKey: historyKey)
    }
}