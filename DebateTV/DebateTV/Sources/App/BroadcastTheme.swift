import SwiftUI


enum BroadcastTheme {
    static let broadcastRed = Color(red: 0.95, green: 0.15, blue: 0.12)
    static let fieldGreen = Color(red: 0.15, green: 0.82, blue: 0.42)
    static let stageAmber = Color(red: 1.0, green: 0.62, blue: 0.04)
    static let deepBlack = Color(red: 0.03, green: 0.03, blue: 0.04)
    static let darkSurface = Color(red: 0.07, green: 0.07, blue: 0.09)
    static let cardSurface = Color(red: 0.11, green: 0.11, blue: 0.13)
    static let neonCyan = Color(red: 0.0, green: 0.88, blue: 1.0)
    static let verdictGold = Color(red: 1.0, green: 0.84, blue: 0.0)
    static let electricBlue = Color(red: 0.25, green: 0.45, blue: 1.0)
    static let hotPink = Color(red: 1.0, green: 0.2, blue: 0.55)


    static let stageLighting = LinearGradient(
        colors: [
            Color(red: 0.12, green: 0.04, blue: 0.02),
            Color(red: 0.03, green: 0.03, blue: 0.07),
            Color(red: 0.02, green: 0.04, blue: 0.12)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )


    static let redSpotlight = RadialGradient(
        colors: [broadcastRed.opacity(0.25), .clear],
        center: .topLeading,
        startRadius: 0,
        endRadius: 350
    )


    static let amberSpotlight = RadialGradient(
        colors: [stageAmber.opacity(0.12), .clear],
        center: .topTrailing,
        startRadius: 0,
        endRadius: 280
    )
}