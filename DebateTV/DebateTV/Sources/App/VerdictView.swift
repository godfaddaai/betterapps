import SwiftUI


struct VerdictView: View {
    let result: DebateResult
    let onRematch: () -> Void
    let onHome: () -> Void
    @State private var revealed: Bool = false
    @State private var scoreAnimated: Bool = false
    @State private var detailsRevealed: Bool = false
    @State private var buttonsRevealed: Bool = false


    var body: some View {
        ZStack {
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.6)


            ScrollView {
                VStack(spacing: 0) {
                    verdictHeader
                    scorecard
                    breakdownBars
                    analysisSection
                    actionButtons
                }
                .padding(.bottom, 44)
            }
            .scrollIndicators(.hidden)


            ScanlineOverlay()
                .ignoresSafeArea()
                .allowsHitTesting(false)
        }
        .onAppear {
            withAnimation(.spring(response: 0.6, dampingFraction: 0.65).delay(0.3)) {
                revealed = true
            }
        }
    }
    
    private var verdictHeader: some View { Text(result.topic).foregroundColor(.white).font(.headline) }
    private var scorecard: some View { 
        HStack {
            Text("User: \(result.userScore)")
            Text("Opponent: \(result.opponentScore)")
        }.foregroundColor(.white)
    }
    private var breakdownBars: some View { Text("Breakdown Bars").foregroundColor(.white) }
    private var analysisSection: some View { Text(result.reasoning).foregroundColor(.white).padding() }
    private var actionButtons: some View {
        HStack {
            Button("Rematch", action: onRematch)
            Button("Home", action: onHome)
        }.padding()
    }
}