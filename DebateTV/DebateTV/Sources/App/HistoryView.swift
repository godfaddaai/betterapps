import SwiftUI


struct HistoryView: View {
    let debateService: DebateService
    @Environment(\.dismiss) private var dismiss
    @State private var selectedResult: DebateResult?
    @State private var filterCategory: DebateCategory?


    private var filteredHistory: [DebateResult] {
        return debateService.debateHistory
    }


    private var winCount: Int { debateService.debateHistory.filter { $0.outcome == .win }.count }
    private var lossCount: Int { debateService.debateHistory.filter { $0.outcome == .loss }.count }
    private var drawCount: Int { debateService.debateHistory.filter { $0.outcome == .draw }.count }


    var body: some View {
        NavigationStack {
            ZStack {
                BroadcastBackground()
                VignetteOverlay(intensity: 0.4)


                if debateService.debateHistory.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "text.book.closed")
                            .font(.system(size: 40))
                            .foregroundStyle(.white.opacity(0.08))
                        VStack(spacing: 6) {
                            Text("No Debates Yet")
                                .font(.system(.headline, weight: .bold))
                                .foregroundStyle(.white.opacity(0.3))
                            Text("Your match history will appear here\nafter your first debate")
                                .font(.system(.caption))
                                .foregroundStyle(.white.opacity(0.15))
                                .multilineTextAlignment(.center)
                        }
                    }
                } else {
                    List(filteredHistory) { result in
                        Text(result.topic)
                    }
                }
            }
        }
    }
}