import SwiftUI
import WebKit

struct WebViewRepresentable: UIViewRepresentable {
    let webView: WKWebView
    func makeUIView(context: Context) -> WKWebView { webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}

struct WebGUIView: View {
    @EnvironmentObject private var settings: ConnectionSettings
    @EnvironmentObject private var store: WebGUIStore
    @Environment(\.scenePhase) private var scenePhase
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            ZStack {
                WebViewRepresentable(webView: store.webView).ignoresSafeArea(edges: .bottom)
                if store.failed { offlineView }
                if store.loading {
                    ProgressView().tint(GCTheme.green).padding(14)
                        .background(.ultraThinMaterial).clipShape(RoundedRectangle(cornerRadius: 10))
                }
            }
            .navigationTitle(settings.mode.label)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Menu {
                        Button("Heimnetz verwenden") { switchMode(.local) }
                        Button("Server verwenden") { switchMode(.server) }.disabled(!settings.serverConfigured)
                    } label: {
                        Label(settings.mode == .local ? "LOCAL" : "SERVER",
                              systemImage: settings.mode == .local ? "house.lodge" : "globe.europe.africa")
                    }
                }
                ToolbarItemGroup(placement: .navigationBarTrailing) {
                    Button { store.reloadLive() } label: { Image(systemName: "arrow.clockwise") }
                    Button { showSettings = true } label: { Image(systemName: "gearshape") }
                }
            }
            .sheet(isPresented: $showSettings) {
                ConnectionSettingsView().environmentObject(settings).environmentObject(store)
            }
            .onAppear { connect() }
            .onChange(of: scenePhase) { phase in if phase == .active { store.reloadLive() } }
        }.tint(GCTheme.green)
    }

    private var offlineView: some View {
        VStack(spacing: 16) {
            Image(systemName: "wifi.exclamationmark").font(.system(size: 42)).foregroundStyle(GCTheme.danger)
            Text(settings.mode == .local ? "Lokale Zentrale nicht erreichbar" : "Server nicht erreichbar")
                .font(.headline.monospaced()).multilineTextAlignment(.center)
            Text(store.errorText).foregroundStyle(GCTheme.muted).multilineTextAlignment(.center)
            Button("Erneut prüfen") { connect(force: true) }.buttonStyle(.borderedProminent)
            if settings.mode == .server {
                Button("Zum Heimnetz wechseln") { switchMode(.local) }.buttonStyle(.bordered)
            } else if settings.serverConfigured {
                Button("Serverzugriff verwenden") { switchMode(.server) }.buttonStyle(.bordered)
            }
        }
        .padding(28).frame(maxWidth: 430)
        .background(GCTheme.surface).overlay(RoundedRectangle(cornerRadius: 14).stroke(GCTheme.line))
        .clipShape(RoundedRectangle(cornerRadius: 14)).padding()
    }

    private func connect(force: Bool = false) {
        guard let url = settings.activeURL else { showSettings = true; return }
        store.connect(to: url, force: force)
    }

    private func switchMode(_ mode: ConnectionSettings.Mode) {
        settings.mode = mode; connect(force: true)
    }
}

struct ConnectionSettingsView: View {
    @EnvironmentObject private var settings: ConnectionSettings
    @EnvironmentObject private var store: WebGUIStore
    @Environment(\.dismiss) private var dismiss
    @State private var validation = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Heimnetz · Raspberry Pi / lokaler Server") {
                    TextField("http://135er-Grow-Central.local/", text: $settings.localAddress)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                    Text("Direkter Zugriff im selben WLAN/LAN. Gerätefunktionen laufen auf dem Pi bzw. lokalen Server.")
                        .font(.caption).foregroundStyle(GCTheme.muted)
                }
                Section("Optionaler Server · Zugriff von überall") {
                    TextField("https://grow.example.de/", text: $settings.serverAddress)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                    Text("Für externen Zugriff wird ausschließlich HTTPS akzeptiert. Login und Rechte stellt die Serverversion bereit.")
                        .font(.caption).foregroundStyle(GCTheme.muted)
                }
                Section("Verbindung") {
                    Picker("Aktiver Zugang", selection: $settings.mode) {
                        ForEach(ConnectionSettings.Mode.allCases) { mode in Text(mode.label).tag(mode) }
                    }
                    if !validation.isEmpty { Text(validation).foregroundStyle(GCTheme.danger) }
                }
                Section {
                    Button("Speichern und verbinden") {
                        guard let url = settings.activeURL else {
                            validation = settings.mode == .server
                                ? "Bitte eine gültige HTTPS-Serveradresse eintragen."
                                : "Bitte eine gültige lokale Adresse eintragen."
                            return
                        }
                        store.connect(to: url, force: true); dismiss()
                    }
                }
                Section("Architektur") {
                    Text("Die App ist nur die WebGUI. FRITZ!, Tapo, Mars Hydro, Kamera, History und Automationen bleiben vollständig in Grow Central Local bzw. der optionalen Serverversion.")
                        .font(.caption).foregroundStyle(GCTheme.muted)
                }
            }
            .navigationTitle("Verbindungen")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Schließen") { dismiss() } } }
        }.preferredColorScheme(.dark)
    }
}
