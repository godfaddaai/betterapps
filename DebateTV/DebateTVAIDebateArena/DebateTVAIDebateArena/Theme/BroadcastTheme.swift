import SwiftUI

struct BroadcastTheme {
    // MARK: - Colors

    /// Primary brand color - DebateTV purple, THE accent across all brand content
    static let primary = Color(hex: "A855F7")

    /// Deeper purple used as the bottom stop of the primary gradient
    static let primaryDeep = Color(hex: "7C3AED")

    /// Secondary accent color - Hot fuchsia, the energetic sibling of the brand purple
    static let secondary = Color(hex: "D946EF")

    /// Success / agree color - Agree-green from the verdict cards
    static let success = Color(hex: "22C55E")

    /// Warning color - Gold for cautions
    static let warning = Color(red: 1.0, green: 0.8, blue: 0.0)

    /// Error / wrong color - Wrong-red from the verdict cards
    static let error = Color(hex: "EF4444")

    /// Background color - Deep night, top of the brand canvas gradient
    static let background = Color(hex: "121022")

    /// Deep night bottom stop of the brand canvas gradient
    static let backgroundDeep = Color(hex: "281234")

    /// Surface color - Slightly lifted night surface
    static let surface = Color(hex: "1E1833")

    /// Card background - Even lighter elevated surface for cards
    static let cardBackground = Color(hex: "2A2144")

    /// Primary text color
    static let text = Color.white

    /// Secondary text color - muted lavender from the brand
    static let textSecondary = Color(hex: "AAA5C3")

    /// Tertiary text color
    static let textTertiary = Color(hex: "AAA5C3").opacity(0.6)

    /// Live indicator color - broadcast red, reserved STRICTLY for LIVE / on-air elements
    static let liveRed = Color(hex: "FF1919")

    /// Broadcast red color (alias for liveRed for compatibility)
    static let broadcastRed = liveRed

    /// Deepest night color for maximum contrast (never pure #000)
    static let deepBlack = Color(hex: "0C0A18")

    /// Stage amber color for warnings/attention
    static let stageAmber = Color(red: 1.0, green: 0.75, blue: 0.0)

    /// Stage lighting color for effects - faint purple wash from the rig
    static let stageLighting = LinearGradient(
        gradient: Gradient(colors: [Color(hex: "A855F7").opacity(0.09), Color(hex: "A855F7").opacity(0.0)]),
        startPoint: .top,
        endPoint: .bottom
    )

    /// Red spotlight effect (LIVE / on-air moments only)
    static let redSpotlight = RadialGradient(
        gradient: Gradient(colors: [liveRed.opacity(0.3), liveRed.opacity(0.0)]),
        center: .center,
        startRadius: 5,
        endRadius: 100
    )

    /// Purple spotlight effect - the brand stage light
    static let purpleSpotlight = RadialGradient(
        gradient: Gradient(colors: [primary.opacity(0.28), primary.opacity(0.0)]),
        center: .center,
        startRadius: 5,
        endRadius: 100
    )

    /// Violet spotlight effect - secondary stage light
    static let violetSpotlight = RadialGradient(
        gradient: Gradient(colors: [secondary.opacity(0.16), secondary.opacity(0.0)]),
        center: .center,
        startRadius: 5,
        endRadius: 100
    )

    /// Amber spotlight effect
    static let amberSpotlight = RadialGradient(
        gradient: Gradient(colors: [stageAmber.opacity(0.3), stageAmber.opacity(0.0)]),
        center: .center,
        startRadius: 5,
        endRadius: 100
    )

    /// Neon highlight color (legacy name - now the brand's electric violet glow)
    static let neonCyan = Color(hex: "C084FC")
    
    /// Get color based on debate outcome
    static func outcomeColor(_ result: DebateResult) -> Color {
        switch result {
        case .won: return success
        case .lost: return error
        case .draw: return warning
        }
    }
    
    // MARK: - Gradients
    
    static let primaryGradient = LinearGradient(
        gradient: Gradient(colors: [primary, primaryDeep]),
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let secondaryGradient = LinearGradient(
        gradient: Gradient(colors: [secondary, secondary.opacity(0.8)]),
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// The brand canvas: deep-night #121022 -> #281234, top to bottom. Never pure black.
    static let backgroundGradient = LinearGradient(
        gradient: Gradient(colors: [background, backgroundDeep]),
        startPoint: .top,
        endPoint: .bottom
    )
    
    static let liveGradient = LinearGradient(
        gradient: Gradient(colors: [liveRed, Color.red.opacity(0.8)]),
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
    
    // MARK: - Shadows
    
    static let cardShadow = Color.black.opacity(0.3)
    static let buttonShadow = Color.black.opacity(0.2)
    
    // MARK: - Typography Styles
    
    struct Typography {
        static let largeTitle = Font.largeTitle.weight(.bold)
        static let title = Font.title.weight(.semibold)
        static let title2 = Font.title2.weight(.medium)
        static let title3 = Font.title3.weight(.medium)
        static let headline = Font.headline.weight(.semibold)
        static let subheadline = Font.subheadline.weight(.medium)
        static let body = Font.body
        static let callout = Font.callout
        static let caption = Font.caption
        static let caption2 = Font.caption2
        
        // Custom styles
        static let timerFont = Font.title.monospacedDigit().weight(.semibold)
        static let scoreFont = Font.largeTitle.monospacedDigit().weight(.bold)
        static let liveIndicator = Font.caption.weight(.bold)
    }
    
    // MARK: - Spacing
    
    struct Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
        static let xxl: CGFloat = 48
    }
    
    // MARK: - Corner Radius
    
    struct CornerRadius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
        static let pill: CGFloat = 999
    }
    
    // MARK: - Icon Sizes
    
    struct IconSize {
        static let sm: CGFloat = 16
        static let md: CGFloat = 24
        static let lg: CGFloat = 32
        static let xl: CGFloat = 48
    }
    
    // MARK: - Animation Durations
    
    struct AnimationDuration {
        static let fast: Double = 0.2
        static let medium: Double = 0.3
        static let slow: Double = 0.5
        static let xSlow: Double = 0.8
    }
    
    // MARK: - Opacity Levels
    
    struct Opacity {
        static let disabled: Double = 0.3
        static let secondary: Double = 0.7
        static let overlay: Double = 0.8
        static let modal: Double = 0.9
    }
}

// MARK: - Theme Extensions

extension Color {
    /// Initialize color from hex string
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - View Modifiers

struct BroadcastCardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(BroadcastTheme.Spacing.md)
            .background(BroadcastTheme.surface)
            .cornerRadius(BroadcastTheme.CornerRadius.lg)
            .shadow(color: BroadcastTheme.cardShadow, radius: 8, x: 0, y: 4)
    }
}

struct BroadcastButtonStyle: ButtonStyle {
    let variant: ButtonVariant
    
    enum ButtonVariant {
        case primary
        case secondary
        case danger
        case ghost
        
        var backgroundColor: Color {
            switch self {
            case .primary: return BroadcastTheme.primary
            case .secondary: return BroadcastTheme.secondary
            case .danger: return BroadcastTheme.error
            case .ghost: return Color.clear
            }
        }
        
        var foregroundColor: Color {
            switch self {
            case .primary, .secondary, .danger: return .white
            case .ghost: return BroadcastTheme.primary
            }
        }
        
        var borderColor: Color? {
            switch self {
            case .ghost: return BroadcastTheme.primary
            default: return nil
            }
        }
    }
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.horizontal, BroadcastTheme.Spacing.lg)
            .padding(.vertical, BroadcastTheme.Spacing.md)
            .background(variant.backgroundColor)
            .foregroundColor(variant.foregroundColor)
            .cornerRadius(BroadcastTheme.CornerRadius.lg)
            .overlay(
                RoundedRectangle(cornerRadius: BroadcastTheme.CornerRadius.lg)
                    .stroke(variant.borderColor ?? Color.clear, lineWidth: 1)
            )
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: BroadcastTheme.AnimationDuration.fast), value: configuration.isPressed)
    }
}

struct LiveIndicatorStyle: ViewModifier {
    @State private var isAnimating = false
    
    func body(content: Content) -> some View {
        content
            .scaleEffect(isAnimating ? 1.1 : 1.0)
            .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: isAnimating)
            .onAppear {
                isAnimating = true
            }
    }
}

// MARK: - View Extensions

extension View {
    func broadcastCard() -> some View {
        modifier(BroadcastCardStyle())
    }
    
    func broadcastButton(_ variant: BroadcastButtonStyle.ButtonVariant = .primary) -> some View {
        buttonStyle(BroadcastButtonStyle(variant: variant))
    }
    
    func liveIndicator() -> some View {
        modifier(LiveIndicatorStyle())
    }
    
    /// Apply broadcast theme background
    func broadcastBackground() -> some View {
        background(BroadcastTheme.backgroundGradient.ignoresSafeArea())
    }
    
    /// Apply haptic feedback
    func hapticFeedback(_ style: UIImpactFeedbackGenerator.FeedbackStyle = .medium) -> some View {
        onTapGesture {
            let impactFeedback = UIImpactFeedbackGenerator(style: style)
            impactFeedback.impactOccurred()
        }
    }
}

// MARK: - Custom Components

struct BroadcastProgressBar: View {
    let progress: Double
    let color: Color
    let height: CGFloat
    
    init(progress: Double, color: Color = BroadcastTheme.primary, height: CGFloat = 4) {
        self.progress = progress
        self.color = color
        self.height = height
    }
    
    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(BroadcastTheme.surface)
                    .frame(height: height)
                
                Rectangle()
                    .fill(color)
                    .frame(width: geometry.size.width * progress, height: height)
                    .animation(.easeInOut(duration: BroadcastTheme.AnimationDuration.medium), value: progress)
            }
        }
        .frame(height: height)
        .cornerRadius(height / 2)
    }
}

struct BroadcastBadge: View {
    let text: String
    let color: Color
    
    init(_ text: String, color: Color = BroadcastTheme.primary) {
        self.text = text
        self.color = color
    }
    
    var body: some View {
        Text(text)
            .font(.caption.weight(.medium))
            .padding(.horizontal, BroadcastTheme.Spacing.sm)
            .padding(.vertical, BroadcastTheme.Spacing.xs)
            .background(color)
            .foregroundColor(.white)
            .cornerRadius(BroadcastTheme.CornerRadius.sm)
    }
}

struct BroadcastDivider: View {
    let color: Color
    let height: CGFloat
    
    init(color: Color = BroadcastTheme.surface, height: CGFloat = 1) {
        self.color = color
        self.height = height
    }
    
    var body: some View {
        Rectangle()
            .fill(color)
            .frame(height: height)
    }
}

// MARK: - Theme Preview

struct BroadcastThemePreview: View {
    var body: some View {
        ScrollView {
            VStack(spacing: BroadcastTheme.Spacing.lg) {
                Text("BroadcastTheme Preview")
                    .font(BroadcastTheme.Typography.largeTitle)
                    .foregroundColor(BroadcastTheme.text)
                
                // Color Palette
                LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: BroadcastTheme.Spacing.md) {
                    ColorSwatch("Primary", BroadcastTheme.primary)
                    ColorSwatch("Secondary", BroadcastTheme.secondary)
                    ColorSwatch("Success", BroadcastTheme.success)
                    ColorSwatch("Warning", BroadcastTheme.warning)
                    ColorSwatch("Error", BroadcastTheme.error)
                    ColorSwatch("Live", BroadcastTheme.liveRed)
                }
                
                // Typography
                VStack(alignment: .leading, spacing: BroadcastTheme.Spacing.sm) {
                    Text("Typography")
                        .font(BroadcastTheme.Typography.headline)
                        .foregroundColor(BroadcastTheme.text)
                    
                    Text("Large Title").font(BroadcastTheme.Typography.largeTitle)
                    Text("Title").font(BroadcastTheme.Typography.title)
                    Text("Headline").font(BroadcastTheme.Typography.headline)
                    Text("Body").font(BroadcastTheme.Typography.body)
                    Text("Caption").font(BroadcastTheme.Typography.caption)
                }
                .foregroundColor(BroadcastTheme.text)
                .broadcastCard()
                
                // Buttons
                VStack(spacing: BroadcastTheme.Spacing.md) {
                    Text("Buttons")
                        .font(BroadcastTheme.Typography.headline)
                        .foregroundColor(BroadcastTheme.text)
                    
                    Button("Primary") {}
                        .broadcastButton(.primary)
                    
                    Button("Secondary") {}
                        .broadcastButton(.secondary)
                    
                    Button("Danger") {}
                        .broadcastButton(.danger)
                    
                    Button("Ghost") {}
                        .broadcastButton(.ghost)
                }
                .broadcastCard()
                
                // Components
                VStack(spacing: BroadcastTheme.Spacing.md) {
                    Text("Components")
                        .font(BroadcastTheme.Typography.headline)
                        .foregroundColor(BroadcastTheme.text)
                    
                    HStack {
                        BroadcastBadge("LIVE", color: BroadcastTheme.liveRed)
                        BroadcastBadge("NEW")
                        BroadcastBadge("HOT", color: BroadcastTheme.secondary)
                    }
                    
                    BroadcastProgressBar(progress: 0.7)
                    
                    BroadcastDivider()
                    
                    HStack {
                        Text("LIVE")
                            .font(BroadcastTheme.Typography.liveIndicator)
                            .foregroundColor(BroadcastTheme.liveRed)
                            .liveIndicator()
                        
                        Spacer()
                        
                        Text("12:34")
                            .font(BroadcastTheme.Typography.timerFont)
                            .foregroundColor(BroadcastTheme.text)
                    }
                }
                .broadcastCard()
            }
            .padding(BroadcastTheme.Spacing.lg)
        }
        .broadcastBackground()
    }
}

struct ColorSwatch: View {
    let name: String
    let color: Color
    
    init(_ name: String, _ color: Color) {
        self.name = name
        self.color = color
    }
    
    var body: some View {
        VStack {
            RoundedRectangle(cornerRadius: BroadcastTheme.CornerRadius.md)
                .fill(color)
                .frame(height: 60)
            
            Text(name)
                .font(BroadcastTheme.Typography.caption)
                .foregroundColor(BroadcastTheme.text)
        }
    }
}

#Preview {
    BroadcastThemePreview()
}