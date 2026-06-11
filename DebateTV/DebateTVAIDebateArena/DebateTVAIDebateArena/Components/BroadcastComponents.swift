import SwiftUI

struct ScanlineOverlay: View {
    var body: some View {
        Canvas { context, size in
            for y in stride(from: 0, to: size.height, by: 3) {
                let rect = CGRect(x: 0, y: y, width: size.width, height: 1)
                context.fill(Path(rect), with: .color(.black.opacity(0.04)))
            }
        }
        .allowsHitTesting(false)
    }
}

struct VignetteOverlay: View {
    var intensity: Double = 0.6

    var body: some View {
        RadialGradient(
            colors: [.clear, .black.opacity(intensity)],
            center: .center,
            startRadius: 150,
            endRadius: 550
        )
        .ignoresSafeArea()
        .allowsHitTesting(false)
    }
}

struct BroadcastBackground: View {
    var body: some View {
        ZStack {
            BroadcastTheme.backgroundGradient.ignoresSafeArea()
            BroadcastTheme.stageLighting.ignoresSafeArea()
            BroadcastTheme.purpleSpotlight.ignoresSafeArea()
            BroadcastTheme.violetSpotlight.ignoresSafeArea()
        }
    }
}

struct AnimatedMeshBackground: View {
    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 20.0)) { timeline in
            let t = timeline.date.timeIntervalSinceReferenceDate
            MeshGradient(
                width: 3,
                height: 3,
                points: [
                    [0, 0], [0.5, 0], [1, 0],
                    [Float(sin(t * 0.2) * 0.08), 0.5],
                    [Float(0.5 + sin(t * 0.15) * 0.12), Float(0.5 + cos(t * 0.18) * 0.08)],
                    [Float(1 + cos(t * 0.2) * 0.08), 0.5],
                    [0, 1], [0.5, 1], [1, 1]
                ],
                colors: [
                    // Deep-night + DebateTV purple family (#121022 -> #281234 canvas)
                    Color(red: 0.07, green: 0.06, blue: 0.13),
                    Color(red: 0.13, green: 0.07, blue: 0.22),
                    Color(red: 0.08, green: 0.06, blue: 0.15),
                    Color(red: 0.11, green: 0.05, blue: 0.20),
                    Color(red: 0.20, green: 0.09, blue: 0.32),
                    Color(red: 0.10, green: 0.05, blue: 0.18),
                    Color(red: 0.13, green: 0.06, blue: 0.18),
                    Color(red: 0.16, green: 0.07, blue: 0.21),
                    Color(red: 0.11, green: 0.05, blue: 0.15)
                ]
            )
            .ignoresSafeArea()
        }
    }
}

struct LiveBadge: View {
    @State private var isAnimating: Bool = false

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(BroadcastTheme.broadcastRed)
                .frame(width: 7, height: 7)
                .opacity(isAnimating ? 1 : 0.3)
                .overlay(
                    Circle()
                        .fill(BroadcastTheme.broadcastRed)
                        .frame(width: 7, height: 7)
                        .blur(radius: 4)
                        .opacity(isAnimating ? 0.6 : 0)
                )
            Text("LIVE")
                .font(.system(size: 11, weight: .black, design: .monospaced))
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(BroadcastTheme.broadcastRed.opacity(0.12))
        .clipShape(Capsule())
        .overlay(Capsule().stroke(BroadcastTheme.broadcastRed.opacity(0.35), lineWidth: 0.5))
        .onAppear {
            withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
                isAnimating = true
            }
        }
    }
}

struct PulsingDot: View {
    let color: Color
    @State private var pulse: Bool = false

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 6, height: 6)
            .overlay(
                Circle()
                    .fill(color.opacity(0.4))
                    .frame(width: 6, height: 6)
                    .scaleEffect(pulse ? 2.5 : 1)
                    .opacity(pulse ? 0 : 0.6)
            )
            .onAppear {
                withAnimation(.easeOut(duration: 1.5).repeatForever(autoreverses: false)) {
                    pulse = true
                }
            }
    }
}

struct ChromaticAberrationEffect: View {
    let offset: CGFloat
    
    var body: some View {
        ZStack {
            Color.clear
                .overlay(
                    LinearGradient(
                        colors: [
                            Color.red.opacity(0.1),
                            Color.clear,
                            Color.blue.opacity(0.1)
                        ],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                    .offset(x: offset)
                    .blendMode(.screen)
                )
        }
        .allowsHitTesting(false)
    }
}

struct StageLight: View {
    let color: Color
    let angle: Angle
    let intensity: Double
    
    var body: some View {
        GeometryReader { geo in
            LinearGradient(
                colors: [
                    color.opacity(intensity),
                    color.opacity(intensity * 0.3),
                    Color.clear
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .mask(
                Ellipse()
                    .frame(width: geo.size.width * 1.5, height: geo.size.height * 0.8)
                    .blur(radius: 40)
            )
            .rotationEffect(angle)
            .blendMode(.screen)
        }
        .allowsHitTesting(false)
    }
}

struct TVStaticNoise: View {
    @State private var phase: CGFloat = 0
    
    var body: some View {
        Canvas { context, size in
            for _ in 0..<100 {
                let x = CGFloat.random(in: 0...size.width)
                let y = CGFloat.random(in: 0...size.height)
                let rect = CGRect(x: x, y: y, width: 2, height: 2)
                context.fill(Path(rect), with: .color(.white.opacity(Double.random(in: 0.02...0.08))))
            }
        }
        .onAppear {
            withAnimation(.linear(duration: 0.1).repeatForever(autoreverses: false)) {
                phase = 1
            }
        }
        .allowsHitTesting(false)
    }
}

struct BroadcastBorder: View {
    let color: Color
    let lineWidth: CGFloat
    let cornerRadius: CGFloat
    
    init(color: Color = BroadcastTheme.broadcastRed, lineWidth: CGFloat = 3, cornerRadius: CGFloat = 12) {
        self.color = color
        self.lineWidth = lineWidth
        self.cornerRadius = cornerRadius
    }
    
    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius)
            .stroke(
                LinearGradient(
                    colors: [
                        color,
                        color.opacity(0.8),
                        color.opacity(0.6)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ),
                lineWidth: lineWidth
            )
    }
}

struct NeonGlow: ViewModifier {
    let color: Color
    let intensity: Double
    
    func body(content: Content) -> some View {
        content
            .shadow(color: color, radius: intensity * 2)
            .shadow(color: color.opacity(0.8), radius: intensity * 4)
            .shadow(color: color.opacity(0.6), radius: intensity * 8)
    }
}

extension View {
    func neonGlow(color: Color = BroadcastTheme.neonCyan, intensity: Double = 4) -> some View {
        modifier(NeonGlow(color: color, intensity: intensity))
    }
}

// MARK: - Enhanced Broadcast Components

struct BroadcastSignalIndicator: View {
    let signalStrength: Int // 0-5
    @State private var animateBars: Bool = false
    
    var body: some View {
        HStack(spacing: 3) {
            ForEach(0..<5) { index in
                RoundedRectangle(cornerRadius: 2)
                    .fill(
                        index < signalStrength 
                            ? LinearGradient(
                                colors: [BroadcastTheme.broadcastRed, BroadcastTheme.neonCyan],
                                startPoint: .bottom,
                                endPoint: .top
                            )
                            : LinearGradient(
                                colors: [Color.white.opacity(0.1), Color.white.opacity(0.05)],
                                startPoint: .bottom,
                                endPoint: .top
                            )
                    )
                    .frame(width: 8, height: CGFloat(10 + index * 6))
                    .scaleEffect(y: animateBars ? 1.0 : 0.3, anchor: .bottom)
                    .animation(
                        .spring(response: 0.5, dampingFraction: 0.6)
                        .delay(Double(index) * 0.05),
                        value: animateBars
                    )
            }
        }
        .onAppear {
            animateBars = true
        }
    }
}

struct BroadcastActionButton: View {
    let title: String
    let icon: String
    let action: () -> Void
    @State private var isPressed: Bool = false
    @State private var ringScale: Double = 1
    @State private var ringOpacity: Double = 0
    
    var body: some View {
        Button(action: {
            action()
            triggerRingAnimation()
        }) {
            ZStack {
                // Expanding ring effect
                Circle()
                    .stroke(BroadcastTheme.broadcastRed, lineWidth: 2)
                    .scaleEffect(ringScale)
                    .opacity(ringOpacity)
                
                // Main button content  
                HStack(spacing: 8) {
                    Image(systemName: icon)
                        .font(.system(size: 14, weight: .bold))
                    
                    Text(title)
                        .font(.system(size: 11, weight: .black, design: .monospaced))
                        .tracking(1.5)
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(
                    ZStack {
                        BroadcastTheme.broadcastRed
                        LinearGradient(
                            colors: [
                                .white.opacity(0.2),
                                .clear,
                                .black.opacity(0.2)
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    }
                )
                .clipShape(Capsule())
                .overlay(
                    Capsule()
                        .stroke(BroadcastTheme.broadcastRed.opacity(0.5), lineWidth: 1)
                )
                .scaleEffect(isPressed ? 0.95 : 1)
                .shadow(
                    color: BroadcastTheme.broadcastRed.opacity(0.4),
                    radius: isPressed ? 5 : 15,
                    y: 5
                )
            }
        }
        .buttonStyle(PlainButtonStyle())
        .scaleEffect(isPressed ? 0.95 : 1)
        .onLongPressGesture(minimumDuration: 0, maximumDistance: .infinity, pressing: { pressing in
            isPressed = pressing
        }, perform: {})
    }
    
    private func triggerRingAnimation() {
        ringScale = 1
        ringOpacity = 1
        
        withAnimation(.easeOut(duration: 0.8)) {
            ringScale = 2
            ringOpacity = 0
        }
    }
}