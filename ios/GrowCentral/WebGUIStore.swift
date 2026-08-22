import Foundation
import Combine
import UIKit
import WebKit

@MainActor
final class WebGUIStore: NSObject, ObservableObject, WKNavigationDelegate, WKUIDelegate {
    @Published var loading = false
    @Published var failed = false
    @Published var errorText = ""
    @Published var pageTitle = "135er Grow Central"
    @Published var canGoBack = false
    @Published var canGoForward = false

    let webView: WKWebView
    private(set) var currentRoot: URL?

    override init() {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.allowsInlineMediaPlayback = true
        webView = WKWebView(frame: .zero, configuration: configuration)
        super.init()
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic
    }

    func connect(to url: URL, force: Bool = false) {
        currentRoot = url
        failed = false
        errorText = ""
        let policy: URLRequest.CachePolicy = force ? .reloadIgnoringLocalAndRemoteCacheData : .useProtocolCachePolicy
        webView.load(URLRequest(url: url, cachePolicy: policy, timeoutInterval: 15))
    }

    func reloadLive() {
        guard let url = webView.url ?? currentRoot else { return }
        connect(to: url, force: true)
    }

    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        loading = true; failed = false
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        loading = false; failed = false
        pageTitle = webView.title ?? "135er Grow Central"
        canGoBack = webView.canGoBack; canGoForward = webView.canGoForward
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { fail(error) }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { fail(error) }

    private func fail(_ error: Error) {
        loading = false; failed = true
        errorText = (error as NSError).code == NSURLErrorNotConnectedToInternet
            ? "Keine Netzwerkverbindung."
            : "Grow Central ist unter dieser Adresse nicht erreichbar."
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if ["http", "https"].contains(url.scheme?.lowercased() ?? "") {
            decisionHandler(.allow)
        } else {
            UIApplication.shared.open(url)
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if navigationAction.targetFrame == nil, let url = navigationAction.request.url { webView.load(URLRequest(url: url)) }
        return nil
    }
}
