import SwiftUI

struct ContentView: View {
    @State private var debateService = DebateService()
    @State private var judgeService = AIJudgeService()
    @State private var viewModel: DebateViewModel?
    @State private var showOnboarding: Bool = false
    
    var body: some View {
        Group {
            if showOnboarding {
                OnboardingView(isOnboardingComplete: $showOnboarding)
            } else if let viewModel {
                debateFlow(viewModel: viewModel)
            } else {
                HomeView(
                    debateService: debateService,
                    onStartDebate: { category in
                        let vm = DebateViewModel(debateService: debateService, judgeService: judgeService)
                        vm.selectedCategory = category
                        self.viewModel = vm
                        vm.startMatchmaking()
                    },
                    onStartWithTopic: { topic in
                        let vm = DebateViewModel(debateService: debateService, judgeService: judgeService)
                        vm.startWithTopic(topic)
                        self.viewModel = vm
                    }
                )
            }
        }
        .animation(.snappy, value: viewModel?.phase)
        .onAppear {
            // Check if onboarding needed
            if UserDefaults.standard.bool(forKey: "hasCompletedOnboarding") == false {
                showOnboarding = true
            }
        }
    }
    
    @ViewBuilder
    private func debateFlow(viewModel: DebateViewModel) -> some View {
        switch viewModel.phase {
        case .idle:
            HomeView(
                debateService: debateService,
                onStartDebate: { category in
                    viewModel.selectedCategory = category
                    viewModel.startMatchmaking()
                },
                onStartWithTopic: { topic in
                    viewModel.startWithTopic(topic)
                }
            )
            
        case .matchmaking:
            MatchmakingView(viewModel: viewModel)
            
        case .topicReveal:
            TopicRevealView(viewModel: viewModel)
            
        case .countdown:
            CountdownView(viewModel: viewModel)
            
        case .debating:
            DebateArenaView(viewModel: viewModel)
            
        case .judging:
            JudgingView()
            
        case .verdict:
            if let result = viewModel.result {
                VerdictView(
                    result: result.outcome == .win ? .won : result.outcome == .loss ? .lost : .draw,
                    onRematch: {
                        viewModel.reset()
                        viewModel.startMatchmaking()
                    },
                    onHome: {
                        viewModel.reset()
                        self.viewModel = nil
                    }
                )
            }
        }
    }
}

#Preview {
    ContentView()
}