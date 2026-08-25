(() => {
  const frame = document.getElementById('legacyFrame');
  const topActions = document.querySelector('.top-actions');
  const systemGrid = document.querySelector('#systemPanel .system-grid');

  function injectLegacyFixes() {
    try {
      const doc = frame?.contentDocument;
      if (!doc || doc.getElementById('gc-mobile-runtime-fix')) return;
      const link = doc.createElement('link');
      link.id = 'gc-mobile-runtime-fix';
      link.rel = 'stylesheet';
      link.href = '/static/mobile_runtime_fix.css?v=1';
      doc.head.appendChild(link);
      doc.documentElement.style.webkitTextSizeAdjust = '100%';
      doc.documentElement.style.textSizeAdjust = '100%';
    } catch (_) {}
  }

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
      const response = await fetch('/api/cloud/status?ts=' + Date.now(), {cache:'no-store', headers:{Accept:'application/json'}});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const x = await response.json();
      const state = !x.enabled ? 'DEAKTIVIERT' : x.connected ? 'VERBUNDEN' : x.service_active ? 'GETRENNT' : 'DIENST AUS';
      if (pill) {
        pill.textContent = x.connected ? `CLOUD ✓ ${x.host || 'ONLINE'}` : `CLOUD ${state}`;
        pill.classList.toggle('online', !!x.connected);
        pill.classList.toggle('offline', !!x.enabled && !x.connected);
        pill.title = x.detail || '';
      }
      setText('cloudState', state);
      setText('cloudHost', x.host || '--');
      setText('cloudOrigin', x.origin || '--');
      setText('cloudSite', x.site_id || '--');
      setText('cloudLatency', Number.isFinite(x.latency_ms) ? `${x.latency_ms} ms` : '--');
    } catch (error) {
      if (pill) {
        pill.textContent = 'CLOUD STATUS FEHLER';
        pill.classList.remove('online');
        pill.classList.add('offline');
      }
      setText('cloudState', 'STATUS FEHLER');
    }
  }

  refreshCloud();
  setInterval(refreshCloud, 30000);
  window.addEventListener('gc:view', refreshCloud);
})();
