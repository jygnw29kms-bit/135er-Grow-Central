(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const titles = {overview:'Übersicht',grow:'Räume',devices:'Geräte',calibration:'Sensor-Kalibrierung',climate:'Klima',irrigation:'Bewässerung',lighting:'Beleuchtung',automation:'Zeitpläne',recipes:'Rezepte',growlog:'Growtagebuch',camera:'Live-Ansicht',recordings:'Aufnahmen',timelapse:'Zeitraffer',settings:'Einstellungen',applehome:'Apple Home',users:'Benutzer',backups:'Backups',updates:'Update',extensions:'Erweiterungen',energy:'Energie'};
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
  function fmt(value, digits=1) { return (value!=null&&value!==''&&Number.isFinite(Number(value))) ? Number(value).toFixed(digits) : '—'; }
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
    if (id === 'devices') {
      renderDeviceTable();
      marsWifiApRead();
      // Device-app owns a single BLE refresh cycle; never duplicate its scan.
      // Existing diagnostic functions remain available but not on an auto-timer.
    } else if (marsTimer!==null) {
      clearInterval(marsTimer);
      marsTimer=null;
    }
    if (id === 'automation') loadAutomations();
    if (id === 'camera') loadCamera();
    if (id === 'energy') loadEnergy(true);
    if (id === 'system') loadSystem();
    window.dispatchEvent(new CustomEvent('gc:view',{detail:{id}}));
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
    let discovered = (state.discovered || []).filter(x => x.provider_id !== "growcentral_esp32" || x.metadata?.trust_status === "TRUSTED");
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
    banner?.classList.remove('warning','error');
    if (!healthOk) {
      banner?.classList.add('error'); setText('headline','Lokaler Core nicht erreichbar'); setText('headlineSub','Bitte Raspberry Pi und Dienststatus prüfen.'); return;
    }
    if (runtimeErrors) {
      banner?.classList.add('warning'); setText('headline','Grow Central läuft mit Hinweisen'); setText('headlineSub',`${runtimeErrors} Provider melden aktuell einen Verbindungsfehler.`); return;
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
      window.dispatchEvent(new CustomEvent('gc:provider-health',{detail:{errors}}));
      return errors;
    } catch (error) {
      $('runtimePreview').innerHTML=`<div class="empty">Device Runtime: ${esc(error.message)}</div>`;
      window.dispatchEvent(new CustomEvent('gc:provider-health',{detail:{errors:1}}));
      return 1;
    }
  }

  async function loadSmart(refresh=false) {
    try {
      const data=await api(`/api/v1/smarthome/overview${refresh?'?refresh=true':''}`); state.smart=data;
      const summary=data.summary||{}; const rows=data.devices||[];
      const power=summary.power_w;
      setText('power', (power!=null&&power!==''&&Number.isFinite(Number(power))) ? fmt(power) : '—');
      setText('powerHint', (power!=null&&power!==''&&Number.isFinite(Number(power))) ? `${summary.online||0} online` : 'keine Messgeräte');
      setText('deviceCounter', `${summary.online||0} / ${summary.configured||rows.length||0}`);
      setText('energyNow', (power!=null&&power!==''&&Number.isFinite(Number(power))) ? fmt(power) : '—');
      setText('energyTotalSmall', `${(summary.energy_wh!=null&&summary.energy_wh!==''&&Number.isFinite(Number(summary.energy_wh))) ? fmt(Number(summary.energy_wh)/1000,3) : '—'} kWh`);
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
        if(temp==null && (item.temperature!=null&&item.temperature!==''&&Number.isFinite(Number(item.temperature))))temp=Number(item.temperature);
        if(rh==null && (item.humidity!=null&&item.humidity!==''&&Number.isFinite(Number(item.humidity))))rh=Number(item.humidity);
        if(vpd==null && (item.vpd!=null&&item.vpd!==''&&Number.isFinite(Number(item.vpd))))vpd=Number(item.vpd);
      }
      if(vpd==null && temp!=null && rh!=null){const es=.6108*Math.exp(17.27*temp/(temp+237.3));vpd=es*(1-rh/100);}
      setText('temp',temp==null?'—':fmt(temp)); setText('rh',rh==null?'—':fmt(rh,0)); setText('vpd',vpd==null?'—':fmt(vpd,2));
      setText('tempHint',temp==null?'keine Daten':'Live-Wert'); setText('rhHint',rh==null?'keine Daten':'Live-Wert'); setText('vpdHint',vpd==null?'keine Daten':'berechnet / Sensor');
    } catch (_) {} finally { document.dispatchEvent(new Event('gc:climate-loaded')); }
  }

  // Real Pi/BlueZ scan. Found advertisements are candidates only; never
  // grant trust or write access as a side effect of discovery.
  // Mars Hydro live controls are embedded in the ordinary Devices view.
  // Read-only by design: no GATT writes, no lamp dimming without validation.
  let marsFanId=null, marsLampId=null, marsLastScan=0, marsTimer=null, marsBusy=false, marsLampBusy=false;
  const marsHistory=[];
  function marsRecordSample(v){
    const row={time:new Date().toISOString(),temperature_c:Number(v.temperature_c),
      humidity_rh:Number(v.humidity_rh),rpm:Number(v.rpm),
      power_on:!!v.power_on,setpoint_percent:Number(v.setpoint_percent),
      airflow_cfm:Number(v.airflow_cfm),pressure_pa:Number(v.pressure_pa),
      airflow_pressure_source:v.airflow_pressure_source||""};
    if(![row.temperature_c,row.humidity_rh,row.rpm,row.setpoint_percent].every(Number.isFinite))return;
    marsHistory.push(row);if(marsHistory.length>120)marsHistory.shift();
    const curve=$('marsRpmLine'),title=$('marsTrendLabel');
    if(curve&&title){
      const samples=marsHistory.slice(-40);
      const maxRpm=Math.max(3000,...samples.map(r=>r.rpm));
      const points=samples.map((r,i)=>{
        const px=samples.length===1?320:(i/(samples.length-1))*624+8;
        const py=110-(r.rpm/maxRpm)*100;
        return px.toFixed(1)+','+py.toFixed(1);
      }).join(' ');
      curve.setAttribute('points',points);
      title.textContent='Drehzahlverlauf · '+samples.length+' echte BLE-Proben · zuletzt '+row.rpm+' RPM bei '+row.setpoint_percent+' %';
    }
    const el=$('marsHistory');if(el){
      el.replaceChildren();
      for(const sample of marsHistory.slice(-8).reverse()){
        const line=document.createElement('div');line.className='device-row';
        line.textContent=new Date(sample.time).toLocaleTimeString('de-DE')+' · '+sample.temperature_c.toLocaleString('de-DE')+
          ' °C · '+sample.humidity_rh.toLocaleString('de-DE')+' % rF · '+sample.rpm+' RPM · '+sample.setpoint_percent+' %';
        el.appendChild(line);
      }
    }
    const download=$('marsExportCsv');if(download)download.disabled=false;
  }
  $('marsExportCsv')?.addEventListener('click',()=>{
    if(!marsHistory.length)return;
    const columns=['time','temperature_c','humidity_rh','rpm','power_on','setpoint_percent','airflow_cfm','pressure_pa','airflow_pressure_source'];
    const csv=[columns.join(';'),...marsHistory.map(r=>columns.map(k=>r[k]).join(';'))].join('\\r\\n');
    const blob=new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const link=document.createElement('a');link.href=url;link.download='grow-central-mars-df150m-messverlauf.csv';
    document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
  });
  async function marsLiveRead(reconnect=false){
    const status=$('marsLiveStatus');
    if(!status || marsBusy || document.hidden || !document.getElementById('devices')?.classList.contains('active'))return;
    marsBusy=true;
    const btn=$('marsConnectLive');if(btn)btn.disabled=true;
    try{
      if(reconnect || !marsFanId || Date.now()-marsLastScan>120000){
        status.textContent='Mars Hydro Bluetooth-Geräte werden gesucht…';
        const found=await api('/api/mars-hydro/ble/scan',{method:'POST'});
        marsLastScan=Date.now();
        const fan=(found.devices||[]).find(d=>d.profile?.target_role==='fan' && d.name?.includes('MZF002'));
        const lamp=(found.devices||[]).find(d=>d.profile?.target_role==='light' && d.name?.endsWith('C260'));
        marsFanId=fan?.candidate_id||null;
        marsLampId=lamp?.candidate_id||null;
        setText('marsLampDetection',lamp?'FC3000 über Bluetooth erkannt · '+lamp.rssi+' dBm':'FC3000 gerade nicht sichtbar · Verbindung über Hersteller-App möglich');
        if(!marsFanId){status.textContent='DF150-M nicht sichtbar. Bitte Bluetooth-Verbindung der Hersteller-App trennen.';return;}
      }
      status.textContent='DF150-M sendet Live-Telemetrie…';
      const result=await api('/api/mars-hydro/ble/observe-fan-telemetry',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({candidate_id:marsFanId})
      });
      if(result.status!=='decoded'||!result.latest){
        status.textContent='Keine neue Meldung. Alte Messwerte werden nicht als Live angezeigt.';
        setText('marsFanUpdated','Verbindung ohne neue Telemetrie');
        return;
      }
      const v=result.latest;
      marsRecordSample(v);
      setText('marsFanTemp',Number(v.temperature_c).toLocaleString('de-DE',{maximumFractionDigits:1})+' °C');
      setText('marsFanHumidity',Number(v.humidity_rh).toLocaleString('de-DE',{maximumFractionDigits:1})+' %');
      setText('marsFanRpm',Number(v.rpm).toLocaleString('de-DE')+' RPM');
      setText('marsFanState',(v.power_on?'Ein':'Aus')+' · '+v.setpoint_percent+' %');
      setText('marsFanCfm',v.airflow_pressure_source==='estimated_from_setpoint_show_only'&&Number.isFinite(Number(v.airflow_cfm))?Number(v.airflow_cfm).toLocaleString('de-DE',{minimumFractionDigits:1,maximumFractionDigits:1})+' CFM':'—');
      setText('marsFanPa',v.airflow_pressure_source==='estimated_from_setpoint_show_only'&&Number.isFinite(Number(v.pressure_pa))?Number(v.pressure_pa).toLocaleString('de-DE',{minimumFractionDigits:1,maximumFractionDigits:1})+' Pa':'—');
      setText('marsFanUpdated','Letzte Messung: '+new Date().toLocaleTimeString('de-DE')+' · '+result.sample_count+' Meldungen');
      status.textContent='DF150-M verbunden · neue Messwerte alle 30 Sekunden';
    }catch(err){status.textContent='Mars Hydro: '+err.message+' · letzte Werte nicht aktuell';marsFanId=null;}
    finally{marsBusy=false;if(btn)btn.disabled=false;}
  }
  // Direct FC3000 status read from observed 19-field MARS notifications.
  // NEVER issue device writes. Stale readings are explicitly labelled.
  async function marsLampRead(forceScan=true){
    const button=$('marsLampRead');
    if(marsLampBusy||document.hidden||!document.getElementById('devices')?.classList.contains('active'))return;
    marsLampBusy=true;if(button)button.disabled=true;
    try {
      if(forceScan||!marsLampId||Date.now()-marsLastScan>120000){
        setText('marsLampUpdated','FC3000 Bluetooth wird gesucht…');
        const found=await api('/api/mars-hydro/ble/scan',{method:'POST'});
        marsLastScan=Date.now();
        const lamp=(found.devices||[]).find(d=>d.profile?.target_role==='light'&&d.name?.endsWith('C260'));
        marsLampId=lamp?.candidate_id||null;
        setText('marsLampDetection',lamp?'FC3000 erkannt · '+lamp.rssi+' dBm':'FC3000 nicht sichtbar · Mars Legacy kann die Verbindung belegen');
        if(!marsLampId){setText('marsLampUpdated','Kein Bluetooth-Kandidat. Lampe eingeschaltet lassen und Mars Legacy schließen.');return;}
      }
      setText('marsLampUpdated','Lese FC3000-Status (5 Sekunden)…');
      const result=await api('/api/mars-hydro/ble/observe-lamp-telemetry',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({candidate_id:marsLampId})
      });
      if(result.status!=='decoded'||!result.latest){
        setText('marsLampUpdated','Keine neue FC3000-Statusmeldung. Vorherige Anzeige ist nicht aktuell.');
        return;
      }
      const v=result.latest;
      setText('marsLampPower',v.power_on?'Ein':'Aus');
      setText('marsLampBrightness',v.brightness_percent+' %');
      setText('marsLampUpdated','Echte BLE-Daten · Firmware '+v.firmware_version+' · '+new Date().toLocaleTimeString('de-DE')+
        ' · '+result.sample_count+' Meldungen');
    }catch(err){
      setText('marsLampUpdated','Verbindungsfehler: '+err.message+' · angezeigte Werte nicht aktuell');
      marsLampId=null;
    }finally{marsLampBusy=false;if(button)button.disabled=false;}
  }
  $('marsLampRead')?.addEventListener('click',()=>marsLampRead(true));
  $('marsLampTrialLevel')?.addEventListener('input',()=>setText('marsLampTrialLevelText',$('marsLampTrialLevel').value+' %'));
  $('marsLampTrialAction')?.addEventListener('change',()=>{
    $('marsLampTrialLevel').disabled=$('marsLampTrialAction').value!=='brightness';
  });
  $('marsLampTrialRun')?.addEventListener('click',async()=>{
    const note=$('marsLampTrialMessage'),button=$('marsLampTrialRun');
    if(!note||!button)return;
    if(!marsLampId){note.textContent='Zuerst FC3000 über „Status lesen“ erkennen.';return;}
    const choice=$('marsLampTrialAction').value;
    const action=choice==='brightness'?'brightness':'power';
    const value=choice==='brightness'?Number($('marsLampTrialLevel').value):(choice==='power_on'?1:0);
    const description=choice==='brightness'?value+' % Helligkeit':choice==='power_on'?'Lampe einschalten':'Lampe ausschalten';
    if(!window.confirm('FC3000 wirklich auf '+description+' setzen? Ein echter Bluetooth-Befehl wird gesendet.'))return;
    button.disabled=true;note.textContent='Prüfe aktuelle FC3000-Sitzung und sende höchstens einen Befehl…';
    try{
      const result=await api('/api/mars-hydro/ble/control-lamp-trial',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({candidate_id:marsLampId,action,value,confirm_physical_change:true})
      });
      note.textContent=result.message+
        (result.device_report_confirmed?' · Status vom Controller bestätigt.':' · Physische Wirkung bitte direkt prüfen.');
      if(result.latest){
        setText('marsLampPower',result.latest.power_on?'Ein':'Aus');
        setText('marsLampBrightness',result.latest.brightness_percent+' %');
        setText('marsLampUpdated','FC3000 Statusmeldung nach Test · '+new Date().toLocaleTimeString('de-DE'));
      }
    }catch(err){note.textContent='Kein erfolgreicher Steuerungstest: '+err.message;}
    finally{button.disabled=false;}
  });
  $('marsConnectLive')?.addEventListener('click',()=>{
    marsLiveRead(true);
    if(marsTimer===null)marsTimer=setInterval(()=>marsLiveRead(false),30000);
  });
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden && marsTimer!==null){clearInterval(marsTimer);marsTimer=null;}
  });

  // Optional separate vendor-cloud control for DF150-M. Never log in or
  // transmit actions until the owner explicitly clicks a control.
  let cloudFanConfigured=false, cloudFanBusy=false;
  async function cloudFanStatus(){
    const state=$('marsCloudFanStatus');
    if(!state)return;
    try{
      const status=await api('/api/mars-hydro/cloud-fan/status');
      cloudFanConfigured=!!status.configured;
      state.textContent=cloudFanConfigured
        ?'Cloud-Zugang eingerichtet · Mars Hydro iPhone-App kann bei Anmeldung abgemeldet werden'
        :'Cloud-Steuerung nicht eingerichtet. Lokal-Bluetooth-Livewerte funktionieren weiterhin.';
    }catch(err){
      cloudFanConfigured=false;
      state.textContent='Cloud-Adapter: '+err.message;
    }
    for(const id of ['marsCloudFanRead','marsCloudFanSet','marsCloudFanOn','marsCloudFanOff','marsCloudFanSpeed']){
      const item=$(id);if(item)item.disabled=!cloudFanConfigured;
    }
  }
  async function cloudFanRequest(path,data){
    return api('/api/mars-hydro/cloud-fan/'+path,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(data||{}),
    });
  }
  $('marsCloudFanSpeed')?.addEventListener('input',()=>{
    setText('marsCloudFanSpeedValue',$('marsCloudFanSpeed').value+' %');
  });
  $('marsCloudFanPanel')?.addEventListener('toggle',()=>{
    if($('marsCloudFanPanel').open)cloudFanStatus();
  });
  $('marsCloudFanRead')?.addEventListener('click',async()=>{
    if(cloudFanBusy || !cloudFanConfigured)return;
    if(!window.confirm('Mars Hydro Cloud anmelden? Dabei kann die Hersteller-App am iPhone abgemeldet werden.'))return;
    cloudFanBusy=true;
    try{
      const r=await cloudFanRequest('fan/read',{});
      setText('marsCloudFanResult','Cloud: '+r.fan.name+' · Sollwert '+(r.fan.speed_percent??'unbekannt')+' % · Quelle Hersteller-Cloud');
    }catch(err){setText('marsCloudFanResult','Cloud-Abfrage: '+err.message);}
    finally{cloudFanBusy=false;}
  });
  async function cloudFanControl(action,value){
    if(cloudFanBusy||!cloudFanConfigured)return;
    const label=action==='speed'?value+' % Drehzahl':value===1?'Lüfter EIN':'Lüfter AUS';
    if(!window.confirm('DF150-M über Mars Hydro Cloud auf '+label+' setzen? Es wird genau ein echter Steuerbefehl gesendet.'))return;
    cloudFanBusy=true;
    setText('marsCloudFanResult','Sende genau einen Lüfterbefehl und lese Status zurück…');
    try{
      const r=await cloudFanRequest('fan/control',{action,value,confirm:true});
      setText('marsCloudFanResult',r.readback_matches
        ?'Hersteller-Cloud bestätigt '+label+' · physische Wirkung nicht unabhängig geprüft'
        :'Befehl vom Anbieter angenommen; Rückmeldung stimmt noch nicht überein. Keine automatische Wiederholung.');
    }catch(err){setText('marsCloudFanResult','Steuerung: '+err.message);}
    finally{cloudFanBusy=false;}
  }
  $('marsCloudFanSet')?.addEventListener('click',()=>cloudFanControl('speed',Number($('marsCloudFanSpeed').value)));
  $('marsCloudFanOn')?.addEventListener('click',()=>cloudFanControl('power',1));
  $('marsCloudFanOff')?.addEventListener('click',()=>cloudFanControl('power',0));

  async function marsWifiApRead(){
    const button=$('marsWifiApRefresh'),status=$('marsWifiApStatus'),list=$('marsWifiApList');
    if(!button||!status||!list)return;
    button.disabled=true;status.textContent='Lese vorhandene WLAN-Funkdaten des Pi…';
    try{
      const result=await api('/api/mars-hydro/ble/wifi-access-points');
      list.replaceChildren();
      if(!result.ok){
        status.textContent='WLAN-Diagnose nicht verfügbar: '+(result.reason||'unbekannt');return;
      }
      const items=result.access_points||[];
      status.textContent=items.length+' Mars-Hydro-WLAN-Sender erkannt · keine Netzwerkänderung';
      if(!items.length){
        const empty=document.createElement('div');empty.className='empty';
        empty.textContent='Kein MZ-AP-MASTER in der WLAN-Liste des Pi. Kein Beweis für ausgeschaltete Geräte.';
        list.appendChild(empty);
      }
      for(const point of items){
        const row=document.createElement('div');row.className='device-row';
        const name=document.createElement('strong');name.textContent=point.device_hint;
        const detail=document.createElement('small');
        detail.textContent=point.ssid+' · '+point.bssid+' · Kanal '+point.channel+
          ' · Signal '+point.signal_percent+' % · '+point.security+' · nicht verbunden';
        row.appendChild(name);row.appendChild(detail);list.appendChild(row);
      }
    }catch(err){status.textContent='WLAN-Diagnose: '+err.message;}
    finally{button.disabled=false;}
  }
  $('marsWifiApRefresh')?.addEventListener('click',marsWifiApRead);

  async function scanLocalBluetooth() {
    const btn=$('bleDiscoverBtn'), status=$('bleDiscoveryStatus'), list=$('bleDiscoveryResults');
    if(!btn||!status||!list)return;
    btn.disabled=true;btn.textContent='BLE-Suche läuft…';
    status.textContent='Bluetooth-Adapter prüfen und BLE-Werbesignale erfassen…';
    try {
      const result=await api('/api/mars-hydro/ble/scan',{method:'POST'});
      const devices=result.devices||[], adapter=result.adapter||{};
      const adapterText=adapter.state==='ready'?'Bluetooth bereit':(adapter.hint||'Adapter nicht bereit');
      status.textContent=adapterText+' · '+(result.message||devices.length+' Geräte erkannt')+' · '+(result.scan_seconds||0)+' Sekunden';
      list.replaceChildren();
      if(!devices.length){const empty=document.createElement('div');empty.className='empty';empty.textContent=result.message||'Keine BLE-Geräte gefunden.';list.append(empty);}
      for(const device of devices){
        const row=document.createElement('div');row.className='device-row';
        const details=document.createElement('div');
        const name=document.createElement('strong');name.textContent=device.name||'Unbekanntes BLE-Gerät';
        const profile=device.profile||{};
        const role=document.createElement('small');
        role.textContent=(profile.label||'BLE-Gerät')+' · Erkennung '+(device.mars_hydro_hint?'plausibel':'ungeklärt');
        const note=document.createElement('small');
        note.textContent=(device.rssi==null?'RSSI unbekannt':device.rssi+' dBm')+' · Herstellerkennungen: '+(device.manufacturer_ids||[]).join(', ')+' · Identität/Steuerung unbestätigt';
        details.append(name,role,note);
        const inspectBtn=document.createElement('button');inspectBtn.className='secondary';inspectBtn.type='button';inspectBtn.textContent='GATT auslesen';
        inspectBtn.addEventListener('click',()=>inspectLocalBluetooth(device.candidate_id,name.textContent,inspectBtn));
        row.append(details,inspectBtn);list.append(row);
      }
    }catch(error){status.textContent='Bluetooth-Suche fehlgeschlagen: '+error.message;list.textContent='Die erweiterten Bluetooth-Diagnosen enthalten den Adapterstatus.';}
    finally{btn.disabled=false;btn.textContent='Bluetooth suchen';}
  }

  async function inspectLocalBluetooth(candidateId,deviceName,button) {
    const output=$('bleGattDetails');if(!output)return;
    button.disabled=true;output.hidden=false;output.textContent=deviceName+': GATT-Dienste werden schreibgeschützt ausgelesen…';
    try {
      const data=await api('/api/mars-hydro/ble/inspect',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({candidate_id:candidateId})
      });
      const cap=data.capabilities||{};
      const summary=[
        'Gerät: '+(data.name||deviceName),
        'GATT-Verbindung: '+(data.connected?'erfolgreich':'nicht verbunden'),
        'MZF002-Transport: '+(cap.mzf002_transport_confirmed?'UUIDs bestätigt':'nicht bestätigt'),
        'Lesbare Characteristics: '+(cap.readable_count??'?'),
        'Notify-Characteristics: '+(cap.notifiable_count??'?'),
        'Lichtsteuerung / Lüftersteuerung: NICHT freigegeben',
        'Temperatur, Feuchte, Drehzahl: bislang KEINE bestätigten Messwerte',
        '',
        'Technische Rohdaten (keine dekodierten Sensorwerte):',
        JSON.stringify(data,null,2)
      ];
      output.textContent=summary.join('\n');
    }catch(error){output.textContent='GATT-Auslesen fehlgeschlagen: '+error.message+'\nHersteller-App trennen und Gerät erneut suchen.';}
    finally{button.disabled=false;}
  }

  async function universalDiscover() {
    const button=$('discoverBtn'); button.disabled=true; button.textContent='Suche läuft…';
    try { const result=await api('/api/devices/discover?timeout=5'); state.discovered=result.devices||[]; document.dispatchEvent(new Event("gc:sensors-discovered")); renderDeviceTable(); const errors=result.errors||[]; toast(`${state.discovered.length} Gerät(e) erkannt${errors.length?` · ${errors.length} Provider mit Hinweis`:''}`,errors.length?'':'success'); }
    catch(error){toast(`Discovery fehlgeschlagen: ${error.message}`,'error');}
    finally{button.disabled=false;button.textContent='Geräte suchen';}
  }

  async function loadAutomations(){try{const d=await api('/api/v1/automations');const rows=d.automations||[];$('automationList').innerHTML=rows.length?rows.map((r)=>`<article class="rule-card"><div><strong>${esc(r.name||'Automation')}</strong><small>${esc([r.trigger,r.device_id].filter(Boolean).join(' · '))}</small></div><span class="state-badge ${r.enabled===false?'offline':''}">${r.enabled===false?'PAUSIERT':'HINTERLEGT'}</span></article>`).join(''):'<div class="empty">Noch keine lokalen Regeln angelegt.</div>';}catch(e){$('automationList').innerHTML=`<div class="empty">Automationen: ${esc(e.message)}</div>`;}}
  async function loadCamera(){try{const d=await api('/api/v1/camera/status?refresh=true');const rows=d.devices||[];$('cameraGrid').innerHTML=rows.length?rows.map((r)=>`<article class="camera-card"><div class="camera-placeholder">◉</div><footer><strong>${esc(r.c920_match?'Logitech C920':r.name||r.device||'Kamera')}</strong><small>${esc(r.capture_capable?'Capture bereit':'Gerät erkannt · prüfen')}</small></footer></article>`).join(''):'<div class="empty">Keine lokale Kamera erkannt.</div>';}catch(e){$('cameraGrid').innerHTML=`<div class="empty">Kamera: ${esc(e.message)}</div>`;}}
  async function loadEnergy(refresh=false){const d=await loadSmart(refresh);if(!d)return;const s=d.summary||{};setText('energyPower',(s.power_w!=null&&s.power_w!==''&&Number.isFinite(Number(s.power_w)))?fmt(s.power_w):'—');setText('energyTotal',(s.energy_wh!=null&&s.energy_wh!==''&&Number.isFinite(Number(s.energy_wh)))?fmt(Number(s.energy_wh)/1000,3):'—');setText('energyOnline',`${s.online||0} / ${s.configured||0}`);setText('energyOn',s.switched_on??'—');$('energyDevices').innerHTML=(d.devices||[]).length?(d.devices||[]).map(miniDevice).join(''):'<div class="empty">Keine Energiedaten verfügbar.</div>';}
  async function loadSystem(){try{const d=await api('/api/v1/system/info');const values=[['Hostname',d.hostname],['IPv4',d.primary_ipv4],['Version',d.version],['Build',d.build],['Hardware',d.model],['OS',d.operating_system],['Uptime',d.uptime?.display]];$('systemGrid').innerHTML=values.map(([k,v])=>`<div class="system-item"><span>${esc(k)}</span><b>${esc(v||'—')}</b></div>`).join('');}catch(e){$('systemGrid').innerHTML=`<div class="empty">System: ${esc(e.message)}</div>`;}}

  async function refreshAll(showToast=false){
    setText('lastUpdate','wird aktualisiert…');
    const healthPromise=api('/api/health');
    const [healthResult,platformResult]=await Promise.allSettled([healthPromise,loadPlatform(),loadSmart(true),loadClimate()]);
    const healthOk=healthResult.status==='fulfilled' && healthResult.value?.ok===true;
    const runtimeErrors=platformResult.status==='fulfilled'?Number(platformResult.value||0):1;
    $('coreDot').className=healthOk?'online':'error'; setText('coreLabel',healthOk?'LOCAL ONLINE':'CORE OFFLINE'); updateHeadline(healthOk,runtimeErrors);
    setText('lastUpdate',new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}));
    window.dispatchEvent(new Event('gc:core-refreshed'));
    if(showToast)toast(healthOk?'Daten aktualisiert':'Core nicht erreichbar',healthOk?'success':'error');
  }

  document.querySelectorAll('#mainNav [data-view],[data-open]').forEach((node)=>node.addEventListener('click',()=>openView(node.dataset.view||node.dataset.open)));
  document.querySelectorAll('.filterbar [data-filter]').forEach((node)=>node.addEventListener('click',()=>{document.querySelectorAll('.filterbar [data-filter]').forEach((x)=>x.classList.remove('active'));node.classList.add('active');state.filter=node.dataset.filter;renderDeviceTable();}));
  $('simpleMode').addEventListener('click',()=>setMode('simple')); $('advancedMode').addEventListener('click',()=>setMode('advanced'));
  $('refreshBtn').addEventListener('click',()=>refreshAll(true)); $('systemRefresh')?.addEventListener('click',loadSystem); $('cameraRefreshMaster')?.addEventListener('click',loadCamera); $('discoverBtn').addEventListener('click',universalDiscover); $('bleDiscoverBtn')?.addEventListener('click',scanLocalBluetooth);
  setMode(state.mode); refreshAll(false); setInterval(()=>refreshAll(false),60000);
})();
