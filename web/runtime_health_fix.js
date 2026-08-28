(() => {
  let consecutiveFailures = 0;

  function setVisualState(state, message = '') {
    if (typeof window.setPiConnectionState === 'function') {
      window.setPiConnectionState(state, message);
      return;
    }
    const offline = state === 'offline';
    document.body?.classList.toggle('pi-offline', offline);
    const overlay = document.getElementById('piOfflineOverlay');
    if (overlay) overlay.hidden = !offline;
    document.querySelectorAll('.live-state').forEach(el => {
      el.textContent = state === 'online' ? 'ONLINE' : state === 'checking' ? 'PRÜFE…' : 'PI OFFLINE';
    });
    document.querySelectorAll('.online-text').forEach(el => {
      el.textContent = state === 'online' ? 'LOCAL ONLINE' : state === 'checking' ? 'PRÜFE…' : 'PI OFFLINE';
    });
    const detail = document.getElementById('piOfflineDetail');
    if (detail && message) detail.textContent = message;
  }

  async function robustHealthCheck() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4500);
    try {
      const url = new URL('/api/health', window.location.origin);
      url.searchParams.set('live', Date.now().toString());
      const response = await fetch(url.toString(), {
        cache: 'no-store',
        credentials: 'same-origin',
        headers: {Accept: 'application/json'},
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const payload = await response.json();
      if (payload?.ok !== true) throw new Error('Health-Antwort ungültig');
      consecutiveFailures = 0;
      setVisualState('online');
      return true;
    } catch (error) {
      consecutiveFailures += 1;
      if (consecutiveFailures >= 3) {
        const reason = error?.name === 'AbortError' ? 'Zeitüberschreitung' : (error?.message || 'Verbindungsfehler');
        setVisualState('offline', `Der Raspberry Pi antwortet nicht (${reason}). Angezeigte Werte sind nicht aktuell.`);
      } else {
        setVisualState('checking');
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  // Replace the legacy one-shot check after the page scripts have loaded. A
  // short WLAN/mDNS transition must not mark a healthy Pi offline permanently.
  window.checkPiConnection = robustHealthCheck;
  window.gcRobustHealthCheck = robustHealthCheck;

  const retry = () => robustHealthCheck().catch(() => {});
  setTimeout(retry, 300);
  setInterval(retry, 5000);
  window.addEventListener('online', retry);
  window.addEventListener('pageshow', retry);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) retry(); });
})();
