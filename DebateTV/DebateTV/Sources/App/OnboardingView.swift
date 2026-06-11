import SwiftUI


struct OnboardingView: View {
    let debateService: DebateService
    let onComplete: () -> Void
    @State private var currentPage: Int = 0
    @State private var username: String = ""
    @State private var selectedEmoji: String = "🎙️"
    @State private var politicalSlider: Double = 3
    @State private var sportsTeamSearch: String = ""
    @State private var selectedTeams: Set<String> = []
    @State private var selectedReligion: String = ""
    @State private var selectedInterests: Set<DebateCategory> = []
    @State private var debateStyle: String = ""
    @State private var appeared: Bool = false
    @State private var titleRevealed: Bool = false
    @State private var subtitleRevealed: Bool = false
    @State private var featuresRevealed: Bool = false
    @State private var buttonRevealed: Bool = false


    private let totalPages = 6


    var body: some View {
        ZStack {
            AnimatedMeshBackground()
            VignetteOverlay(intensity: 0.7)


            TabView(selection: $currentPage) {
                Text("Splash").tag(0)
                Text("Welcome").tag(1)
                Text("Profile").tag(2)
                Text("Interests").tag(3)
                Text("Stance").tag(4)
                Text("Style").tag(5)
            }
            // Removed unavailable tabViewStyle for macOS compatibility
            
            VStack {
                Spacer()
                Button("Complete") {
                    onComplete()
                }
                .padding()
                .background(BroadcastTheme.broadcastRed)
                .foregroundColor(.white)
                .cornerRadius(8)
            }
        }
    }
    
    // Stubs for missing Subviews referenced
    private var splashPage: some View { Text("Splash") }
    private var welcomePage: some View { Text("Welcome") }
    private var profilePage: some View { Text("Profile") }
    private var interestsPage: some View { Text("Interests") }
    private var stancePage: some View { Text("Stance") }
    private var stylePickerPage: some View { Text("Style") }
}