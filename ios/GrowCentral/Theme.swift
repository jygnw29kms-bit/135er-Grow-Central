import SwiftUI

enum GCTheme {
    static let background = Color(red: 0.008, green: 0.027, blue: 0.039)
    static let surface = Color(red: 0.025, green: 0.067, blue: 0.086)
    static let line = Color(red: 0.106, green: 0.224, blue: 0.255)
    static let green = Color(red: 0.612, green: 1.0, blue: 0.125)
    static let cyan = Color(red: 0.086, green: 0.937, blue: 0.945)
    static let muted = Color(red: 0.50, green: 0.59, blue: 0.61)
    static let danger = Color(red: 1.0, green: 0.36, blue: 0.45)
}

struct GCBackground: ViewModifier {
    func body(content: Content) -> some View {
        content.background(
            RadialGradient(colors: [Color(red: 0.035, green: 0.125, blue: 0.16), GCTheme.background], center: .center, startRadius: 20, endRadius: 700)
                .ignoresSafeArea()
        ).preferredColorScheme(.dark).tint(GCTheme.green)
    }
}
