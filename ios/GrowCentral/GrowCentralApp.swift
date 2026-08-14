import SwiftUI

@main
struct GrowCentralApp: App {
    @StateObject private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase
    var body: some Scene {
        WindowGroup {
            RootView().environmentObject(model).modifier(GCBackground())
                .task { await model.load(); await model.refresh() }
                .onChange(of: scenePhase) { phase in if phase == .active { Task { await model.refresh() } } }
        }
    }
}

struct RootView: View {
    @EnvironmentObject var model: AppModel
    var body: some View {
        TabView(selection: $model.selectedTab) {
            NavigationStack { DashboardView() }.tabItem { Label("Dashboard", systemImage: "gauge.with.dots.needle.67percent") }.tag(0)
            NavigationStack { DevicesView() }.tabItem { Label("Geräte", systemImage: "powerplug") }.tag(1)
            NavigationStack { HistoryView() }.tabItem { Label("Auswertung", systemImage: "chart.xyaxis.line") }.tag(2)
            NavigationStack { BluetoothView(bluetooth: model.bluetooth) }.tabItem { Label("Bluetooth", systemImage: "antenna.radiowaves.left.and.right") }.tag(3)
            NavigationStack { SettingsView() }.tabItem { Label("System", systemImage: "gearshape") }.tag(4)
        }
        .onChange(of: model.selectedTab) { _ in Task { await model.refresh() } }
        .alert("135er Grow Central", isPresented: Binding(get: { model.message != nil }, set: { if !$0 { model.message = nil } })) {
            Button("OK") { model.message = nil }
        } message: { Text(model.message ?? "") }
    }
}

struct GCTitle: View {
    let title: String
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("135ER GROW CENTRAL · IOS").font(.caption2.monospaced().weight(.bold)).foregroundStyle(GCTheme.green)
            Text(title).font(.title2.monospaced())
        }.frame(maxWidth: .infinity, alignment: .leading)
    }
}
