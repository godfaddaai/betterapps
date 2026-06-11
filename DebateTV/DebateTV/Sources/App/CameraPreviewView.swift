import SwiftUI
import AVFoundation

#if canImport(UIKit)
import UIKit

struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> UIView {
        let view = CameraPreviewUIView()
        view.backgroundColor = .black
        if let previewLayer = view.layer as? AVCaptureVideoPreviewLayer {
            previewLayer.session = session
            previewLayer.videoGravity = .resizeAspectFill
        }
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {}
}

final class CameraPreviewUIView: UIView {
    override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
}
#elseif canImport(AppKit)
import AppKit

struct CameraPreviewView: NSViewRepresentable {
    let session: AVCaptureSession

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor.black.cgColor
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer?.addSublayer(previewLayer)
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        if let sublayers = nsView.layer?.sublayers {
            for layer in sublayers where layer is AVCaptureVideoPreviewLayer {
                layer.frame = nsView.bounds
            }
        }
    }
}
#endif

struct CameraUnavailablePlaceholder: View {
    var label: String = "Camera Preview"
    var icon: String = "video.fill"
    var accentColor: Color = BroadcastTheme.neonCyan

    var body: some View {
        ZStack {
            Color(red: 0.06, green: 0.06, blue: 0.08)

            VStack(spacing: 14) {
                Image(systemName: icon)
                    .font(.system(size: 36))
                    .foregroundStyle(accentColor.opacity(0.4))
                Text(label)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(accentColor.opacity(0.6))
            }
        }
    }
}