import SwiftUI


struct ContentView: View {
    @State private var debateService = DebateService()
    @State private var judgeService = AIJudgeService()
    @State private var viewModel: DebateViewModel?
    @State private var showOnboarding: Bool = false


    var body: some View {
        Group {
            if showOnboarding {
                OnboardingView(debateService: debateService) {
                    withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                        showOnboarding = false
                    }
                }
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
    }

    @ViewBuilder
    private func debateFlow(viewModel: DebateViewModel) -> some View {
        switch viewModel.phase {
        case .idle:
            EmptyView()
        case .matchmaking:
            MatchmakingView(
                progress: viewModel.matchmakingProgress,
                opponentName: viewModel.opponentName,
                onCancel: { self.viewModel = nil }
            )
        case .debate:
            DebateArenaView(viewModel: viewModel)
        case .verdict:
            if let result = viewModel.debateResult {
                VerdictView(
                    result: result,
                    onRematch: { self.viewModel = nil },
                    onHome: { self.viewModel = nil }
                )
            }
        }
    }
}