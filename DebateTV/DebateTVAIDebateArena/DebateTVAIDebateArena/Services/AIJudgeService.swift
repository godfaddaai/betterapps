import Foundation
import Combine

class AIJudgeService: ObservableObject {
    // MARK: - Published Properties
    @Published var analysisInProgress = false
    @Published var currentAnalysis: LiveAnalysis?
    @Published var confidenceScore: Double = 0.0
    
    // MARK: - Publishers
    let liveAnalysisPublisher = PassthroughSubject<LiveAnalysis, Never>()
    let finalAnalysisPublisher = PassthroughSubject<AIAnalysis, Never>()
    let argumentScorePublisher = PassthroughSubject<ArgumentScore, Never>()
    
    // MARK: - Private Properties
    private let networkService = AINetworkService()
    private var analysisTimer: Timer?
    private var cancellables = Set<AnyCancellable>()
    private var currentDebateTranscript: [DebateSegment] = []
    private var argumentCounter = 0
    
    // Analysis criteria weights
    private let criteriaWeights: [AnalysisCriterion: Double] = [
        .logicalConsistency: 0.25,
        .evidenceQuality: 0.20,
        .argumentStrength: 0.20,
        .rebuttalEffectiveness: 0.15,
        .communicationClarity: 0.10,
        .factualAccuracy: 0.10
    ]
    
    // MARK: - Initialization
    
    init() {
        setupAnalysisTimer()
    }
    
    deinit {
        stopAnalysis()
    }
    
    // MARK: - Public Methods
    
    func startLiveAnalysis(for debateId: String) {
        analysisInProgress = true
        currentDebateTranscript.removeAll()
        argumentCounter = 0
        
        startAnalysisTimer()
        
        // Initialize live analysis
        currentAnalysis = LiveAnalysis(
            debateId: debateId,
            currentScore: LiveScore(user: 5.0, opponent: 5.0),
            strengths: [],
            improvements: [],
            momentum: .neutral,
            lastUpdated: Date()
        )
    }
    
    func stopAnalysis() {
        analysisInProgress = false
        stopAnalysisTimer()
    }
    
    func processArgument(_ argument: String, speaker: Speaker, timestamp: Date) {
        let segment = DebateSegment(
            id: UUID().uuidString,
            speaker: speaker,
            content: argument,
            timestamp: timestamp,
            duration: 0
        )
        
        currentDebateTranscript.append(segment)
        argumentCounter += 1
        
        // Analyze argument in background
        Task {
            let score = await analyzeArgument(segment)
            
            await MainActor.run {
                self.argumentScorePublisher.send(score)
                self.updateLiveAnalysis(with: score)
            }
        }
    }
    
    func generateFinalAnalysis() async -> AIAnalysis {
        analysisInProgress = true
        defer { analysisInProgress = false }
        
        // Simulate comprehensive analysis
        try? await Task.sleep(nanoseconds: 2_000_000_000) // 2 seconds
        
        let finalAnalysis = await performComprehensiveAnalysis()
        
        await MainActor.run {
            self.finalAnalysisPublisher.send(finalAnalysis)
        }
        
        return finalAnalysis
    }
    
    func getArgumentSuggestions(for context: String, position: ArgumentPosition) async -> [ArgumentSuggestion] {
        // Simulate AI generating argument suggestions
        try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
        
        let suggestions = generateArgumentSuggestions(for: context, position: position)
        return suggestions
    }
    
    func analyzeFactualClaim(_ claim: String) async -> FactCheckResult {
        // Simulate fact-checking
        try? await Task.sleep(nanoseconds: 1_500_000_000) // 1.5 seconds
        
        return FactCheckResult(
            claim: claim,
            accuracy: FactualAccuracy.allCases.randomElement()!,
            confidence: Double.random(in: 0.7...0.95),
            sources: [
                "Wikipedia: Relevant Article",
                "Scholarly Journal: Research Paper",
                "Government Source: Official Statistics"
            ],
            explanation: "This claim has been verified against multiple reliable sources."
        )
    }
    
    func getRealTimeFeedback() -> RealTimeFeedback? {
        guard let analysis = currentAnalysis else { return nil }
        
        return RealTimeFeedback(
            speakingPace: generatePaceFeedback(),
            tonality: generateTonalityFeedback(),
            argumentStrength: analysis.currentScore.user,
            suggestions: generateImprovementSuggestions()
        )
    }
    
    // MARK: - Private Methods
    
    private func setupAnalysisTimer() {
        analysisTimer = Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { [weak self] _ in
            self?.updateLiveAnalysis()
        }
    }
    
    private func startAnalysisTimer() {
        guard analysisTimer == nil else { return }
        setupAnalysisTimer()
    }
    
    private func stopAnalysisTimer() {
        analysisTimer?.invalidate()
        analysisTimer = nil
    }
    
    private func updateLiveAnalysis() {
        guard var analysis = currentAnalysis else { return }
        
        // Update scores based on recent arguments
        analysis.currentScore = calculateCurrentScores()
        analysis.momentum = calculateMomentum()
        analysis.strengths = generateCurrentStrengths()
        analysis.improvements = generateCurrentImprovements()
        analysis.lastUpdated = Date()
        
        currentAnalysis = analysis
        liveAnalysisPublisher.send(analysis)
    }
    
    private func updateLiveAnalysis(with argumentScore: ArgumentScore) {
        guard var analysis = currentAnalysis else { return }
        
        // Update scores based on argument
        if argumentScore.speaker == .user {
            analysis.currentScore.user = min(10.0, analysis.currentScore.user + argumentScore.impact)
        } else {
            analysis.currentScore.opponent = min(10.0, analysis.currentScore.opponent + argumentScore.impact)
        }
        
        // Update momentum
        analysis.momentum = argumentScore.impact > 0.2 ? .gaining : argumentScore.impact < -0.2 ? .losing : .neutral
        
        currentAnalysis = analysis
        liveAnalysisPublisher.send(analysis)
    }
    
    private func analyzeArgument(_ segment: DebateSegment) async -> ArgumentScore {
        // Simulate AI analysis of argument
        let analysisResults = await performArgumentAnalysis(segment)
        
        let score = ArgumentScore(
            id: segment.id,
            speaker: segment.speaker,
            logicalConsistency: analysisResults.logicalConsistency,
            evidenceQuality: analysisResults.evidenceQuality,
            clarity: analysisResults.clarity,
            relevance: analysisResults.relevance,
            impact: analysisResults.overallImpact,
            timestamp: segment.timestamp
        )
        
        return score
    }
    
    private func performArgumentAnalysis(_ segment: DebateSegment) async -> ArgumentAnalysisResult {
        // Simulate comprehensive argument analysis
        try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds
        
        return ArgumentAnalysisResult(
            logicalConsistency: Double.random(in: 6.0...9.5),
            evidenceQuality: Double.random(in: 5.5...9.0),
            clarity: Double.random(in: 7.0...9.8),
            relevance: Double.random(in: 6.5...9.3),
            overallImpact: Double.random(in: -0.5...0.8)
        )
    }
    
    private func performComprehensiveAnalysis() async -> AIAnalysis {
        // Analyze entire debate transcript
        var totalScores: [AnalysisCriterion: (user: Double, opponent: Double)] = [:]
        
        // Initialize scores
        for criterion in AnalysisCriterion.allCases {
            totalScores[criterion] = (user: 0.0, opponent: 0.0)
        }
        
        // Analyze each segment
        for segment in currentDebateTranscript {
            let segmentAnalysis = await performDetailedSegmentAnalysis(segment)
            
            for criterion in AnalysisCriterion.allCases {
                let score = segmentAnalysis.scores[criterion] ?? 0.0
                if segment.speaker == .user {
                    totalScores[criterion]?.user += score
                } else {
                    totalScores[criterion]?.opponent += score
                }
            }
        }
        
        // Calculate weighted overall scores
        let userScore = calculateWeightedScore(totalScores, for: .user)
        let opponentScore = calculateWeightedScore(totalScores, for: .opponent)
        
        // Determine result
        let result: DebateResult
        let scoreDifference = userScore - opponentScore
        
        if abs(scoreDifference) < 0.5 {
            result = .draw
        } else if scoreDifference > 0 {
            result = .won
        } else {
            result = .lost
        }
        
        return AIAnalysis(
            overallScore: userScore,
            result: result,
            strengths: generateFinalStrengths(totalScores),
            improvements: generateFinalImprovements(totalScores),
            detailedFeedback: generateDetailedFeedback(totalScores, userScore: userScore, opponentScore: opponentScore),
            criteriaScores: extractCriteriaScores(totalScores, for: .user)
        )
    }
    
    private func performDetailedSegmentAnalysis(_ segment: DebateSegment) async -> DetailedSegmentAnalysis {
        // Simulate detailed AI analysis of segment
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds
        
        var scores: [AnalysisCriterion: Double] = [:]
        
        for criterion in AnalysisCriterion.allCases {
            scores[criterion] = Double.random(in: 4.0...9.5)
        }
        
        return DetailedSegmentAnalysis(
            segmentId: segment.id,
            scores: scores,
            keyPhrase: extractKeyPhrase(from: segment.content),
            sentiment: AnalysisSentiment.allCases.randomElement()!
        )
    }
    
    private func calculateCurrentScores() -> LiveScore {
        let userSegments = currentDebateTranscript.filter { $0.speaker == .user }
        let opponentSegments = currentDebateTranscript.filter { $0.speaker == .opponent }
        
        let userScore = userSegments.isEmpty ? 5.0 : Double.random(in: 6.0...9.0)
        let opponentScore = opponentSegments.isEmpty ? 5.0 : Double.random(in: 5.5...8.5)
        
        return LiveScore(user: userScore, opponent: opponentScore)
    }
    
    private func calculateMomentum() -> AnalysisMomentum {
        // Analyze recent arguments to determine momentum
        let recentSegments = currentDebateTranscript.suffix(3)
        let userSegments = recentSegments.filter { $0.speaker == .user }.count
        let opponentSegments = recentSegments.filter { $0.speaker == .opponent }.count
        
        if userSegments > opponentSegments {
            return .gaining
        } else if opponentSegments > userSegments {
            return .losing
        } else {
            return .neutral
        }
    }
    
    private func generateCurrentStrengths() -> [String] {
        let strengths = [
            "Strong logical reasoning",
            "Effective use of evidence",
            "Clear communication",
            "Good rebuttal skills",
            "Compelling arguments",
            "Factual accuracy",
            "Emotional appeal",
            "Structured approach"
        ]
        
        return Array(strengths.shuffled().prefix(Int.random(in: 2...4)))
    }
    
    private func generateCurrentImprovements() -> [String] {
        let improvements = [
            "Consider counterarguments more thoroughly",
            "Provide more concrete evidence",
            "Slow down speaking pace",
            "Address opponent's strongest points",
            "Use more varied vocabulary",
            "Improve logical flow",
            "Strengthen opening statements",
            "Better time management"
        ]
        
        return Array(improvements.shuffled().prefix(Int.random(in: 1...3)))
    }
    
    private func calculateWeightedScore(_ scores: [AnalysisCriterion: (user: Double, opponent: Double)], for speaker: Speaker) -> Double {
        var totalWeightedScore = 0.0
        var totalWeight = 0.0
        
        for (criterion, weight) in criteriaWeights {
            if let scoreData = scores[criterion] {
                let score = speaker == .user ? scoreData.user : scoreData.opponent
                totalWeightedScore += score * weight
                totalWeight += weight
            }
        }
        
        return totalWeight > 0 ? totalWeightedScore / totalWeight : 5.0
    }
    
    private func generateArgumentSuggestions(for context: String, position: ArgumentPosition) -> [ArgumentSuggestion] {
        let suggestions = [
            ArgumentSuggestion(
                type: .evidenceBased,
                content: "Consider citing recent studies that support your position",
                relevanceScore: 0.85,
                sources: ["Academic Research Database", "Government Statistics"]
            ),
            ArgumentSuggestion(
                type: .logical,
                content: "Address the logical inconsistency in the opponent's argument",
                relevanceScore: 0.78,
                sources: ["Logic and Reasoning Guide"]
            ),
            ArgumentSuggestion(
                type: .counterArgument,
                content: "Anticipate and preemptively address potential counterarguments",
                relevanceScore: 0.82,
                sources: ["Debate Strategy Manual"]
            )
        ]
        
        return suggestions.shuffled().prefix(Int.random(in: 2...3)).map { $0 }
    }
    
    private func generateFinalStrengths(_ scores: [AnalysisCriterion: (user: Double, opponent: Double)]) -> [String] {
        return [
            "Demonstrated strong analytical thinking throughout the debate",
            "Effectively used evidence to support key arguments",
            "Maintained clear and logical argument structure",
            "Showed good adaptability in responses to opponent"
        ]
    }
    
    private func generateFinalImprovements(_ scores: [AnalysisCriterion: (user: Double, opponent: Double)]) -> [String] {
        return [
            "Consider expanding on counterarguments for more thorough analysis",
            "Work on maintaining consistent energy throughout longer debates",
            "Practice integrating more diverse types of evidence"
        ]
    }
    
    private func generateDetailedFeedback(_ scores: [AnalysisCriterion: (user: Double, opponent: Double)], userScore: Double, opponentScore: Double) -> String {
        return """
        Your debate performance demonstrated strong analytical skills and effective argumentation. 
        
        You scored particularly well in logical consistency and evidence quality, showing your ability to construct well-reasoned arguments. Your communication clarity was also notable, making your points accessible to the audience.
        
        Areas for improvement include developing more robust rebuttals and considering alternative perspectives more thoroughly. Overall, this was a solid performance with clear strategic thinking evident throughout the debate.
        
        Final Score: \(String(format: "%.1f", userScore))/10
        """
    }
    
    private func extractCriteriaScores(_ scores: [AnalysisCriterion: (user: Double, opponent: Double)], for speaker: Speaker) -> [AnalysisCriterion: Double] {
        var criteriaScores: [AnalysisCriterion: Double] = [:]
        
        for (criterion, scoreData) in scores {
            criteriaScores[criterion] = speaker == .user ? scoreData.user : scoreData.opponent
        }
        
        return criteriaScores
    }
    
    private func extractKeyPhrase(from content: String) -> String {
        let words = content.components(separatedBy: .whitespacesAndNewlines)
        let keyWords = words.filter { $0.count > 4 }
        return keyWords.prefix(3).joined(separator: " ")
    }
    
    private func generatePaceFeedback() -> PaceFeedback {
        let wordsPerMinute = Int.random(in: 120...200)
        
        if wordsPerMinute < 140 {
            return PaceFeedback(wpm: wordsPerMinute, recommendation: .speakFaster, note: "Consider speaking slightly faster to maintain engagement")
        } else if wordsPerMinute > 180 {
            return PaceFeedback(wpm: wordsPerMinute, recommendation: .speakSlower, note: "Slow down slightly to ensure clarity")
        } else {
            return PaceFeedback(wpm: wordsPerMinute, recommendation: .maintainPace, note: "Good speaking pace")
        }
    }
    
    private func generateTonalityFeedback() -> TonalityFeedback {
        return TonalityFeedback(
            confidence: Double.random(in: 0.7...0.95),
            assertiveness: Double.random(in: 0.6...0.9),
            clarity: Double.random(in: 0.75...0.95),
            recommendation: "Maintain confident tone while remaining open to different perspectives"
        )
    }
    
    private func generateImprovementSuggestions() -> [String] {
        return [
            "Great point! Consider adding specific examples",
            "Strong argument - now address potential counterpoints",
            "Excellent evidence - tie it back to your main thesis"
        ].shuffled().prefix(1).map { $0 }
    }
}

// MARK: - Supporting Types

struct LiveAnalysis {
    let debateId: String
    var currentScore: LiveScore
    var strengths: [String]
    var improvements: [String]
    var momentum: AnalysisMomentum
    var lastUpdated: Date
}

struct LiveScore {
    var user: Double
    var opponent: Double
}

enum AnalysisMomentum {
    case gaining
    case neutral
    case losing
    
    var description: String {
        switch self {
        case .gaining: return "Gaining momentum"
        case .neutral: return "Steady performance"
        case .losing: return "Need to strengthen arguments"
        }
    }
    
    var color: String {
        switch self {
        case .gaining: return "green"
        case .neutral: return "blue"
        case .losing: return "orange"
        }
    }
}

struct ArgumentScore {
    let id: String
    let speaker: Speaker
    let logicalConsistency: Double
    let evidenceQuality: Double
    let clarity: Double
    let relevance: Double
    let impact: Double
    let timestamp: Date
    
    var overallScore: Double {
        (logicalConsistency + evidenceQuality + clarity + relevance) / 4.0
    }
}

enum AnalysisCriterion: String, Codable, CaseIterable {
    case logicalConsistency
    case evidenceQuality
    case argumentStrength
    case rebuttalEffectiveness
    case communicationClarity
    case factualAccuracy
    
    var displayName: String {
        switch self {
        case .logicalConsistency: return "Logical Consistency"
        case .evidenceQuality: return "Evidence Quality"
        case .argumentStrength: return "Argument Strength"
        case .rebuttalEffectiveness: return "Rebuttal Effectiveness"
        case .communicationClarity: return "Communication Clarity"
        case .factualAccuracy: return "Factual Accuracy"
        }
    }
    
    var description: String {
        switch self {
        case .logicalConsistency:
            return "How well arguments follow logical reasoning"
        case .evidenceQuality:
            return "Quality and relevance of supporting evidence"
        case .argumentStrength:
            return "Overall persuasiveness and impact of arguments"
        case .rebuttalEffectiveness:
            return "Ability to address and counter opponent's points"
        case .communicationClarity:
            return "Clarity and accessibility of communication"
        case .factualAccuracy:
            return "Accuracy of facts and claims presented"
        }
    }
}

struct ArgumentSuggestion {
    let type: SuggestionType
    let content: String
    let relevanceScore: Double
    let sources: [String]
    
    enum SuggestionType {
        case evidenceBased
        case logical
        case counterArgument
        case rhetoricalTechnique
        
        var icon: String {
            switch self {
            case .evidenceBased: return "doc.text"
            case .logical: return "brain"
            case .counterArgument: return "arrow.left.arrow.right"
            case .rhetoricalTechnique: return "quote.bubble"
            }
        }
    }
}

enum ArgumentPosition {
    case supporting
    case opposing
    case neutral
}

struct FactCheckResult {
    let claim: String
    let accuracy: FactualAccuracy
    let confidence: Double
    let sources: [String]
    let explanation: String
}

enum FactualAccuracy: CaseIterable {
    case verified
    case partiallyAccurate
    case disputed
    case `false`
    case insufficientData
    
    var description: String {
        switch self {
        case .verified: return "Verified"
        case .partiallyAccurate: return "Partially Accurate"
        case .disputed: return "Disputed"
        case .`false`: return "False"
        case .insufficientData: return "Insufficient Data"
        }
    }
    
    var color: String {
        switch self {
        case .verified: return "green"
        case .partiallyAccurate: return "yellow"
        case .disputed: return "orange"
        case .`false`: return "red"
        case .insufficientData: return "gray"
        }
    }
}

struct RealTimeFeedback {
    let speakingPace: PaceFeedback
    let tonality: TonalityFeedback
    let argumentStrength: Double
    let suggestions: [String]
}

struct PaceFeedback {
    let wpm: Int
    let recommendation: PaceRecommendation
    let note: String
    
    enum PaceRecommendation {
        case speakFaster
        case speakSlower
        case maintainPace
    }
}

struct TonalityFeedback {
    let confidence: Double
    let assertiveness: Double
    let clarity: Double
    let recommendation: String
}

struct DebateSegment {
    let id: String
    let speaker: Speaker
    let content: String
    let timestamp: Date
    let duration: TimeInterval
}

struct ArgumentAnalysisResult {
    let logicalConsistency: Double
    let evidenceQuality: Double
    let clarity: Double
    let relevance: Double
    let overallImpact: Double
}

struct DetailedSegmentAnalysis {
    let segmentId: String
    let scores: [AnalysisCriterion: Double]
    let keyPhrase: String
    let sentiment: AnalysisSentiment
}

enum AnalysisSentiment: CaseIterable {
    case positive
    case neutral
    case negative
    case passionate
    case analytical
}

// MARK: - Mock Network Service

class AINetworkService {
    func analyzeDebateTranscript(_ transcript: [DebateSegment]) async throws -> AIAnalysis {
        // Simulate network call to AI service
        try await Task.sleep(nanoseconds: 2_000_000_000)
        
        // Return mock analysis
        return AIAnalysis(
            overallScore: Double.random(in: 6.5...9.2),
            result: [.won, .lost, .draw].randomElement()!,
            strengths: ["Strong evidence", "Clear logic"],
            improvements: ["Consider counterarguments"],
            detailedFeedback: "Comprehensive analysis..."
        )
    }
    
    func factCheck(_ claim: String) async throws -> FactCheckResult {
        try await Task.sleep(nanoseconds: 1_000_000_000)
        
        return FactCheckResult(
            claim: claim,
            accuracy: .verified,
            confidence: 0.85,
            sources: ["Source 1", "Source 2"],
            explanation: "Fact check explanation..."
        )
    }
}

// Preview removed as AIJudgeService is not a View