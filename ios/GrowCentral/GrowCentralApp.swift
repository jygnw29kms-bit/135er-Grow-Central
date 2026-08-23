import SwiftUI

@main
struct GrowCentralApp: App {
    @StateObject private var settings = ConnectionSettings()
    @StateObject private var webGUI = WebGUIStore()
    var body: some Scene {
        WindowGroup {
            WebGUIView().environmentObject(settings).environmentObject(webGUI)
                .modifier(GCBackground()).preferredColorScheme(.dark)
        }
    }
}
