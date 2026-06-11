import SwiftUI

struct OnboardingView: View {
    @State private var currentPage = 0
    @Binding var isOnboardingComplete: Bool
    
    private let pages = OnboardingPage.allPages
    
    var body: some View {
        ZStack {
            BroadcastTheme.backgroundGradient
                .ignoresSafeArea()
            
            VStack {
                // Skip Button
                HStack {
                    Spacer()
                    if currentPage < pages.count - 1 {
                        Button("Skip") {
                            completeOnboarding()
                        }
                        .font(.subheadline)
                        .foregroundColor(BroadcastTheme.text.opacity(0.6))
                        .padding()
                    }
                }
                
                // Content
                TabView(selection: $currentPage) {
                    ForEach(0..<pages.count, id: \.self) { index in
                        OnboardingPageView(page: pages[index])
                            .tag(index)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                .animation(.easeInOut, value: currentPage)
                
                // Page Indicator & Navigation
                VStack(spacing: 24) {
                    PageIndicator(
                        currentPage: currentPage,
                        totalPages: pages.count
                    )
                    
                    NavigationButtons(
                        currentPage: currentPage,
                        totalPages: pages.count,
                        onNext: { nextPage() },
                        onComplete: { completeOnboarding() }
                    )
                }
                .padding()
            }
        }
    }
    
    private func nextPage() {
        withAnimation(.easeInOut(duration: 0.3)) {
            currentPage += 1
        }
    }
    
    private func completeOnboarding() {
        UserDefaults.standard.set(true, forKey: "hasCompletedOnboarding")
        withAnimation(.easeInOut(duration: 0.5)) {
            isOnboardingComplete = false
        }
    }
}

struct OnboardingPageView: View {
    let page: OnboardingPage
    
    var body: some View {
        VStack(spacing: 32) {
            Spacer()
            
            // Illustration
            ZStack {
                Circle()
                    .fill(BroadcastTheme.primary.opacity(0.18))
                    .frame(width: 210, height: 210)
                    .blur(radius: 24)

                Circle()
                    .fill(BroadcastTheme.primary.opacity(0.1))
                    .frame(width: 200, height: 200)

                Circle()
                    .stroke(BroadcastTheme.primary.opacity(0.25), lineWidth: 1)
                    .frame(width: 200, height: 200)

                Image(systemName: page.iconName)
                    .font(.system(size: 80, weight: .light))
                    .foregroundColor(BroadcastTheme.primary)
            }
            .scaleEffect(1.0)
            .animation(.easeInOut(duration: 2).repeatForever(autoreverses: true), value: true)
            
            // Content
            VStack(spacing: 16) {
                Text(page.title)
                    .font(.largeTitle.bold())
                    .foregroundColor(BroadcastTheme.text)
                    .multilineTextAlignment(.center)
                
                Text(page.description)
                    .font(.body)
                    .foregroundColor(BroadcastTheme.textSecondary)
                    .multilineTextAlignment(.center)
                    .lineLimit(nil)
                    .padding(.horizontal)
            }
            
            // Features List (if any)
            if !page.features.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(page.features, id: \.self) { feature in
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(BroadcastTheme.primary)
                            Text(feature)
                                .font(.subheadline)
                                .foregroundColor(BroadcastTheme.text)
                        }
                    }
                }
                .padding()
                .background(BroadcastTheme.surface)
                .cornerRadius(16)
            }
            
            Spacer()
        }
        .padding()
    }
}

struct PageIndicator: View {
    let currentPage: Int
    let totalPages: Int
    
    var body: some View {
        HStack(spacing: 8) {
            ForEach(0..<totalPages, id: \.self) { index in
                Capsule()
                    .fill(index == currentPage ? BroadcastTheme.primary : BroadcastTheme.text.opacity(0.3))
                    .frame(width: index == currentPage ? 24 : 8, height: 8)
                    .animation(.easeInOut(duration: 0.3), value: currentPage)
            }
        }
    }
}

struct NavigationButtons: View {
    let currentPage: Int
    let totalPages: Int
    let onNext: () -> Void
    let onComplete: () -> Void
    
    var body: some View {
        HStack {
            // Back Button (hidden on first page)
            if currentPage > 0 {
                Button("Back") {
                    // Handle back navigation if needed
                }
                .font(.subheadline)
                .foregroundColor(BroadcastTheme.text.opacity(0.6))
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                Spacer()
            }
            
            // Next/Get Started Button
            Button(action: currentPage == totalPages - 1 ? onComplete : onNext) {
                HStack {
                    Text(currentPage == totalPages - 1 ? "Get Started" : "Next")
                    if currentPage < totalPages - 1 {
                        Image(systemName: "arrow.right")
                    }
                }
                .font(.headline)
                .foregroundColor(.white)
                .frame(maxWidth: currentPage == 0 ? .infinity : nil)
                .padding()
                .background(BroadcastTheme.primaryGradient)
                .cornerRadius(16)
                .shadow(color: BroadcastTheme.primary.opacity(0.35), radius: 12, y: 5)
            }
        }
    }
}

struct OnboardingPage {
    let title: String
    let description: String
    let iconName: String
    let features: [String]
    
    static let allPages = [
        OnboardingPage(
            title: "Welcome to DebateTV",
            description: "The ultimate platform for live debates with AI-powered judging and real-time audience engagement.",
            iconName: "tv",
            features: []
        ),
        OnboardingPage(
            title: "Debate Live",
            description: "Engage in real-time debates on topics you're passionate about. Stream live to audiences worldwide.",
            iconName: "person.2.wave.2",
            features: [
                "Choose from trending topics",
                "Match with opponents worldwide",
                "Stream to live audiences",
                "Real-time interaction"
            ]
        ),
        OnboardingPage(
            title: "AI-Powered Judging",
            description: "Get instant, unbiased feedback on your debate performance with our advanced AI judge system.",
            iconName: "brain.head.profile",
            features: [
                "Objective performance scoring",
                "Detailed argument analysis",
                "Improvement suggestions",
                "Fair and consistent judging"
            ]
        ),
        OnboardingPage(
            title: "Track Your Progress",
            description: "Monitor your debate skills, track wins and losses, and see your improvement over time.",
            iconName: "chart.line.uptrend.xyaxis",
            features: [
                "Personal statistics",
                "Performance analytics",
                "Skill progression tracking",
                "Achievement system"
            ]
        ),
        OnboardingPage(
            title: "Ready to Start?",
            description: "Join thousands of debaters improving their skills and engaging in meaningful discussions.",
            iconName: "flag.checkered",
            features: []
        )
    ]
}

// Permission Request View (can be shown after onboarding)
struct PermissionRequestView: View {
    @Binding var isPresented: Bool
    @State private var cameraPermissionGranted = false
    @State private var microphonePermissionGranted = false
    
    var body: some View {
        VStack(spacing: 24) {
            VStack(spacing: 16) {
                Image(systemName: "lock.shield")
                    .font(.system(size: 60))
                    .foregroundColor(BroadcastTheme.primary)
                
                Text("Permissions Needed")
                    .font(.title.bold())
                    .foregroundColor(BroadcastTheme.text)
                
                Text("DebateTV needs access to your camera and microphone to enable live debates.")
                    .font(.body)
                    .foregroundColor(BroadcastTheme.text.opacity(0.7))
                    .multilineTextAlignment(.center)
            }
            
            VStack(spacing: 16) {
                PermissionRow(
                    icon: "camera",
                    title: "Camera Access",
                    description: "Required for video debates",
                    isGranted: cameraPermissionGranted
                ) {
                    requestCameraPermission()
                }
                
                PermissionRow(
                    icon: "mic",
                    title: "Microphone Access",
                    description: "Required for audio in debates",
                    isGranted: microphonePermissionGranted
                ) {
                    requestMicrophonePermission()
                }
            }
            
            Button("Continue") {
                isPresented = false
            }
            .disabled(!(cameraPermissionGranted && microphonePermissionGranted))
            .frame(maxWidth: .infinity)
            .padding()
            .background(
                (cameraPermissionGranted && microphonePermissionGranted) ? 
                BroadcastTheme.primary : BroadcastTheme.text.opacity(0.3)
            )
            .foregroundColor(.white)
            .cornerRadius(16)
        }
        .padding()
        .background(BroadcastTheme.background)
    }
    
    private func requestCameraPermission() {
        // Request camera permission
        cameraPermissionGranted = true // Mock for preview
    }
    
    private func requestMicrophonePermission() {
        // Request microphone permission
        microphonePermissionGranted = true // Mock for preview
    }
}

struct PermissionRow: View {
    let icon: String
    let title: String
    let description: String
    let isGranted: Bool
    let action: () -> Void
    
    var body: some View {
        HStack {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(BroadcastTheme.primary)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.headline)
                    .foregroundColor(BroadcastTheme.text)
                
                Text(description)
                    .font(.subheadline)
                    .foregroundColor(BroadcastTheme.text.opacity(0.7))
            }
            
            Spacer()
            
            if isGranted {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                    .font(.title2)
            } else {
                Button("Allow") {
                    action()
                }
                .font(.subheadline.weight(.medium))
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(BroadcastTheme.primary)
                .foregroundColor(.white)
                .cornerRadius(8)
            }
        }
        .padding()
        .background(BroadcastTheme.surface)
        .cornerRadius(12)
    }
}

#Preview {
    OnboardingView(isOnboardingComplete: .constant(false))
}