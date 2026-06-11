import SwiftUI


struct HomeView: View {
    let debateService: DebateService
    let onStartDebate: (DebateCategory?) -> Void
    let onStartWithTopic: (DebateTopic) -> Void
    @State private var selectedCategory: DebateCategory?
    @State private var showProfile: Bool = false
    @State private var showHistory: Bool = false
    @State private var appeared: Bool = false
    @State private var heroGlow: Bool = false


    private var greeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        if hour < 12 { return "Good morning" }
        if hour < 17 { return "Good afternoon" }
        return "Good evening"
    }


    private var featuredTopic: DebateTopic {
        let dayIndex = Calendar.current.ordinality(of: .day, in: .year, for: Date()) ?? 0
        return DebateTopic.samples[dayIndex % DebateTopic.samples.count]
    }


    private var filteredTopics: [DebateTopic] {
        if let cat = selectedCategory {
            return DebateTopic.samples.filter { $0.category == cat }
        }
        return DebateTopic.samples
    }


    var body: some View {
        ZStack {
            BroadcastBackground()
            VignetteOverlay(intensity: 0.4)

            VStack {
                Text(greeting)
                    .font(.largeTitle)
                    .foregroundStyle(.white)
                
                Spacer()
                
                Button("Start Debate") {
                    onStartDebate(selectedCategory)
                }
                .padding()
                .background(BroadcastTheme.broadcastRed)
                .foregroundColor(.white)
                .cornerRadius(8)
                
                Spacer()
            }
        }
    }
}
