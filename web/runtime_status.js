(() => {
  const byId = (id) => document.getElementById(id);

  let providerErrors=0;

  function apply(data) {
    const warning = data?.state === 'warning'||providerErrors>0;
    const provisioned = data?.provisioned === true;
    const cloud = data?.cloud || {};
    const providers = data?.device_runtime || {};

    const issues=[...new Set([...(data.warnings||[]),...(data.blockers||[])])];
    const count=issues.length+providerErrors;
    const summary=!data.ok?'System prüfen':warning?'Lokal bereit · Hinweise':'System bereit';
    const descriptions={setup_required:'Ersteinrichtung offen',setup_applying:'Einrichtung läuft',setup_warning:'Hinweis zur Einrichtung',setup_error:'Einrichtung fehlgeschlagen',cloud_not_connected:'Optionale Cloud nicht verbunden',device_runtime_empty:'Keine Geräteprovider registriert',runtime_unreachable:'Status nicht erreichbar'};
    const details=issues.map(key=>descriptions[key]||key);if(providerErrors)details.push(`${providerErrors} Provider mit Verbindungsfehler`);
    const label=byId('masterOnlineLabel');if(label){label.textContent=summary;label.parentElement.classList.toggle('warn',warning||!data.ok);label.parentElement.classList.toggle('online',data.ok&&!warning)}
    const masterWarning=byId('masterWarningLabel');if(masterWarning){masterWarning.textContent=`${count} Hinweis${count===1?'':'e'}`;masterWarning.parentElement.classList.toggle('warn',count>0);masterWarning.parentElement.title=details.join(' · ')||'Keine gemeldeten Hinweise'}
    const hero=byId('heroHealthLabel');if(hero)hero.textContent=summary;
    const masterSub=byId('headlineSub');if(masterSub&&!byId('statusBanner'))masterSub.textContent=details.join(' · ')||'Lokaler Core bereit; Geräte einzeln prüfen.';

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

    document.documentElement.dataset.runtime = !data.ok?'error':warning?'warning':'ok';
    window.GrowCentralRuntime = data;
  }

  async function refresh() {
    try {
      const response = await fetch('/api/runtime/health', {cache: 'no-store'});
      if (!response.ok) throw new Error(String(response.status));
      const data=await response.json();
      if(typeof data.ok!=='boolean'||!['ok','warning','error'].includes(data.state))throw new Error('Invalid runtime health response');
      apply(data);
    } catch (_) {
      apply({ok: false, state: 'error', provisioned: false, cloud: {}, device_runtime: {provider_count: 0}, blockers:['runtime_unreachable'], warnings:[]});
    }
  }

  window.addEventListener('gc:provider-health',event=>{providerErrors=Number(event.detail?.errors)||0;if(window.GrowCentralRuntime)apply(window.GrowCentralRuntime)});
  window.addEventListener('gc:core-refreshed',refresh);
  window.addEventListener('gc:refresh', refresh);
  refresh();
  setInterval(refresh, 15000);
})();
