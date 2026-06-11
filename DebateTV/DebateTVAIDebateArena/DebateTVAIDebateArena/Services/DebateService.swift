import Foundation
import Combine
import AVFoundation
import UIKit

class DebateService: ObservableObject {
    // MARK: - Published Properties
    @Published var connectionStatus: ConnectionStatus = .disconnected
    @Published var isConnected = false
    @Published var currentOpponent: DebateOpponent?
    @Published var streamQuality: StreamQuality = .medium
    @Published var profile: UserProfile = UserProfile(
        username: "DebateUser",
        avatarEmoji: "🎭",
        rank: .bronze,
        wins: 5,
        losses: 3,
        draws: 2,
        streak: 2,
        bestStreak: 4,
        totalDebates: 10,
        averageScore: 75.5,
        joinDate: Date(),
        hasCompletedOnboarding: true
    )
    
    // MARK: - Publishers for real-time updates
    let remoteVideoFramePublisher = PassthroughSubject<UIImage?, Never>()
    let remoteMutedPublisher = PassthroughSubject<Bool, Never>()
    let viewerCountPublisher = PassthroughSubject<Int, Never>()
    let messagePublisher = PassthroughSubject<DebateMessage, Never>()
    let reactionPublisher = PassthroughSubject<ReactionType, Never>()
    
    // MARK: - Private Properties
    private let networkManager = NetworkManager()
    private let webSocketManager = WebSocketManager()
    private let streamingManager = StreamingManager()
    private var cancellables = Set<AnyCancellable>()
    
    // Mock data for simulation
    private var mockTimer: Timer?
    private var mockViewerCount = 50
    @Published var debateHistory: [DebateSession] = []
    
    // MARK: - Initialization
    
    init() {
        setupSubscriptions()
        // Restore locally persisted history (newest first) so stats + recent matches survive relaunch
        debateHistory = ProfileStore.loadRecentSessions()
    }
    
    deinit {
        disconnect()
    }
    
    // MARK: - Public Methods
    
    var randomOpponentName: String {
        ["DebateMaster", "LogicPro", "ArgumentAce", "RhetoricKing", "ReasonRuler", "DiscourseChamp"].randomElement()!
    }
    
    func getRandomTopic(for category: DebateCategory?) -> DebateTopic {
        let topics = [
            DebateTopic(
                id: UUID().uuidString,
                title: "Should AI replace human decision-making in critical sectors?",
                description: "Explore the implications of AI in healthcare, justice, and governance",
                category: .technology,
                difficulty: 3
            ),
            DebateTopic(
                id: UUID().uuidString,
                title: "Is social media doing more harm than good?",
                description: "Examine the impact of social platforms on society and mental health",
                category: .social,
                difficulty: 2
            ),
            DebateTopic(
                id: UUID().uuidString,
                title: "Should space exploration be prioritized over Earth's problems?",
                description: "Debate the allocation of resources between space and terrestrial challenges",
                category: .science,
                difficulty: 4
            ),
            DebateTopic(
                id: UUID().uuidString,
                title: "Is universal basic income the future of economics?",
                description: "Discuss the viability and impact of UBI on society",
                category: .politics,
                difficulty: 3
            ),
            DebateTopic(
                id: UUID().uuidString,
                title: "Should genetic engineering be used to enhance human capabilities?",
                description: "Explore the ethical implications of human genetic modification",
                category: .philosophy,
                difficulty: 5
            )
        ]
        
        if let category = category {
            let filtered = topics.filter { $0.category == category }
            return filtered.randomElement() ?? topics.randomElement()!
        } else {
            return topics.randomElement()!
        }
    }
    
    func addDebateToHistory(_ session: DebateSession) {
        debateHistory.insert(session, at: 0) // newest first
        ProfileStore.record(session) // persist stats + recents locally (UserDefaults)
    }
    
    func connect() {
        connectionStatus = .connecting
        
        // Simulate connection process
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            self.connectionStatus = .connected
            self.isConnected = true
            self.startMockUpdates()
        }
    }
    
    func disconnect() {
        connectionStatus = .disconnected
        isConnected = false
        stopMockUpdates()
        webSocketManager.disconnect()
        streamingManager.stopStreaming()
    }
    
    func joinDebateRoom(roomId: String) async throws -> DebateRoom {
        guard isConnected else {
            throw DebateServiceError.notConnected
        }
        
        // Simulate API call to join room
        try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second delay
        
        let room = DebateRoom(
            id: roomId,
            topic: "Sample Debate Topic",
            participants: [],
            viewerCount: mockViewerCount,
            status: .active
        )
        
        return room
    }
    
    func findOpponent(for topic: DebateTopic, difficulty: DifficultyLevel) async throws -> DebateOpponent {
        guard isConnected else {
            throw DebateServiceError.notConnected
        }
        
        // Simulate matchmaking delay
        try await Task.sleep(nanoseconds: UInt64.random(in: 2_000_000_000...5_000_000_000))
        
        let opponent = DebateOpponent(
            id: UUID().uuidString,
            displayName: ["Alex", "Jordan", "Taylor", "Casey", "Riley"].randomElement()!,
            username: "user\(Int.random(in: 1000...9999))",
            profileImageURL: nil,
            winRate: Int.random(in: 60...95),
            totalDebates: Int.random(in: 10...100),
            isOnline: true,
            skillLevel: difficulty
        )
        
        currentOpponent = opponent
        return opponent
    }
    
    func startStream(for debate: DebateSession) async throws {
        guard isConnected else {
            throw DebateServiceError.notConnected
        }
        
        try await streamingManager.startStreaming()
        
        // Update stream quality based on connection
        streamQuality = determineOptimalQuality()
    }
    
    func stopStream() {
        streamingManager.stopStreaming()
    }
    
    func sendMessage(_ message: String, type: MessageType) {
        let debateMessage = DebateMessage(
            id: UUID().uuidString,
            senderId: "current_user",
            senderName: "You",
            content: message,
            type: type,
            timestamp: Date()
        )
        
        messagePublisher.send(debateMessage)
        
        // In real implementation, send to WebSocket
        webSocketManager.sendMessage(debateMessage)
    }
    
    func sendReaction(_ reaction: ReactionType) {
        reactionPublisher.send(reaction)
        
        // In real implementation, send to WebSocket
        webSocketManager.sendReaction(reaction)
    }
    
    func toggleAudio(_ enabled: Bool) {
        streamingManager.toggleAudio(enabled)
        
        // Notify other participants
        let message = DebateMessage(
            id: UUID().uuidString,
            senderId: "system",
            senderName: "System",
            content: enabled ? "Microphone enabled" : "Microphone muted",
            type: .system,
            timestamp: Date()
        )
        
        messagePublisher.send(message)
    }
    
    func toggleVideo(_ enabled: Bool) {
        streamingManager.toggleVideo(enabled)
        
        // Notify other participants
        let message = DebateMessage(
            id: UUID().uuidString,
            senderId: "system",
            senderName: "System",
            content: enabled ? "Camera enabled" : "Camera disabled",
            type: .system,
            timestamp: Date()
        )
        
        messagePublisher.send(message)
    }
    
    func reportUser(_ userId: String, reason: ReportReason) async throws {
        guard isConnected else {
            throw DebateServiceError.notConnected
        }
        
        // Simulate API call to report user
        try await networkManager.reportUser(userId: userId, reason: reason)
    }
    
    func blockUser(_ userId: String) async throws {
        guard isConnected else {
            throw DebateServiceError.notConnected
        }
        
        // Simulate API call to block user
        try await networkManager.blockUser(userId: userId)
    }
    
    // MARK: - Private Methods
    
    private func setupSubscriptions() {
        // Subscribe to network status changes
        networkManager.connectionStatusPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] status in
                self?.handleNetworkStatusChange(status)
            }
            .store(in: &cancellables)
        
        // Subscribe to WebSocket messages
        webSocketManager.messagePublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] message in
                self?.handleIncomingMessage(message)
            }
            .store(in: &cancellables)
    }
    
    private func startMockUpdates() {
        mockTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { [weak self] _ in
            self?.generateMockUpdates()
        }
    }
    
    private func stopMockUpdates() {
        mockTimer?.invalidate()
        mockTimer = nil
    }
    
    private func generateMockUpdates() {
        // Simulate viewer count changes
        mockViewerCount += Int.random(in: -5...10)
        mockViewerCount = max(10, mockViewerCount)
        viewerCountPublisher.send(mockViewerCount)
        
        // Simulate remote video frame (in real app, this would come from WebRTC)
        if Bool.random() {
            let mockFrame = generateMockVideoFrame()
            remoteVideoFramePublisher.send(mockFrame)
        }
        
        // Simulate opponent mute status changes
        if Int.random(in: 1...10) == 1 {
            remoteMutedPublisher.send(Bool.random())
        }
        
        // Simulate random reactions
        if Int.random(in: 1...8) == 1 {
            let reaction = ReactionType.allCases.randomElement()!
            reactionPublisher.send(reaction)
        }
    }
    
    private func generateMockVideoFrame() -> UIImage? {
        // Generate a simple colored rectangle as mock video frame
        let size = CGSize(width: 320, height: 240)
        let renderer = UIGraphicsImageRenderer(size: size)
        
        return renderer.image { context in
            let colors: [UIColor] = [.blue, .green, .purple, .orange]
            let color = colors.randomElement()!
            
            context.cgContext.setFillColor(color.cgColor)
            context.cgContext.fill(CGRect(origin: .zero, size: size))
            
            // Add some text to make it look more like a video frame
            let text = "Mock Video"
            let attributes: [NSAttributedString.Key: Any] = [
                .foregroundColor: UIColor.white,
                .font: UIFont.systemFont(ofSize: 20)
            ]
            
            let textSize = text.size(withAttributes: attributes)
            let textRect = CGRect(
                x: (size.width - textSize.width) / 2,
                y: (size.height - textSize.height) / 2,
                width: textSize.width,
                height: textSize.height
            )
            
            text.draw(in: textRect, withAttributes: attributes)
        }
    }
    
    private func handleNetworkStatusChange(_ status: NetworkStatus) {
        switch status {
        case .connected:
            if connectionStatus == .connecting {
                connectionStatus = .connected
                isConnected = true
            }
        case .disconnected:
            connectionStatus = .disconnected
            isConnected = false
        case .poor:
            // Adjust stream quality for poor connection
            streamQuality = .low
        }
    }
    
    private func handleIncomingMessage(_ message: DebateMessage) {
        messagePublisher.send(message)
        
        // Handle special message types
        switch message.type {
        case .reaction:
            if let reactionString = message.content.components(separatedBy: ":").last,
               let reaction = ReactionType.allCases.first(where: { $0.rawValue == reactionString }) {
                reactionPublisher.send(reaction)
            }
        case .system:
            // Handle system messages (user joined/left, etc.)
            break
        case .chat, .argument:
            // Regular messages, already sent to publisher
            break
        }
    }
    
    private func determineOptimalQuality() -> StreamQuality {
        switch networkManager.currentConnectionQuality {
        case .excellent:
            return .high
        case .good:
            return .medium
        case .fair:
            return .low
        case .poor:
            return .low
        }
    }
}

// MARK: - Supporting Types

enum ConnectionStatus {
    case disconnected
    case connecting
    case connected
    case reconnecting
    case failed
    
    var description: String {
        switch self {
        case .disconnected: return "Disconnected"
        case .connecting: return "Connecting..."
        case .connected: return "Connected"
        case .reconnecting: return "Reconnecting..."
        case .failed: return "Connection Failed"
        }
    }
}

// StreamQuality is defined in DebateModels.swift

enum MessageType {
    case chat
    case argument
    case reaction
    case system
}

enum ReportReason: CaseIterable {
    case harassment
    case inappropriateContent
    case spam
    case cheating
    case other
    
    var description: String {
        switch self {
        case .harassment: return "Harassment or bullying"
        case .inappropriateContent: return "Inappropriate content"
        case .spam: return "Spam or repetitive content"
        case .cheating: return "Cheating or unfair behavior"
        case .other: return "Other"
        }
    }
}

enum DebateServiceError: Error, LocalizedError {
    case notConnected
    case connectionFailed
    case streamingError(String)
    case matchmakingFailed
    case roomNotFound
    case userBlocked
    case networkError(String)
    
    var errorDescription: String? {
        switch self {
        case .notConnected:
            return "Not connected to debate service"
        case .connectionFailed:
            return "Failed to connect to debate service"
        case .streamingError(let message):
            return "Streaming error: \(message)"
        case .matchmakingFailed:
            return "Failed to find an opponent"
        case .roomNotFound:
            return "Debate room not found"
        case .userBlocked:
            return "User is blocked"
        case .networkError(let message):
            return "Network error: \(message)"
        }
    }
}

struct DebateRoom {
    let id: String
    let topic: String
    let participants: [String]
    let viewerCount: Int
    let status: DebateRoomStatus
}

enum DebateRoomStatus {
    case waiting
    case active
    case paused
    case ended
}

struct DebateMessage: Codable, Identifiable {
    let id: String
    let senderId: String
    let senderName: String
    let content: String
    let type: MessageType
    let timestamp: Date
}

// Extend MessageType to be Codable
extension MessageType: Codable {
    enum CodingKeys: String, CodingKey {
        case rawValue
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawValue = try container.decode(String.self)
        
        switch rawValue {
        case "chat": self = .chat
        case "argument": self = .argument
        case "reaction": self = .reaction
        case "system": self = .system
        default: self = .chat
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        
        let rawValue: String
        switch self {
        case .chat: rawValue = "chat"
        case .argument: rawValue = "argument"
        case .reaction: rawValue = "reaction"
        case .system: rawValue = "system"
        }
        
        try container.encode(rawValue)
    }
}

// MARK: - Mock Network Manager

class NetworkManager {
    let connectionStatusPublisher = PassthroughSubject<NetworkStatus, Never>()
    
    var currentConnectionQuality: ConnectionQuality = .good
    
    init() {
        // Simulate network quality changes
        Timer.scheduledTimer(withTimeInterval: 10.0, repeats: true) { _ in
            self.currentConnectionQuality = ConnectionQuality.allCases.randomElement()!
        }
    }
    
    func reportUser(userId: String, reason: ReportReason) async throws {
        // Simulate API call delay
        try await Task.sleep(nanoseconds: 1_000_000_000)
        
        // Simulate occasional failures
        if Int.random(in: 1...10) == 1 {
            throw DebateServiceError.networkError("Failed to report user")
        }
    }
    
    func blockUser(userId: String) async throws {
        // Simulate API call delay
        try await Task.sleep(nanoseconds: 1_000_000_000)
        
        // Simulate occasional failures
        if Int.random(in: 1...10) == 1 {
            throw DebateServiceError.networkError("Failed to block user")
        }
    }
}

enum NetworkStatus {
    case connected
    case disconnected
    case poor
}

enum ConnectionQuality: CaseIterable {
    case excellent
    case good
    case fair
    case poor
}

// MARK: - Mock WebSocket Manager

class WebSocketManager {
    let messagePublisher = PassthroughSubject<DebateMessage, Never>()
    
    private var isConnected = false
    
    func connect() {
        isConnected = true
    }
    
    func disconnect() {
        isConnected = false
    }
    
    func sendMessage(_ message: DebateMessage) {
        guard isConnected else { return }
        
        // In real implementation, send to WebSocket server
        print("Sending message: \(message.content)")
    }
    
    func sendReaction(_ reaction: ReactionType) {
        guard isConnected else { return }
        
        // In real implementation, send to WebSocket server
        print("Sending reaction: \(reaction.rawValue)")
    }
}

// MARK: - Mock Streaming Manager

class StreamingManager {
    private var isStreaming = false
    private var isAudioEnabled = true
    private var isVideoEnabled = true
    
    func startStreaming() async throws {
        // Simulate streaming setup delay
        try await Task.sleep(nanoseconds: 1_000_000_000)
        
        isStreaming = true
        print("Streaming started")
    }
    
    func stopStreaming() {
        isStreaming = false
        print("Streaming stopped")
    }
    
    func toggleAudio(_ enabled: Bool) {
        isAudioEnabled = enabled
        print("Audio \(enabled ? "enabled" : "disabled")")
    }
    
    func toggleVideo(_ enabled: Bool) {
        isVideoEnabled = enabled
        print("Video \(enabled ? "enabled" : "disabled")")
    }
}

// Preview removed as DebateService is not a View