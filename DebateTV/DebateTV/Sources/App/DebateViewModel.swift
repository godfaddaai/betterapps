import SwiftUI
import AVFoundation


@Observable
final class DebateViewModel {
    var phase: DebatePhase = .idle
    var currentTopic: DebateTopic?
    var opponentName: String = ""
    var timeRemaining: Int = 180
    var result: DebateResult?
    var matchmakingProgress: Double = 0
    var countdownValue: Int = 3
    var selectedCategory: DebateCategory?


    var isMuted: Bool = false
    var isCameraOff: Bool = false
    var isOpponentSpeaking: Bool = false
    var isUserSpeaking: Bool = false
    var liveTranscript: [TranscriptLine] = []
    var opponentMuted: Bool = false


    let captureSession = AVCaptureSession()
    private var isCaptureConfigured: Bool = false


    private let debateService: DebateService
    private let judgeService: AIJudgeService
    private var timerTask: Task<Void, Never>?
    private var matchmakingTask: Task<Void, Never>?
    private var speakingSimTask: Task<Void, Never>?


    init(debateService: DebateService, judgeService: AIJudgeService) {
        self.debateService = debateService
        self.judgeService = judgeService
    }


    func startMatchmaking() {
        phase = .matchmaking
        Task {
            try? await Task.sleep(for: .seconds(2))
            phase = .debate
        }
    }
    
    func startWithTopic(_ topic: DebateTopic) {
        self.currentTopic = topic
        phase = .debate
    }
    
    func submitArguments() {
        Task {
            let res = await judgeService.judgeDebate(topic: currentTopic ?? DebateTopic(title: "Unknown", category: .culture, summary: ""), userArguments: [], opponentArguments: [])
            self.result = res
            self.phase = .verdict
        }
    }
    
    var debateResult: DebateResult? { return result }
    var topic: DebateTopic? { return currentTopic }
}

enum DebatePhase {
    case idle
    case matchmaking
    case debate
    case verdict
}

struct TranscriptLine: Identifiable {
    let id = UUID()
    let text: String
}