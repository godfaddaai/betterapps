import SwiftUI
import AVFoundation
import Observation

enum DebatePhase: Sendable, Equatable {
    case idle
    case matchmaking
    case topicReveal
    case countdown
    case debating
    case judging
    case verdict
}

struct TranscriptLine: Identifiable, Equatable {
    let id = UUID()
    let speaker: String
    let text: String
    let timestamp: Date
}

@Observable
final class DebateViewModel {
    var phase: DebatePhase = .idle
    var currentTopic: DebateTopic?
    var opponentName: String = ""
    var timeRemaining: Int = 180
    var result: DebateResultStruct?
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
        matchmakingProgress = 0
        opponentName = debateService.randomOpponentName
        
        matchmakingTask = Task {
            for i in 1...20 {
                try? await Task.sleep(for: .milliseconds(150))
                matchmakingProgress = Double(i) / 20.0
            }
            if currentTopic == nil {
                currentTopic = debateService.getRandomTopic(for: selectedCategory)
            }
            phase = .topicReveal
            
            try? await Task.sleep(for: .seconds(3))
            phase = .countdown
            await runCountdown()
        }
    }
    
    func startWithTopic(_ topic: DebateTopic) {
        currentTopic = topic
        startMatchmaking()
    }
    
    private func runCountdown() async {
        countdownValue = 3
        for i in (1...3).reversed() {
            countdownValue = i
            try? await Task.sleep(for: .seconds(1))
        }
        startDebate()
    }
    
    func startDebate() {
        phase = .debating
        timeRemaining = 180
        configureCapture()
        startTimer()
        simulateSpeaking()
        
        // Add initial transcript
        liveTranscript.append(TranscriptLine(
            speaker: "System",
            text: "Debate started. Topic: \(currentTopic?.title ?? "")",
            timestamp: Date()
        ))
    }
    
    private func startTimer() {
        timerTask?.cancel()
        timerTask = Task {
            while timeRemaining > 0 {
                try? await Task.sleep(for: .seconds(1))
                timeRemaining -= 1
                
                if timeRemaining == 0 {
                    await endDebate()
                }
            }
        }
    }
    
    private func simulateSpeaking() {
        speakingSimTask = Task {
            while phase == .debating {
                try? await Task.sleep(for: .seconds(Double.random(in: 3...8)))
                isOpponentSpeaking = Bool.random()
                
                if isOpponentSpeaking {
                    let sampleArguments = [
                        "I believe we need to consider the broader implications...",
                        "The evidence clearly shows that...",
                        "Let me address your previous point...",
                        "That's an interesting perspective, however...",
                        "We cannot ignore the fact that..."
                    ]
                    
                    liveTranscript.append(TranscriptLine(
                        speaker: opponentName,
                        text: sampleArguments.randomElement() ?? "",
                        timestamp: Date()
                    ))
                }
                
                try? await Task.sleep(for: .seconds(Double.random(in: 2...5)))
                isOpponentSpeaking = false
            }
        }
    }
    
    func toggleMute() {
        isMuted.toggle()
    }
    
    func toggleCamera() {
        isCameraOff.toggle()
    }
    
    func speak() {
        guard !isOpponentSpeaking else { return }
        isUserSpeaking = true
        
        Task {
            try? await Task.sleep(for: .seconds(3))
            isUserSpeaking = false
            
            liveTranscript.append(TranscriptLine(
                speaker: "You",
                text: "That's a valid point, but I think we should also consider...",
                timestamp: Date()
            ))
        }
    }
    
    func endDebateEarly() {
        Task {
            await endDebate()
        }
    }
    
    private func endDebate() async {
        phase = .judging
        timerTask?.cancel()
        speakingSimTask?.cancel()
        
        // Simulate judging
        try? await Task.sleep(for: .seconds(3))
        
        // Generate result
        let outcomes: [DebateOutcome] = [.win, .loss, .draw]
        let outcome = outcomes.randomElement() ?? .draw
        
        result = DebateResultStruct(
            id: UUID().uuidString,
            topic: currentTopic ?? DebateTopic(
                id: "1",
                title: "Unknown Topic",
                description: "",
                category: .technology,
                difficulty: .intermediate
            ),
            userScore: Int.random(in: 65...95),
            opponentScore: Int.random(in: 65...95),
            outcome: outcome,
            reasoning: "Both debaters presented compelling arguments with strong evidence...",
            strongestArgument: "Your point about sustainability was particularly well-articulated.",
            opponentStrongestArgument: "The opponent's economic analysis was thorough and convincing.",
            fallaciesSpotted: ["Appeal to authority", "Straw man"],
            date: Date(),
            opponentName: opponentName
        )
        
        // Convert DebateResultStruct to DebateSession for history
        if let debateResult = result, let topic = currentTopic {
            let session = DebateSession(
                id: debateResult.id,
                topic: topic.title,
                opponent: opponentName,
                result: debateResult.outcome == .win ? .won : debateResult.outcome == .loss ? .lost : .draw,
                aiScore: Double(debateResult.userScore),
                duration: "5 min",
                createdAt: Date(),
                keyArguments: [debateResult.strongestArgument],
                category: topic.category,
                difficulty: topic.difficultyLevel
            )
            debateService.addDebateToHistory(session)
        }
        phase = .verdict
    }
    
    func reset() {
        phase = .idle
        currentTopic = nil
        opponentName = ""
        timeRemaining = 180
        result = nil
        matchmakingProgress = 0
        countdownValue = 3
        selectedCategory = nil
        isMuted = false
        isCameraOff = false
        isOpponentSpeaking = false
        isUserSpeaking = false
        liveTranscript = []
        timerTask?.cancel()
        matchmakingTask?.cancel()
        speakingSimTask?.cancel()
    }
    
    private func configureCapture() {
        guard !isCaptureConfigured else { return }
        
        captureSession.beginConfiguration()
        
        // Add video input
        if let videoDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front),
           let videoInput = try? AVCaptureDeviceInput(device: videoDevice),
           captureSession.canAddInput(videoInput) {
            captureSession.addInput(videoInput)
        }
        
        // Add audio input
        if let audioDevice = AVCaptureDevice.default(for: .audio),
           let audioInput = try? AVCaptureDeviceInput(device: audioDevice),
           captureSession.canAddInput(audioInput) {
            captureSession.addInput(audioInput)
        }
        
        captureSession.commitConfiguration()
        
        Task {
            captureSession.startRunning()
        }
        
        isCaptureConfigured = true
    }
    
    deinit {
        timerTask?.cancel()
        matchmakingTask?.cancel()
        speakingSimTask?.cancel()
        captureSession.stopRunning()
    }
}