import SwiftUI
import AVFoundation


struct DebateArenaView: View {
    @Bindable var viewModel: DebateViewModel
    @State private var showTranscript: Bool = false
    @State private var speakingPulse: Bool = false


    var body: some View {
        GeometryReader { geo in
            ZStack {
                Color.black.ignoresSafeArea()


                VStack(spacing: 0) {
                    broadcastHeader


                    ZStack {
                        VStack(spacing: 0) {
                            opponentVideoFeed(height: geo.size.height * 0.42)
                            userVideoFeed(height: geo.size.height * 0.30)
                        }


                        topicBanner
                            .frame(maxHeight: .infinity, alignment: .center)
                    }


                    if showTranscript {
                        transcriptStrip
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                    }

                    controlBar
                    tickerBanner
                }

                ScanlineOverlay()
            }
        }
    }
    
    // Stubs
    private var broadcastHeader: some View { Text("Header").foregroundColor(.white) }
    private func opponentVideoFeed(height: CGFloat) -> some View { Color.red.frame(height: height) }
    private func userVideoFeed(height: CGFloat) -> some View { Color.blue.frame(height: height) }
    private var topicBanner: some View { Text("Topic").foregroundColor(.white) }
    private var transcriptStrip: some View { Text("Transcript").foregroundColor(.white) }
    private var controlBar: some View {
        Button("End Debate") {
            viewModel.submitArguments()
        }.foregroundColor(.white)
    }
    private var tickerBanner: some View { Text("Ticker").foregroundColor(.white) }
}