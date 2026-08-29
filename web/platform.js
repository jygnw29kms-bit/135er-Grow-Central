(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const titles = {overview:'Übersicht',grow:'Growboxen',devices:'Geräte',automation:'Automationen',camera:'Kamera',energy:'Energie',system:'System'};
  const state = {platform:null,runtime:null,smart:null,discovered:[],filter:'all',mode:localStorage.getItem('gc.mode') === 'advanced' ? 'advanced' : 'simple'};

  async function api(path, options={}) {
    const response = await fetch(path, {cache:'no-store', ...options});
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }
  function toast(message, type='') {
    const node = $('toast');
    node.textContent = message;
    node.className = `toast show ${type}`.trim();
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => node.className = 'toast', 3200);
  }
  function setText(id, value, fallback='—') { const node=$(id); if(node) node.textContent = value ?? fallback; }
  function fmt(value, digits=1) { return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—'; }
  function supportLabel(value='') { return ({detected:'DETECTED',experimental:'EXPERIMENTAL',compatible:'COMPATIBLE',validated:'VALIDATED',certified:'CERTIFIED'})[value] || String(value).toUpperCase(); }

  function setMode(mode) {
    state.mode = mode === 'advanced' ? 'advanced' : 'simple';
    localStorage.setItem('gc.mode', state.mode);
    document.documentElement.dataset.mode = state.mode;
    $('simpleMode').classList.toggle('active', state.mode === 'simple');
    $('advancedMode').classList.toggle('active', state.mode === 'advanced');
    const active = document.querySelector('.view.active');
    if (state.mode === 'simple' && active?.classList.contains('advanced-only')) openView('overview');
  }
  function openView(id) {
    if (state.mode === 'simple' && ['energy','system'].includes(id)) id = 'overview';
    document.querySelectorAll('.view').forEach((node) => node.classList.toggle('active', node.id === id));
    document.querySelectorAll('#mainNav [data-view]').forEach((node) => node.classList.toggle('active', node.dataset.view === id));
    setText('pageTitle', titles[id] || 'Grow Central');
    if (id === 'devices') renderDeviceTable();
    if (id === 'automation') loadAutomations();
    if (id === 'camera') loadCamera();
    if (id === 'energy') loadEnergy(true);
    if (id === 'system') loadSystem();
  }

  function providerCard(provider) {
    const runtime = state.runtime?.providers?.find((item) => item.id === provider.id);
    const runtimeLabel = runtime ? (runtime.error ? 'RUNTIME FEHLER' : `${runtime.device_count} GERÄT(E)`) : 'NICHT AKTIV';
    return `<article class="provider-card"><header><h4>${esc(provider.name)}</h4><span class="support ${esc(provider.support)}">${supportLabel(provider.support)}</span></header><p>${esc(provider.notes || 'Grow-Central Provider')}</p><div class="tags"><span>${esc(runtimeLabel)}</span>${(provider.transports||[]).map((x)=>`<span>${esc(x)}</span>`).join('')}</div></article>`;
  }
  function miniDevice(row) {
    const s = row.state || {};
    const bits = [];
    if (s.power_w != null) bits.push(`${fmt(s.power_w)} W`);
    if (s.temperature != null) bits.push(`${fmt(s.temperature)} °C`);
    if (s.humidity != null) bits.push(`${fmt(s.humidity,0)} %`);
    if (s.energy_wh != null) bits.push(`${fmt(Number(s.energy_wh)/1000,2)} kWh`);
    return `<div class="device-row"><div><strong>${esc(row.name || row.id)}</strong><small>${esc([row.adapter || row.provider_id, ...bits].filter(Boolean).join(' · ') || 'Gerät')}</small></div><span class="state-badge ${row.online === false ? 'offline' : ''}">${row.online === false ? 'OFFLINE' : 'ONLINE'}</span></div>`;
  }
  function discoveredRow(row) {
    const caps = (row.capabilities || []).slice(0,4).join(', ');
    return `<div class="device-table-row" data-kind="${esc(row.device_class || '')}" data-online="true"><div><strong>${esc(row.name || row.native_id)}</strong><small>${esc(row.model || row.native_id)}</small></div><span>${esc(row.device_class || 'device')}</span><span>${esc(row.provider_id)}</span><span><b class="state-badge">ERKANNT</b><small>${esc(caps || row.transport || '')}</small></span></div>`;
  }
  function legacyTableRow(row) {
    const s=row.state||{};
    const values=[];
    if(s.power_w!=null)values.push(`${fmt(s.power_w)} W`);
    if(s.temperature!=null)values.push(`${fmt(s.temperature)} °C`);
    if(s.humidity!=null)values.push(`${fmt(s.humidity,0)} %`);
    return `<div class="device-table-row" data-kind="${esc(row.type || 'switch')}" data-online="${row.online!==false}"><div><strong>${esc(row.name||row.id)}</strong><small>${esc(row.id||'')}</small></div><span>${esc(row.type||'device')}</span><span>${esc(row.adapter||'legacy')}</span><span><b class="state-badge ${row.online===false?'offline':''}">${row.online===false?'OFFLINE':'ONLINE'}</b><small>${esc(values.join(' · ')||'keine Live-Werte')}</small></span></div>`;
  }
  function renderDeviceTable() {
    const legacy = state.smart?.devices || [];
    let discovered = state.discovered || [];
    if (state.filter === 'online') discovered = discovered;
    else if (!['all','provider'].includes(state.filter)) discovered = discovered.filter((x)=>x.device_class===state.filter);
    let legacyFiltered = legacy;
    if (state.filter === 'online') legacyFiltered = legacy.filter((x)=>x.online !== false);
    else if (!['all','provider'].includes(state.filter)) legacyFiltered = legacy.filter((x)=>(x.type||'switch')===state.filter);
    const html = [...legacyFiltered.map(legacyTableRow), ...discovered.map(discoveredRow)].join('');
    $('deviceList').innerHTML = html || '<div class="empty">Keine Geräte für diesen Filter.</div>';
  }

  function updateHeadline(healthOk, runtimeErrors=0) {
    const banner=$('statusBanner');
    banner.classList.remove('warning','error');
    if (!healthOk) {
      banner.classList.add('error'); setText('headline','Lokaler Core nicht erreichbar'); setText('headlineSub','Bitte Raspberry Pi und Dienststatus prüfen.'); return;
    }
    if (runtimeErrors) {
      banner.classList.add('warning'); setText('headline','Grow Central läuft mit Hinweisen'); setText('headlineSub',`${runtimeErrors} Provider melden aktuell einen Verbindungsfehler.`); return;
    }
    setText('headline','Alles läuft normal'); setText('headlineSub','Lokaler Core ist bereit. Geräte werden herstellerunabhängig verwaltet.');
  }

  async function loadPlatform() {
    try {
      const [platform, runtime] = await Promise.all([api('/api/devices/platform'), api('/api/devices/runtime')]);
      state.platform=platform; state.runtime=runtime;
      setText('providerCount', `${platform.providers.length} Provider`);
      const errors=(runtime.providers||[]).filter((x)=>x.error).length;
      const available=(runtime.providers||[]).filter((x)=>!x.error).length;
      setText('runtimeCounter', `${available}/${(runtime.providers||[]).length}`);
      $('runtimePreview').innerHTML=(runtime.providers||[]).slice(0,7).map((x)=>`<div class="health-row"><div><strong>${esc(x.name)}</strong><small>${x.error?esc(x.error):`${x.device_count} Gerät(e) erkannt`}</small></div><span class="state-badge ${x.error?'warning':''}">${x.error?'CHECK':'READY'}</span></div>`).join('')||'<div class="empty">Keine Runtime-Provider.</div>';
      $('runtimeFull').innerHTML=(runtime.providers||[]).map((x)=>`<div class="health-row"><div><strong>${esc(x.name)}</strong><small>${x.error?esc(x.error):`${x.device_count} Gerät(e) · ${supportLabel(x.support)}`}</small></div><span class="state-badge ${x.error?'warning':''}">${x.error?'FEHLER':'BEREIT'}</span></div>`).join('');
      $('providerGrid').innerHTML=platform.providers.map(providerCard).join('');
      return errors;
    } catch (error) {
      $('runtimePreview').innerHTML=`<div class="empty">Device Runtime: ${esc(error.message)}</div>`;
      return 1;
    }
  }

  async function loadSmart(refresh=false) {
    try {
      const data=await api(`/api/v1/smarthome/overview${refresh?'?refresh=true':''}`); state.smart=data;
      const summary=data.summary||{}; const rows=data.devices||[];
      const power=summary.power_w;
      setText('power', Number.isFinite(Number(power)) ? fmt(power) : '—');
      setText('powerHint', Number.isFinite(Number(power)) ? `${summary.online||0} online` : 'keine Messgeräte');
      setText('deviceCounter', `${summary.online||0} / ${summary.configured||rows.length||0}`);
      setText('energyNow', Number.isFinite(Number(power)) ? fmt(power) : '—');
      setText('energyTotalSmall', `${Number.isFinite(Number(summary.energy_wh)) ? fmt(Number(summary.energy_wh)/1000,3) : '—'} kWh`);
      $('devicePreview').innerHTML=rows.length?rows.slice(0,7).map(miniDevice).join(''):'<div class="empty">Noch keine lokalen Geräte registriert.</div>';
      renderDeviceTable();
      return data;
    } catch (error) { $('devicePreview').innerHTML=`<div class="empty">Gerätedaten: ${esc(error.message)}</div>`; return null; }
  }

  async function loadClimate() {
    try {
      const data=await api('/api/status'); const notifications=(data.notifications||[]).slice().reverse();
      let temp=null,rh=null,vpd=null;
      for(const item of notifications){
        if(temp==null && Number.isFinite(Number(item.temperature)))temp=Number(item.temperature);
        if(rh==null && Number.isFinite(Number(item.humidity)))rh=Number(item.humidity);
        if(vpd==null && Number.isFinite(Number(item.vpd)))vpd=Number(item.vpd);
      }
      if(vpd==null && temp!=null && rh!=null){const es=.6108*Math.exp(17.27*temp/(temp+237.3));vpd=es*(1-rh/100);}
      setText('temp',temp==null?'—':fmt(temp)); setText('rh',rh==null?'—':fmt(rh,0)); setText('vpd',vpd==null?'—':fmt(vpd,2));
      setText('tempHint',temp==null?'keine Daten':'Live-Wert'); setText('rhHint',rh==null?'keine Daten':'Live-Wert'); setText('vpdHint',vpd==null?'keine Daten':'berechnet / Sensor');
    } catch (_) {}
  }

  async function universalDiscover() {
    const button=$('discoverBtn'); button.disabled=true; button.textContent='Suche läuft…';
    try { const result=await api('/api/devices/discover?timeout=5'); state.discovered=result.devices||[]; renderDeviceTable(); const errors=result.errors||[]; toast(`${state.discovered.length} Gerät(e) erkannt${errors.length?` · ${errors.length} Provider mit Hinweis`:''}`,errors.length?'':'success'); }
    catch(error){toast(`Discovery fehlgeschlagen: ${error.message}`,'error');}
    finally{button.disabled=false;button.textContent='Geräte suchen';}
  }

  async function loadAutomations(){try{const d=await api('/api/v1/automations');const rows=d.automations||[];$('automationList').innerHTML=rows.length?rows.map((r)=>`<article class="rule-card"><div><strong>${esc(r.name||'Automation')}</strong><small>${esc([r.trigger,r.device_id].filter(Boolean).join(' · '))}</small></div><span class="state-badge ${r.enabled===false?'offline':''}">${r.enabled===false?'PAUSIERT':'AKTIV'}</span></article>`).join(''):'<div class="empty">Noch keine lokalen Regeln angelegt.</div>';}catch(e){$('automationList').innerHTML=`<div class="empty">Automationen: ${esc(e.message)}</div>`;}}
  async function loadCamera(){try{const d=await api('/api/v1/camera/status?refresh=true');const rows=d.devices||[];$('cameraGrid').innerHTML=rows.length?rows.map((r)=>`<article class="camera-card"><div class="camera-placeholder">◉</div><footer><strong>${esc(r.c920_match?'Logitech C920':r.name||r.device||'Kamera')}</strong><small>${esc(r.capture_capable?'Capture bereit':'Gerät erkannt · prüfen')}</small></footer></article>`).join(''):'<div class="empty">Keine lokale Kamera erkannt.</div>';}catch(e){$('cameraGrid').innerHTML=`<div class="empty">Kamera: ${esc(e.message)}</div>`;}}
  async function loadEnergy(refresh=false){const d=await loadSmart(refresh);if(!d)return;const s=d.summary||{};setText('energyPower',Number.isFinite(Number(s.power_w))?fmt(s.power_w):'—');setText('energyTotal',Number.isFinite(Number(s.energy_wh))?fmt(Number(s.energy_wh)/1000,3):'—');setText('energyOnline',`${s.online||0} / ${s.configured||0}`);setText('energyOn',s.switched_on??'—');$('energyDevices').innerHTML=(d.devices||[]).length?(d.devices||[]).map(miniDevice).join(''):'<div class="empty">Keine Energiedaten verfügbar.</div>';}
  async function loadSystem(){try{const d=await api('/api/v1/system/info');const values=[['Hostname',d.hostname],['IPv4',d.primary_ipv4],['Version',d.version],['Build',d.build],['Hardware',d.model],['OS',d.operating_system],['Uptime',d.uptime?.display]];$('systemGrid').innerHTML=values.map(([k,v])=>`<div class="system-item"><span>${esc(k)}</span><b>${esc(v||'—')}</b></div>`).join('');}catch(e){$('systemGrid').innerHTML=`<div class="empty">System: ${esc(e.message)}</div>`;}}

  async function refreshAll(showToast=false){
    setText('lastUpdate','wird aktualisiert…');
    const healthPromise=api('/api/health');
    const [healthResult,platformResult]=await Promise.allSettled([healthPromise,loadPlatform(),loadSmart(true),loadClimate()]);
    const healthOk=healthResult.status==='fulfilled' && healthResult.value?.ok===true;
    const runtimeErrors=platformResult.status==='fulfilled'?Number(platformResult.value||0):1;
    $('coreDot').className=healthOk?'online':'error'; setText('coreLabel',healthOk?'LOCAL ONLINE':'CORE OFFLINE'); updateHeadline(healthOk,runtimeErrors);
    setText('lastUpdate',new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}));
    if(showToast)toast(healthOk?'Daten aktualisiert':'Core nicht erreichbar',healthOk?'success':'error');
  }

  document.querySelectorAll('#mainNav [data-view],[data-open]').forEach((node)=>node.addEventListener('click',()=>openView(node.dataset.view||node.dataset.open)));
  document.querySelectorAll('.filterbar [data-filter]').forEach((node)=>node.addEventListener('click',()=>{document.querySelectorAll('.filterbar [data-filter]').forEach((x)=>x.classList.remove('active'));node.classList.add('active');state.filter=node.dataset.filter;renderDeviceTable();}));
  $('simpleMode').addEventListener('click',()=>setMode('simple')); $('advancedMode').addEventListener('click',()=>setMode('advanced'));
  $('refreshBtn').addEventListener('click',()=>refreshAll(true)); $('systemRefresh')?.addEventListener('click',loadSystem); $('discoverBtn').addEventListener('click',universalDiscover);
  setMode(state.mode); refreshAll(false); setInterval(()=>refreshAll(false),60000);
})();
