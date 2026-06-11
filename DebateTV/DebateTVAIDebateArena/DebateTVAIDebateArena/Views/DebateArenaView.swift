import SwiftUI
import AVFoundation

struct DebateArenaView: View {
    @Bindable var viewModel: DebateViewModel
    @State private var showingTranscript: Bool = false
    @State private var currentSpeakerGlow: Bool = false
    @State private var timerPulse: Bool = false
    
    var body: some View {
        ZStack {
            // Broadcast production background
            Color.black
            AnimatedMeshBackground()
                .opacity(0.3)
            
            VStack(spacing: 0) {
                // Top bar with timer
                topBar
                
                // Video feeds
                videoFeeds
                    .padding(.top, 12)
                
                // Control bar
                controlBar
                    .padding(.top, 16)
                
                // Live transcript
                if showingTranscript {
                    liveTranscript
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            
            // Overlay effects
            VignetteOverlay(intensity: 0.4)
            ScanlineOverlay()
                .opacity(0.3)
                .allowsHitTesting(false)
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 1).repeatForever(autoreverses: true)) {
                currentSpeakerGlow = true
            }
            
            withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                timerPulse = true
            }
        }
    }
    
    private var topBar: some View {
        VStack(spacing: 0) {
            // Broadcast header
            HStack {
                HStack(spacing: 6) {
                    Circle()
                        .fill(BroadcastTheme.broadcastRed)
                        .frame(width: 7, height: 7)
                        .scaleEffect(timerPulse ? 1.2 : 1.0)
                    
                    Text("LIVE DEBATE")
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .foregroundStyle(BroadcastTheme.broadcastRed)
                        .tracking(2)
                }
                
                Spacer()
                
                // Topic title
                if let topic = viewModel.currentTopic {
                    Text(topic.title)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.white.opacity(0.5))
                        .lineLimit(1)
                        .frame(maxWidth: 150)
                }
                
                Spacer()
                
                // Timer
                TimerDisplay(seconds: viewModel.timeRemaining, isPulsing: viewModel.timeRemaining < 30)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 16)
            .background(
                LinearGradient(
                    colors: [
                        Color.black.opacity(0.9),
                        Color.black.opacity(0.7)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            
            // Separator line
            Rectangle()
                .fill(
                    LinearGradient(
                        colors: [
                            .clear,
                            BroadcastTheme.broadcastRed.opacity(0.3),
                            .clear
                        ],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .frame(height: 1)
        }
    }
    
    private var videoFeeds: some View {
        GeometryReader { geo in
            HStack(spacing: 12) {
                // User video
                VideoFeedView(
                    name: "YOU",
                    isSpeaking: viewModel.isUserSpeaking,
                    isMuted: viewModel.isMuted,
                    isCameraOff: viewModel.isCameraOff,
                    color: BroadcastTheme.neonCyan,
                    captureSession: viewModel.captureSession,
                    isUser: true
                )
                .frame(width: (geo.size.width - 12) / 2)
                
                // Opponent video
                VideoFeedView(
                    name: viewModel.opponentName,
                    isSpeaking: viewModel.isOpponentSpeaking,
                    isMuted: viewModel.opponentMuted,
                    isCameraOff: false,
                    color: BroadcastTheme.stageAmber,
                    captureSession: nil,
                    isUser: false
                )
                .frame(width: (geo.size.width - 12) / 2)
            }
            .padding(.horizontal, 12)
        }
    }
    
    private var controlBar: some View {
        VStack(spacing: 12) {
            // Main controls
            HStack(spacing: 24) {
                // Mute button
                ControlButton(
                    icon: viewModel.isMuted ? "mic.slash.fill" : "mic.fill",
                    isActive: !viewModel.isMuted,
                    color: BroadcastTheme.neonCyan
                ) {
                    viewModel.toggleMute()
                }
                
                // Camera button
                ControlButton(
                    icon: viewModel.isCameraOff ? "video.slash.fill" : "video.fill",
                    isActive: !viewModel.isCameraOff,
                    color: BroadcastTheme.neonCyan
                ) {
                    viewModel.toggleCamera()
                }
                
                // Speak button (main action)
                Button {
                    viewModel.speak()
                } label: {
                    ZStack {
                        Circle()
                            .fill(
                                LinearGradient(
                                    colors: [
                                        BroadcastTheme.broadcastRed,
                                        BroadcastTheme.broadcastRed.opacity(0.7)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 72, height: 72)
                        
                        if viewModel.isUserSpeaking {
                            Circle()
                                .stroke(BroadcastTheme.broadcastRed, lineWidth: 3)
                                .frame(width: 72, height: 72)
                                .scaleEffect(currentSpeakerGlow ? 1.2 : 1.0)
                                .opacity(currentSpeakerGlow ? 0 : 1)
                        }
                        
                        VStack(spacing: 4) {
                            Image(systemName: "mic.fill")
                                .font(.system(size: 22))
                            Text("SPEAK")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .tracking(1)
                        }
                        .foregroundStyle(.white)
                    }
                }
                .disabled(viewModel.isOpponentSpeaking)
                .opacity(viewModel.isOpponentSpeaking ? 0.5 : 1.0)
                
                // Transcript button
                ControlButton(
                    icon: "text.bubble.fill",
                    isActive: showingTranscript,
                    color: BroadcastTheme.neonCyan
                ) {
                    withAnimation(.spring(response: 0.3)) {
                        showingTranscript.toggle()
                    }
                }
                
                // End debate button
                ControlButton(
                    icon: "xmark.circle.fill",
                    isActive: false,
                    color: BroadcastTheme.error
                ) {
                    viewModel.endDebateEarly()
                }
            }
            
            // Speaking indicator
            if viewModel.isOpponentSpeaking {
                HStack(spacing: 8) {
                    Circle()
                        .fill(BroadcastTheme.stageAmber)
                        .frame(width: 6, height: 6)
                        .scaleEffect(currentSpeakerGlow ? 1.3 : 1.0)
                    
                    Text("\(viewModel.opponentName.uppercased()) IS SPEAKING")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(BroadcastTheme.stageAmber)
                        .tracking(1)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 6)
                .background(BroadcastTheme.stageAmber.opacity(0.1))
                .clipShape(Capsule())
                .overlay(
                    Capsule()
                        .stroke(BroadcastTheme.stageAmber.opacity(0.3), lineWidth: 1)
                )
                .transition(.scale.combined(with: .opacity))
            }
        }
        .padding(.horizontal, 20)
    }
    
    private var liveTranscript: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("LIVE TRANSCRIPT")
                    .font(.system(size: 10, weight: .black, design: .monospaced))
                    .foregroundStyle(.white.opacity(0.5))
                    .tracking(2)
                
                Spacer()
                
                Button {
                    withAnimation(.spring(response: 0.3)) {
                        showingTranscript = false
                    }
                } label: {
                    Image(systemName: "chevron.down")
                        .font(.system(size: 12))
                        .foregroundStyle(.white.opacity(0.5))
                }
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(viewModel.liveTranscript) { line in
                            TranscriptLineView(line: line)
                                .id(line.id)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 16)
                }
                .frame(height: 180)
                .onChange(of: viewModel.liveTranscript) { _, _ in
                    withAnimation {
                        proxy.scrollTo(viewModel.liveTranscript.last?.id, anchor: .bottom)
                    }
                }
            }
        }
        .background(Color.black.opacity(0.8))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(.white.opacity(0.1), lineWidth: 0.5)
        )
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }
}

struct VideoFeedView: View {
    let name: String
    let isSpeaking: Bool
    let isMuted: Bool
    let isCameraOff: Bool
    let color: Color
    let captureSession: AVCaptureSession?
    let isUser: Bool
    
    var body: some View {
        ZStack {
            // Video background
            if let session = captureSession, !isCameraOff && isUser {
                CameraPreview(session: session)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            } else if !isUser {
                // Simulated opponent video
                RoundedRectangle(cornerRadius: 12)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color(red: 0.15, green: 0.12, blue: 0.18),
                                Color(red: 0.08, green: 0.06, blue: 0.1)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay(
                        Image(systemName: "person.fill")
                            .font(.system(size: 48))
                            .foregroundStyle(.white.opacity(0.2))
                    )
            } else {
                // Camera off state
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.black.opacity(0.8))
                    .overlay(
                        VStack(spacing: 8) {
                            Image(systemName: "video.slash")
                                .font(.system(size: 32))
                            Text("Camera Off")
                                .font(.system(.caption, weight: .medium))
                        }
                        .foregroundStyle(.white.opacity(0.3))
                    )
            }
            
            // Speaking indicator border
            if isSpeaking {
                RoundedRectangle(cornerRadius: 12)
                    .stroke(color, lineWidth: 3)
                    .shadow(color: color, radius: 8)
            } else {
                RoundedRectangle(cornerRadius: 12)
                    .stroke(.white.opacity(0.1), lineWidth: 0.5)
            }
            
            // Name label
            VStack {
                HStack {
                    HStack(spacing: 6) {
                        if isSpeaking {
                            Image(systemName: "waveform")
                                .font(.system(size: 10))
                                .foregroundStyle(color)
                        }
                        
                        Text(name.uppercased())
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundStyle(.white)
                            .tracking(1)
                        
                        if isMuted {
                            Image(systemName: "mic.slash.fill")
                                .font(.system(size: 9))
                                .foregroundStyle(.white.opacity(0.5))
                        }
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.black.opacity(0.7))
                    .clipShape(Capsule())
                    
                    Spacer()
                }
                .padding(10)
                
                Spacer()
            }
        }
        .aspectRatio(9/16, contentMode: .fit)
    }
}

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        previewLayer.connection?.automaticallyAdjustsVideoMirroring = false
        previewLayer.connection?.isVideoMirrored = true
        
        view.layer.addSublayer(previewLayer)
        
        DispatchQueue.main.async {
            previewLayer.frame = view.bounds
        }
        
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {
        if let layer = uiView.layer.sublayers?.first as? AVCaptureVideoPreviewLayer {
            DispatchQueue.main.async {
                layer.frame = uiView.bounds
            }
        }
    }
}

struct ControlButton: View {
    let icon: String
    let isActive: Bool
    let color: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            ZStack {
                Circle()
                    .fill(isActive ? color.opacity(0.15) : .white.opacity(0.05))
                    .frame(width: 48, height: 48)
                
                Circle()
                    .stroke(isActive ? color.opacity(0.5) : .white.opacity(0.2), lineWidth: 1)
                    .frame(width: 48, height: 48)
                
                Image(systemName: icon)
                    .font(.system(size: 20))
                    .foregroundStyle(isActive ? color : .white.opacity(0.5))
            }
        }
    }
}

struct TimerDisplay: View {
    let seconds: Int
    let isPulsing: Bool
    
    private var timeString: String {
        let minutes = seconds / 60
        let remainingSeconds = seconds % 60
        return String(format: "%02d:%02d", minutes, remainingSeconds)
    }
    
    private var timerColor: Color {
        if seconds < 10 { return BroadcastTheme.error }
        if seconds < 30 { return BroadcastTheme.warning }
        return BroadcastTheme.success
    }
    
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "timer")
                .font(.system(size: 12))
            
            Text(timeString)
                .font(.system(size: 14, weight: .bold, design: .monospaced))
        }
        .foregroundStyle(timerColor)
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(timerColor.opacity(0.15))
        .clipShape(Capsule())
        .overlay(
            Capsule()
                .stroke(timerColor.opacity(0.3), lineWidth: 1)
        )
        .scaleEffect(isPulsing && seconds < 10 ? 1.05 : 1.0)
        .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: isPulsing)
    }
}

struct TranscriptLineView: View {
    let line: TranscriptLine
    
    private var speakerColor: Color {
        switch line.speaker {
        case "You": return BroadcastTheme.neonCyan
        case "System": return .white.opacity(0.5)
        default: return BroadcastTheme.stageAmber
        }
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(line.speaker.uppercased())
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundStyle(speakerColor)
                    .tracking(1)
                
                Text(line.timestamp, style: .time)
                    .font(.system(size: 8))
                    .foregroundStyle(.white.opacity(0.3))
            }
            
            Text(line.text)
                .font(.system(.caption))
                .foregroundStyle(.white.opacity(0.8))
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

#Preview {
    DebateArenaView(viewModel: {
        let vm = DebateViewModel(
            debateService: DebateService(),
            judgeService: AIJudgeService()
        )
        vm.phase = .debating
        vm.currentTopic = DebateTopic(
            id: "1",
            title: "Should AI replace human decision-making?",
            description: "Exploring the role of AI in critical sectors",
            category: .technology,
            difficulty: 3
        )
        vm.opponentName = "DebateMaster"
        vm.timeRemaining = 178
        vm.isOpponentSpeaking = true
        vm.liveTranscript = [
            TranscriptLine(speaker: "System", text: "Debate started", timestamp: Date()),
            TranscriptLine(speaker: "You", text: "I believe AI should augment rather than replace human decision-making", timestamp: Date()),
            TranscriptLine(speaker: "DebateMaster", text: "That's an interesting point, but consider the efficiency gains...", timestamp: Date())
        ]
        return vm
    }())
}