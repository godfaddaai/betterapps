import Foundation
import SwiftUI

// MARK: - Core Debate Models

struct DebateSession: Identifiable, Codable {
    let id: String
    let topic: String
    let opponent: String
    let result: DebateResult
    let aiScore: Double?
    let duration: String
    let createdAt: Date
    let keyArguments: [String]
    let category: DebateCategory?
    let difficulty: DifficultyLevel?
    let viewerCount: Int?
    let reactions: [String]?
    
    init(id: String, topic: String, opponent: String, result: DebateResult, aiScore: Double? = nil, duration: String, createdAt: Date, keyArguments: [String], category: DebateCategory? = nil, difficulty: DifficultyLevel? = nil, viewerCount: Int? = nil, reactions: [String]? = nil) {
        self.id = id
        self.topic = topic
        self.opponent = opponent
        self.result = result
        self.aiScore = aiScore
        self.duration = duration
        self.createdAt = createdAt
        self.keyArguments = keyArguments
        self.category = category
        self.difficulty = difficulty
        self.viewerCount = viewerCount
        self.reactions = reactions
    }
}

enum DebateResult: String, Codable, CaseIterable {
    case won
    case lost
    case draw
    
    var displayName: String {
        switch self {
        case .won: return "Won"
        case .lost: return "Lost"
        case .draw: return "Draw"
        }
    }
    
    var color: Color {
        switch self {
        case .won: return .green
        case .lost: return .red
        case .draw: return .orange
        }
    }
    
    var icon: String {
        switch self {
        case .won: return "trophy.fill"
        case .lost: return "xmark.circle.fill"
        case .draw: return "equal.circle.fill"
        }
    }
}

// MARK: - Speaker Enum
enum Speaker {
    case user, opponent
}

// MARK: - Reaction Type
enum ReactionType: String, CaseIterable {
    case applause = "👏"
    case fire = "🔥"
    case thinking = "🤔"
    case mindBlown = "🤯"
    case heart = "❤️"
    
    var emoji: String {
        return rawValue
    }
}

// MARK: - Debate Topic Models

struct DebateTopic: Identifiable, Codable {
    let id: String
    let title: String
    let description: String
    let category: DebateCategory
    let difficultyLevel: DifficultyLevel
    
    var difficulty: Int {
        difficultyLevel.stars
    }
    let tags: [String]
    let participantCount: Int
    let trending: Bool
    let estimatedDuration: TimeInterval
    let backgroundInfo: String?
    
    // Convenience init for backwards compatibility
    init(id: String, title: String, description: String, category: DebateCategory, difficulty: Int) {
        self.id = id
        self.title = title
        self.description = description
        self.category = category
        self.difficultyLevel = difficulty == 1 ? .beginner : 
                              difficulty == 2 ? .intermediate : 
                              difficulty == 3 ? .advanced : .expert
        self.tags = []
        self.participantCount = 0
        self.trending = false
        self.estimatedDuration = 600
        self.backgroundInfo = nil
    }
    
    init(id: String = UUID().uuidString, title: String, description: String, category: DebateCategory, difficulty: DifficultyLevel, tags: [String] = [], participantCount: Int = 0, trending: Bool = false, estimatedDuration: TimeInterval = 1200, backgroundInfo: String? = nil) {
        self.id = id
        self.title = title
        self.description = description
        self.category = category
        self.difficultyLevel = difficulty
        self.tags = tags
        self.participantCount = participantCount
        self.trending = trending
        self.estimatedDuration = estimatedDuration
        self.backgroundInfo = backgroundInfo
    }
}

enum DebateCategory: String, Codable, CaseIterable {
    case politics = "Politics"
    case technology = "Technology"
    case science = "Science"
    case ethics = "Ethics"
    case economics = "Economics"
    case education = "Education"
    case environment = "Environment"
    case healthcare = "Healthcare"
    case social = "Social Issues"
    case philosophy = "Philosophy"
    case entertainment = "Entertainment"
    case sports = "Sports"
    
    var icon: String {
        switch self {
        case .politics: return "building.columns"
        case .technology: return "cpu"
        case .science: return "flask"
        case .ethics: return "scale.3d"
        case .economics: return "chart.line.uptrend.xyaxis"
        case .education: return "graduationcap"
        case .environment: return "leaf"
        case .healthcare: return "cross"
        case .social: return "person.3"
        case .philosophy: return "brain.head.profile"
        case .entertainment: return "tv"
        case .sports: return "sportscourt"
        }
    }
    
    var color: Color {
        switch self {
        case .politics: return .blue
        case .technology: return .purple
        case .science: return .green
        case .ethics: return .orange
        case .economics: return .red
        case .education: return .yellow
        case .environment: return .mint
        case .healthcare: return .pink
        case .social: return .indigo
        case .philosophy: return .brown
        case .entertainment: return .cyan
        case .sports: return .teal
        }
    }
    
    var description: String {
        switch self {
        case .politics: return "Government, policy, and political systems"
        case .technology: return "Tech innovation, AI, and digital society"
        case .science: return "Scientific research and discoveries"
        case .ethics: return "Moral principles and values"
        case .economics: return "Markets, trade, and economic policy"
        case .education: return "Learning systems and educational reform"
        case .environment: return "Climate, sustainability, and conservation"
        case .healthcare: return "Medical systems and health policy"
        case .social: return "Society, culture, and human rights"
        case .philosophy: return "Fundamental questions about existence"
        case .entertainment: return "Media, arts, and popular culture"
        case .sports: return "Athletics, competition, and sports culture"
        }
    }
}

// MARK: - Additional Result Models for VerdictView

nonisolated enum DebateOutcome: String, Codable, Sendable {
    case win = "Win"
    case loss = "Loss"
    case draw = "Draw"
}

nonisolated struct DebateResultStruct: Identifiable, Codable, Sendable {
    let id: String
    let topic: DebateTopic
    let userScore: Int
    let opponentScore: Int
    let outcome: DebateOutcome
    let reasoning: String
    let strongestArgument: String
    let opponentStrongestArgument: String
    let fallaciesSpotted: [String]
    let date: Date
    let opponentName: String
}

enum DifficultyLevel: String, Codable, CaseIterable {
    case beginner = "Beginner"
    case intermediate = "Intermediate"
    case advanced = "Advanced"
    case expert = "Expert"
    
    var stars: Int {
        switch self {
        case .beginner: return 1
        case .intermediate: return 2
        case .advanced: return 3
        case .expert: return 4
        }
    }
    
    var color: Color {
        switch self {
        case .beginner: return .green
        case .intermediate: return .blue
        case .advanced: return .orange
        case .expert: return .red
        }
    }
    
    var description: String {
        switch self {
        case .beginner: return "New to debating, simple topics"
        case .intermediate: return "Some experience, moderate complexity"
        case .advanced: return "Experienced debater, complex topics"
        case .expert: return "Expert level, highly nuanced topics"
        }
    }
    
    var requiredRating: Int {
        switch self {
        case .beginner: return 0
        case .intermediate: return 1200
        case .advanced: return 1600
        case .expert: return 2000
        }
    }
}

// MARK: - User and Opponent Models

struct DebateOpponent: Identifiable, Codable {
    let id: String
    let displayName: String
    let username: String
    let profileImageURL: String?
    let winRate: Int
    let totalDebates: Int
    let isOnline: Bool
    let skillLevel: DifficultyLevel
    let specialties: [DebateCategory]
    let rating: Int
    let lastActiveDate: Date?
    
    init(id: String = UUID().uuidString, displayName: String, username: String, profileImageURL: String? = nil, winRate: Int, totalDebates: Int, isOnline: Bool = false, skillLevel: DifficultyLevel = .intermediate, specialties: [DebateCategory] = [], rating: Int = 1500, lastActiveDate: Date? = nil) {
        self.id = id
        self.displayName = displayName
        self.username = username
        self.profileImageURL = profileImageURL
        self.winRate = winRate
        self.totalDebates = totalDebates
        self.isOnline = isOnline
        self.skillLevel = skillLevel
        self.specialties = specialties
        self.rating = rating
        self.lastActiveDate = lastActiveDate
    }
    
    var statusColor: Color {
        return isOnline ? .green : .gray
    }
    
    var skillLevelBadge: String {
        return skillLevel.rawValue
    }
}

struct LiveDebate: Identifiable, Codable {
    let id: String
    let topic: String
    let participants: [String]
    let viewerCount: Int
    let duration: String
    let category: DebateCategory
    let isLive: Bool
    let startTime: Date
    
    init(id: String = UUID().uuidString, topic: String, participants: [String], viewerCount: Int, duration: String, category: DebateCategory, isLive: Bool = true, startTime: Date = Date()) {
        self.id = id
        self.topic = topic
        self.participants = participants
        self.viewerCount = viewerCount
        self.duration = duration
        self.category = category
        self.isLive = isLive
        self.startTime = startTime
    }
}

// MARK: - AI Analysis Models

struct AIAnalysis: Codable {
    let overallScore: Double
    let result: DebateResult
    let strengths: [String]
    let improvements: [String]
    let detailedFeedback: String
    let criteriaScores: [AnalysisCriterion: Double]?
    let timestamp: Date
    
    init(overallScore: Double, result: DebateResult, strengths: [String], improvements: [String], detailedFeedback: String, criteriaScores: [AnalysisCriterion: Double]? = nil, timestamp: Date = Date()) {
        self.overallScore = overallScore
        self.result = result
        self.strengths = strengths
        self.improvements = improvements
        self.detailedFeedback = detailedFeedback
        self.criteriaScores = criteriaScores
        self.timestamp = timestamp
    }
    
    var formattedScore: String {
        return String(format: "%.1f", overallScore)
    }
    
    var scoreOutOf10: String {
        return "\(formattedScore)/10"
    }
    
    var performanceLevel: PerformanceLevel {
        switch overallScore {
        case 9.0...10.0: return .exceptional
        case 7.5..<9.0: return .excellent
        case 6.0..<7.5: return .good
        case 4.5..<6.0: return .fair
        default: return .needsImprovement
        }
    }
}

enum PerformanceLevel: String, CaseIterable {
    case exceptional = "Exceptional"
    case excellent = "Excellent"
    case good = "Good"
    case fair = "Fair"
    case needsImprovement = "Needs Improvement"
    
    var color: Color {
        switch self {
        case .exceptional: return .purple
        case .excellent: return .green
        case .good: return .blue
        case .fair: return .orange
        case .needsImprovement: return .red
        }
    }
    
    var description: String {
        switch self {
        case .exceptional: return "Outstanding performance across all criteria"
        case .excellent: return "Strong performance with minor areas for improvement"
        case .good: return "Solid performance with room for growth"
        case .fair: return "Adequate performance with several improvement areas"
        case .needsImprovement: return "Significant improvement needed across multiple areas"
        }
    }
}

// MARK: - Stream and Broadcast Models

struct BroadcastSettings: Codable {
    var quality: StreamQuality
    var audioBitrate: Int
    var videoBitrate: Int
    var frameRate: Int
    var recordLocally: Bool
    var enableLowLatency: Bool
    var autoStartRecording: Bool
    
    static let `default` = BroadcastSettings(
        quality: .medium,
        audioBitrate: 128,
        videoBitrate: 2500,
        frameRate: 30,
        recordLocally: true,
        enableLowLatency: true,
        autoStartRecording: false
    )
}

enum StreamQuality: String, Codable, CaseIterable {
    case low = "480p"
    case medium = "720p"
    case high = "1080p"
    
    var displayName: String {
        return rawValue
    }
    
    var videoBitrate: Int {
        switch self {
        case .low: return 1000 // 1 Mbps
        case .medium: return 2500 // 2.5 Mbps
        case .high: return 5000 // 5 Mbps
        }
    }
    
    var resolution: CGSize {
        switch self {
        case .low: return CGSize(width: 854, height: 480)
        case .medium: return CGSize(width: 1280, height: 720)
        case .high: return CGSize(width: 1920, height: 1080)
        }
    }
}

// MARK: - Statistics and Analytics Models

struct UserDebateStats: Codable {
    let totalDebates: Int
    let wins: Int
    let losses: Int
    let draws: Int
    let averageScore: Double
    let bestScore: Double
    let currentStreak: Int
    let longestStreak: Int
    let favoriteCategories: [DebateCategory]
    let totalViewTime: TimeInterval
    let totalDebateTime: TimeInterval
    
    var winRate: Double {
        guard totalDebates > 0 else { return 0.0 }
        return Double(wins) / Double(totalDebates) * 100
    }
    
    var lossRate: Double {
        guard totalDebates > 0 else { return 0.0 }
        return Double(losses) / Double(totalDebates) * 100
    }
    
    var drawRate: Double {
        guard totalDebates > 0 else { return 0.0 }
        return Double(draws) / Double(totalDebates) * 100
    }
    
    init(totalDebates: Int = 0, wins: Int = 0, losses: Int = 0, draws: Int = 0, averageScore: Double = 0.0, bestScore: Double = 0.0, currentStreak: Int = 0, longestStreak: Int = 0, favoriteCategories: [DebateCategory] = [], totalViewTime: TimeInterval = 0, totalDebateTime: TimeInterval = 0) {
        self.totalDebates = totalDebates
        self.wins = wins
        self.losses = losses
        self.draws = draws
        self.averageScore = averageScore
        self.bestScore = bestScore
        self.currentStreak = currentStreak
        self.longestStreak = longestStreak
        self.favoriteCategories = favoriteCategories
        self.totalViewTime = totalViewTime
        self.totalDebateTime = totalDebateTime
    }
}

struct DebateAnalytics: Codable {
    let sessionId: String
    let startTime: Date
    let endTime: Date?
    let speakingTime: TimeInterval
    let silenceTime: TimeInterval
    let interruptionCount: Int
    let averageSpeakingPace: Double // words per minute
    let emotionalTone: EmotionalTone
    let argumentCount: Int
    let questionCount: Int
    let evidenceUsageCount: Int
    
    var duration: TimeInterval {
        guard let endTime = endTime else { return 0 }
        return endTime.timeIntervalSince(startTime)
    }
    
    var speakingPercentage: Double {
        guard duration > 0 else { return 0 }
        return (speakingTime / duration) * 100
    }
}

enum EmotionalTone: String, Codable, CaseIterable {
    case calm = "Calm"
    case passionate = "Passionate"
    case aggressive = "Aggressive"
    case analytical = "Analytical"
    case humorous = "Humorous"
    case serious = "Serious"
    
    var color: Color {
        switch self {
        case .calm: return .blue
        case .passionate: return .red
        case .aggressive: return .orange
        case .analytical: return .purple
        case .humorous: return .green
        case .serious: return .gray
        }
    }
    
    var description: String {
        switch self {
        case .calm: return "Measured and composed delivery"
        case .passionate: return "Energetic and enthusiastic"
        case .aggressive: return "Forceful and confrontational"
        case .analytical: return "Logical and methodical"
        case .humorous: return "Light-hearted and witty"
        case .serious: return "Formal and grave"
        }
    }
}

// MARK: - Preferences and Settings Models

struct UserPreferences: Codable {
    var preferredCategories: [DebateCategory]
    var skillLevel: DifficultyLevel
    var maxDebateLength: TimeInterval
    var allowAnonymousOpponents: Bool
    var enableLiveAnalysis: Bool
    var autoSaveDebates: Bool
    var notificationSettings: NotificationSettings
    var privacySettings: PrivacySettings
    
    static let `default` = UserPreferences(
        preferredCategories: [],
        skillLevel: .beginner,
        maxDebateLength: 1800, // 30 minutes
        allowAnonymousOpponents: true,
        enableLiveAnalysis: true,
        autoSaveDebates: true,
        notificationSettings: .default,
        privacySettings: .default
    )
}

struct NotificationSettings: Codable {
    var debateInvitations: Bool
    var matchFound: Bool
    var debateStarting: Bool
    var analysisReady: Bool
    var achievements: Bool
    var weeklyReports: Bool
    
    static let `default` = NotificationSettings(
        debateInvitations: true,
        matchFound: true,
        debateStarting: true,
        analysisReady: true,
        achievements: true,
        weeklyReports: false
    )
}

struct PrivacySettings: Codable {
    var profileVisibility: ProfileVisibility
    var showDebateHistory: Bool
    var shareStatistics: Bool
    var allowRecording: Bool
    var dataCollection: Bool
    
    static let `default` = PrivacySettings(
        profileVisibility: .friendsOnly,
        showDebateHistory: true,
        shareStatistics: false,
        allowRecording: true,
        dataCollection: true
    )
}

enum ProfileVisibility: String, Codable, CaseIterable {
    case `public` = "Public"
    case friendsOnly = "Friends Only"
    case `private` = "Private"
    
    var description: String {
        switch self {
        case .`public`: return "Anyone can see your profile"
        case .friendsOnly: return "Only friends can see your profile"
        case .`private`: return "Profile is hidden from others"
        }
    }
}

// MARK: - Achievement and Gamification Models

struct Achievement: Identifiable, Codable {
    let id: String
    let title: String
    let description: String
    let iconName: String
    let category: AchievementCategory
    let points: Int
    let isUnlocked: Bool
    let unlockedDate: Date?
    let progress: Double // 0.0 to 1.0
    let requirement: String
    
    init(id: String = UUID().uuidString, title: String, description: String, iconName: String, category: AchievementCategory, points: Int, isUnlocked: Bool = false, unlockedDate: Date? = nil, progress: Double = 0.0, requirement: String) {
        self.id = id
        self.title = title
        self.description = description
        self.iconName = iconName
        self.category = category
        self.points = points
        self.isUnlocked = isUnlocked
        self.unlockedDate = unlockedDate
        self.progress = progress
        self.requirement = requirement
    }
    
    var progressPercentage: Int {
        return Int(progress * 100)
    }
}

enum AchievementCategory: String, Codable, CaseIterable {
    case debating = "Debating"
    case analysis = "Analysis"
    case social = "Social"
    case consistency = "Consistency"
    case improvement = "Improvement"
    
    var color: Color {
        switch self {
        case .debating: return .blue
        case .analysis: return .purple
        case .social: return .green
        case .consistency: return .orange
        case .improvement: return .red
        }
    }
}

// MARK: - Error Models

enum DebateError: Error, LocalizedError {
    case noInternetConnection
    case serverUnavailable
    case invalidSession
    case opponentDisconnected
    case streamingFailed
    case analysisUnavailable
    case permissionDenied
    case unknownError(String)
    
    var errorDescription: String? {
        switch self {
        case .noInternetConnection:
            return "No internet connection available"
        case .serverUnavailable:
            return "Debate service is temporarily unavailable"
        case .invalidSession:
            return "Invalid debate session"
        case .opponentDisconnected:
            return "Your opponent has disconnected"
        case .streamingFailed:
            return "Failed to start video stream"
        case .analysisUnavailable:
            return "AI analysis is temporarily unavailable"
        case .permissionDenied:
            return "Required permissions not granted"
        case .unknownError(let message):
            return "An error occurred: \(message)"
        }
    }
    
    var recoveryMessage: String {
        switch self {
        case .noInternetConnection:
            return "Please check your internet connection and try again"
        case .serverUnavailable:
            return "Please try again in a few minutes"
        case .invalidSession:
            return "Please start a new debate session"
        case .opponentDisconnected:
            return "You can wait for reconnection or end the debate"
        case .streamingFailed:
            return "Check camera and microphone permissions"
        case .analysisUnavailable:
            return "Analysis will be available after the debate"
        case .permissionDenied:
            return "Grant required permissions in Settings"
        case .unknownError:
            return "Please try again or contact support"
        }
    }
}

// MARK: - Mock Data Extensions

extension DebateSession {
    static var mockSessions: [DebateSession] {
        return [
            DebateSession(
                id: "1",
                topic: "Should artificial intelligence replace human judges in legal proceedings?",
                opponent: "AI Advocate",
                result: .won,
                aiScore: 8.7,
                duration: "18:42",
                createdAt: Date().addingTimeInterval(-86400),
                keyArguments: ["Human judgment irreplaceable", "AI lacks empathy", "Legal precedent importance"],
                category: .technology,
                difficulty: .advanced,
                viewerCount: 127
            ),
            DebateSession(
                id: "2",
                topic: "Climate change: Individual responsibility vs Corporate accountability",
                opponent: "EcoWarrior",
                result: .lost,
                aiScore: 6.8,
                duration: "22:15",
                createdAt: Date().addingTimeInterval(-172800),
                keyArguments: ["Corporate responsibility primary", "Systemic change needed", "Individual actions limited"],
                category: .environment,
                difficulty: .intermediate,
                viewerCount: 89
            ),
            DebateSession(
                id: "3",
                topic: "Should social media platforms be regulated by government?",
                opponent: "TechLibertarian",
                result: .draw,
                aiScore: 7.5,
                duration: "16:33",
                createdAt: Date().addingTimeInterval(-259200),
                keyArguments: ["Free speech concerns", "Platform responsibility", "Government overreach"],
                category: .politics,
                difficulty: .advanced,
                viewerCount: 203
            )
        ]
    }
}

extension DebateTopic {
    static var trendingTopics: [DebateTopic] {
        return [
            DebateTopic(
                title: "Should AI art be considered legitimate art?",
                description: "Exploring the artistic value and authenticity of AI-generated artwork",
                category: .technology,
                difficulty: .intermediate,
                tags: ["AI", "art", "creativity"],
                participantCount: 245,
                trending: true
            ),
            DebateTopic(
                title: "Universal Basic Income: Solution or Problem?",
                description: "Examining the economic and social implications of UBI",
                category: .economics,
                difficulty: .advanced,
                tags: ["UBI", "economics", "policy"],
                participantCount: 189,
                trending: true
            ),
            DebateTopic(
                title: "Space exploration vs Earth's problems",
                description: "Should we focus on space exploration or solving Earth's issues first?",
                category: .science,
                difficulty: .intermediate,
                tags: ["space", "priorities", "resources"],
                participantCount: 156,
                trending: true
            )
        ]
    }
}

extension UserDebateStats {
    static var mockStats: UserDebateStats {
        return UserDebateStats(
            totalDebates: 47,
            wins: 28,
            losses: 15,
            draws: 4,
            averageScore: 7.3,
            bestScore: 9.2,
            currentStreak: 3,
            longestStreak: 8,
            favoriteCategories: [.technology, .environment, .politics],
            totalViewTime: 14400, // 4 hours
            totalDebateTime: 25200 // 7 hours
        )
    }
}