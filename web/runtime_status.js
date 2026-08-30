(() => {
  const byId = (id) => document.getElementById(id);

  function apply(data) {
    const ok = data?.state === 'ok';
    const warning = data?.state === 'warning';
    const provisioned = data?.provisioned === true;
    const cloud = data?.cloud || {};
    const providers = data?.device_runtime || {};

    const desktopBanner = byId('statusBanner');
    if (desktopBanner) {
      desktopBanner.classList.toggle('error', !data?.ok);
      desktopBanner.classList.toggle('warning', warning);
      const headline = byId('headline');
      const sub = byId('headlineSub');
      if (headline) headline.textContent = !data?.ok ? 'Grow Central benötigt Aufmerksamkeit' : warning ? 'Grow Central läuft mit Hinweisen' : 'Alles läuft normal';
      if (sub) sub.textContent = !provisioned
        ? 'Die Ersteinrichtung ist noch nicht vollständig abgeschlossen.'
        : cloud.enabled && cloud.state !== 'connected'
          ? `Lokaler Betrieb ist bereit · Cloud ${cloud.state || 'nicht verbunden'}.`
          : `Lokaler Core bereit · ${providers.provider_count || 0} Provider aktiv.`;
    }

    const coreDot = byId('coreDot');
    if (coreDot) coreDot.className = data?.ok ? (warning ? 'warning' : 'online') : 'error';
    const coreLabel = byId('coreLabel');
    if (coreLabel) coreLabel.textContent = data?.ok ? (warning ? 'LOCAL · HINWEIS' : 'LOCAL ONLINE') : 'CORE CHECK';

    const mobileStatus = byId('mStatus');
    if (mobileStatus) {
      mobileStatus.classList.toggle('warning', warning);
      mobileStatus.classList.toggle('error', !data?.ok);
    }
    const mobileHeadline = byId('mHeadline');
    const mobileSub = byId('mHeadlineSub');
    if (mobileHeadline) mobileHeadline.textContent = !data?.ok ? 'Prüfung erforderlich' : warning ? 'Lokal bereit' : 'Alles läuft normal';
    if (mobileSub) mobileSub.textContent = !provisioned
      ? 'Ersteinrichtung noch offen.'
      : cloud.enabled && cloud.state !== 'connected'
        ? `Cloud ${cloud.state || 'nicht verbunden'} · lokale Steuerung aktiv.`
        : `${providers.provider_count || 0} Provider · lokale Steuerung aktiv.`;
    const connection = byId('connectionLabel');
    if (connection) connection.textContent = data?.ok ? 'LOCAL' : 'CHECK';

    document.documentElement.dataset.runtime = data?.state || 'unknown';
    window.GrowCentralRuntime = data;
  }

  async function refresh() {
    try {
      const response = await fetch('/api/runtime/health', {cache: 'no-store'});
      if (!response.ok) throw new Error(String(response.status));
      apply(await response.json());
    } catch (_) {
      apply({ok: false, state: 'error', provisioned: false, cloud: {}, device_runtime: {provider_count: 0}});
    }
  }

  window.addEventListener('gc:refresh', refresh);
  refresh();
  setInterval(refresh, 15000);
})();
