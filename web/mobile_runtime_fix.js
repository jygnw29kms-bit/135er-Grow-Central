(() => {
  const frame = document.getElementById('legacyFrame');
  const topActions = document.querySelector('.top-actions');
  const systemGrid = document.querySelector('#systemPanel .system-grid');

  function syncViewportHeight() {
    const viewport = window.visualViewport;
    const height = Math.max(1, Math.round(viewport ? viewport.height : window.innerHeight));
    document.documentElement.style.setProperty('--gc-viewport-height', `${height}px`);
  }

  function injectLegacyFixes() {
    try {
      const doc = frame?.contentDocument;
      if (!doc) return;
      if (!doc.getElementById('gc-mobile-runtime-fix')) {
        const link = doc.createElement('link');
        link.id = 'gc-mobile-runtime-fix';
        link.rel = 'stylesheet';
        link.href = '/static/mobile_runtime_fix.css?v=4';
        doc.head.appendChild(link);
      }
      doc.documentElement.style.webkitTextSizeAdjust = '100%';
      doc.documentElement.style.textSizeAdjust = '100%';
      doc.documentElement.style.maxWidth = '100%';
      if (doc.body) {
        doc.body.style.maxWidth = '100%';
        doc.body.style.overflowX = 'hidden';
      }
    } catch (_) {}
  }

  syncViewportHeight();
  window.addEventListener('resize', syncViewportHeight, {passive:true});
  window.addEventListener('orientationchange', syncViewportHeight, {passive:true});
  window.visualViewport?.addEventListener('resize', syncViewportHeight, {passive:true});
  window.visualViewport?.addEventListener('scroll', syncViewportHeight, {passive:true});

  if (frame) {
    frame.addEventListener('load', injectLegacyFixes);
    injectLegacyFixes();
  }

  let pill = document.getElementById('cloudStatusPill');
  if (!pill && topActions) {
    pill = document.createElement('div');
    pill.id = 'cloudStatusPill';
    pill.className = 'cloud-pill';
    pill.textContent = 'CLOUD …';
    topActions.prepend(pill);
  }

  let card = document.getElementById('cloudStatusCard');
  if (!card && systemGrid) {
    card = document.createElement('article');
    card.id = 'cloudStatusCard';
    card.className = 'system-card cloud-card';
    card.innerHTML = '<div class="card-head"><span>CLOUD</span><b>LIVE LINK</b></div><div class="cloud-meta"><div><span>Status</span><b id="cloudState">Prüfe…</b></div><div><span>Cloudhost</span><b id="cloudHost">--</b></div><div><span>Endpoint</span><b id="cloudOrigin">--</b></div><div><span>Site</span><b id="cloudSite">--</b></div><div><span>Latenz</span><b id="cloudLatency">--</b></div></div>';
    systemGrid.appendChild(card);
  }

  const setText = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };

  async function refreshCloud() {
    try {
      const response = await fetch('/api/cloud/status?ts=' + Date.now(), {
        cache:'no-store',
        credentials:'same-origin',
        headers:{Accept:'application/json'}
      });
      if (response.redirected && new URL(response.url).pathname === '/login') {
        throw new Error('GUI-Sitzung abgelaufen');
      }
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) throw new Error('Ungültige Cloud-Status-Antwort');
      const x = await response.json();

      let state = 'DEAKTIVIERT';
      if (x.enabled && x.service_active && x.connected) state = 'VERBUNDEN';
      else if (x.enabled && x.service_active) state = 'AKTIV';
      else if (x.enabled) state = 'DIENST AUS';

      if (pill) {
        if (x.connected) pill.textContent = `CLOUD ✓ ${x.host || 'ONLINE'}`;
        else if (x.service_active) pill.textContent = 'CLOUD LINK AKTIV';
        else pill.textContent = `CLOUD ${state}`;
        pill.classList.toggle('online', !!x.service_active);
        pill.classList.toggle('offline', !!x.enabled && !x.service_active);
        pill.title = x.connected ? (x.detail || 'Cloud verbunden') : `${x.detail || 'Cloud-Verbindung noch nicht bestätigt'} · Dienst ${x.service_active ? 'aktiv' : 'inaktiv'}`;
      }

      const stateDetail = x.service_active && !x.connected ? `${state} · CLOUD GETRENNT` : state;
      setText('cloudState', stateDetail);
      setText('cloudHost', x.host || '--');
      setText('cloudOrigin', x.origin || '--');
      setText('cloudSite', x.site_id || '--');
      setText('cloudLatency', Number.isFinite(x.latency_ms) ? `${x.latency_ms} ms` : '--');
    } catch (error) {
      if (pill) {
        pill.textContent = 'CLOUD STATUS NICHT VERFÜGBAR';
        pill.classList.remove('online');
        pill.classList.add('offline');
        pill.title = error?.message || 'Cloud-Status konnte nicht gelesen werden';
      }
      setText('cloudState', 'STATUS NICHT VERFÜGBAR');
    }
  }

  refreshCloud();
  setInterval(refreshCloud, 15000);
  window.addEventListener('gc:view', () => { syncViewportHeight(); injectLegacyFixes(); refreshCloud(); });
  window.addEventListener('online', refreshCloud);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshCloud(); });
})();
