import Foundation
import SwiftUI


nonisolated enum DebateRank: String, Codable, CaseIterable, Sendable {
    case bronze = "Bronze"
    case silver = "Silver"
    case gold = "Gold"
    case platinum = "Platinum"
    case diamond = "Diamond"


    var icon: String {
        switch self {
        case .bronze: "shield.fill"
        case .silver: "shield.lefthalf.filled"
        case .gold: "star.circle.fill"
        case .platinum: "crown.fill"
        case .diamond: "diamond.fill"
        }
    }


    var minWins: Int {
        switch self {
        case .bronze: 0
        case .silver: 5
        case .gold: 15
        case .platinum: 30
        case .diamond: 50
        }
    }
}


nonisolated enum DebateCategory: String, Codable, CaseIterable, Sendable {
    case philosophy = "Philosophy"
    case politics = "Politics"
    case technology = "Technology"
    case ethics = "Ethics"
    case science = "Science"
    case culture = "Culture"
    
    var icon: String {
        switch self {
        case .philosophy: return "book.fill"
        case .politics: return "building.columns.fill"
        case .technology: return "laptopcomputer"
        case .ethics: return "scale.3d"
        case .science: return "atom"
        case .culture: return "globe.americas.fill"
        }
    }
}

struct UserProfile: Codable, Sendable {
    var id: UUID = UUID()
    var name: String = "Debater"
    var rank: DebateRank = .bronze
    var wins: Int = 0
    var losses: Int = 0
    var avatarStyle: String = "person.fill"
    
    static let initial = UserProfile()
}

struct DebateTopic: Identifiable, Sendable {
    var id: UUID = UUID()
    var title: String
    var category: DebateCategory
    var summary: String
    
    static let samples: [DebateTopic] = [
        DebateTopic(title: "Is AGI dangerous?", category: .technology, summary: ""),
        DebateTopic(title: "Meaning of life?", category: .philosophy, summary: "")
    ]
}

enum DebateOutcome: String, Codable, Sendable {
    case win = "Win"
    case loss = "Loss"
    case draw = "Draw"
}

struct DebateResult: Identifiable, Codable, Sendable {
    var id: UUID = UUID()
    var date: Date = Date()
    var topic: String
    var outcome: DebateOutcome
    var userScore: Int
    var opponentScore: Int
    var reasoning: String
    var strongArguments: [String]
    var weakArguments: [String]
}