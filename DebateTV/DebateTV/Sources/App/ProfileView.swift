import SwiftUI


struct ProfileView: View {
    let debateService: DebateService
    @Environment(\.dismiss) private var dismiss
    @State private var editingName: Bool = false
    @State private var nameText: String = ""
    @State private var appeared: Bool = false


    var body: some View {
        NavigationStack {
            ZStack {
                BroadcastBackground()
                VignetteOverlay(intensity: 0.4)


                ScrollView {
                    VStack(spacing: 24) {
                        profileHeader
                        rankProgress
                        statsCards
                        stancesSection
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 8)
                    .padding(.bottom, 40)
                }
                .scrollIndicators(.hidden)
            }
            .navigationTitle("Profile")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .foregroundStyle(.white.opacity(0.6))
                }
            }
        }
    }
    
    private var profileHeader: some View { Text("Header") }
    private var rankProgress: some View { Text("Rank") }
    private var statsCards: some View { Text("Stats") }
    private var stancesSection: some View { Text("Stances") }
}