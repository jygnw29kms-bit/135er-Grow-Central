(()=>{
'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=1)=>v!=null&&v!==''&&Number.isFinite(Number(v))?Number(v).toFixed(d):'?';
const api=async(path,options={})=>{const r=await fetch(path,{cache:'no-store',credentials:'same-origin',...options});const type=r.headers.get('content-type')||'';const body=type.includes('json')?await r.json():await r.text();if(!r.ok)throw new Error(body?.detail||body||`HTTP ${r.status}`);return body};
const toast=(msg,type='')=>{const t=$('toast');if(!t)return;t.textContent=msg;t.className=`toast show ${type}`;clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove('show'),3500)};
const kindLabel={grow_tent:'Growzelt',grow_room:'Growraum',drying:'Trocknung',storage:'Lager',other:'Sonstiges'};
const categoryLabel={note:'Notiz',watering:'Bew?sserung',feeding:'D?ngung',training:'Training',defoliation:'Entlaubung',pest:'Sch?dlinge',flowering:'Bl?te',harvest:'Ernte',other:'Sonstiges'};

function mount(id,html){
  const section=$(id); if(!section)return null;
  let root=section.querySelector(':scope > .gc-live-body');
  if(!root){
    [...section.children].forEach(node=>{if(!node.classList?.contains('master-section-head'))node.hidden=true});
    root=document.createElement('div');root.className='gc-live-body';section.append(root);
  }
  root.innerHTML=html;return root;
}
function stateBadge(ok,yes='ONLINE',no='OFFLINE'){return `<span class="state-badge ${ok?'':'offline'}">${ok?yes:no}</span>`}
function valueCard(title,value,unit='',hint=''){return `<article class="master-panel gc-kpi"><small>${esc(title)}</small><strong>${esc(value)}${unit?` <em>${esc(unit)}</em>`:''}</strong>${hint?`<span>${esc(hint)}</span>`:''}</article>`}
function lineSvg(values,{min=null,max=null}={}){
  const nums=values.map(Number).filter(Number.isFinite);if(nums.length<2)return '<div class="gc-empty">Noch nicht genug Historie.</div>';
  const lo=min??Math.min(...nums), hi=max??Math.max(...nums); const span=Math.max(.001,hi-lo);
  const pts=nums.map((v,i)=>`${(i/(nums.length-1)*100).toFixed(2)},${(100-(v-lo)/span*100).toFixed(2)}`).join(' ');
  return `<svg class="gc-line-chart" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}" fill="none" vector-effect="non-scaling-stroke"/></svg>`;
}
async function roomsWithHistory(limit=288){
  const data=await api('/api/v1/rooms'); const rooms=data.rooms||[];
  const histories=await Promise.all(rooms.map(async r=>{try{return (await api(`/api/v1/rooms/${encodeURIComponent(r.id)}/sensors?limit=${limit}`)).samples||[]}catch{return []}}));
  return rooms.map((r,i)=>({...r,history:histories[i]}));
}

async function renderClimate(){
  const root=mount('climate','<div class="gc-loading">Klimadaten werden geladen?</div>');
  try{
    const rooms=await roomsWithHistory(288); const live=rooms.map(r=>r.latest_sensor).filter(Boolean);
    const avg=(key,d=1)=>{const n=live.map(x=>Number(x[key])).filter(Number.isFinite);return n.length?(n.reduce((a,b)=>a+b,0)/n.length).toFixed(d):'?'};
    root.innerHTML=`<div class="gc-kpis">${valueCard('Temperatur',avg('temperature_c'),'?C',`${live.length} aktive Quelle(n)`)}${valueCard('Luftfeuchte',avg('humidity_percent',0),'%', 'Raummittel')}${valueCard('VPD',avg('vpd_kpa',2),'kPa','Raummittel')}</div><div class="gc-stack" id="climateRooms"></div>`;
    $('climateRooms').innerHTML=rooms.length?rooms.map(r=>{const s=r.latest_sensor||{}, hist=r.history||[];return `<article class="master-panel gc-room-live"><div class="master-panel-head"><h3>${esc(r.name)}</h3>${stateBadge(!!r.latest_sensor,'DATEN','KEINE DATEN')}</div><div class="gc-room-values"><b>${fmt(s.temperature_c)} ?C</b><b>${fmt(s.humidity_percent,0)} % rF</b><b>${fmt(s.vpd_kpa,2)} kPa</b></div><div class="gc-chart-pair"><div><small>Temperatur</small>${lineSvg(hist.map(x=>x.temperature_c))}</div><div><small>Luftfeuchte</small>${lineSvg(hist.map(x=>x.humidity_percent),{min:0,max:100})}</div></div><small>${hist.length} Messpunkte geladen</small></article>`}).join(''):'<div class="gc-empty">Noch keine R?ume angelegt.</div>';
  }catch(e){root.innerHTML=`<div class="gc-error">Klima konnte nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderIrrigation(){
  const root=mount('irrigation','<div class="gc-loading">Bew?sserungsdaten werden geladen?</div>');
  try{
    const [roomData,calData,devices]=await Promise.all([api('/api/v1/rooms'),api('/api/v1/sensor-calibration'),api('/api/devices/discover?timeout=1')]);
    const rooms=roomData.rooms||[], cal=calData.devices||[];
    const pumps=(devices.devices||[]).filter(d=>['pump','valve'].includes(d.device_class)||((d.capabilities||[]).some(x=>['switch','flow'].includes(x))&&/pump|pumpe|ventil|valve/i.test(`${d.name} ${d.model||''}`)));
    root.innerHTML=`<div class="master-two-col"><article class="master-panel"><div class="master-panel-head"><h3>Bodenfeuchte</h3><span>${cal.length} Sensor(en)</span></div><div class="gc-list">${cal.length?cal.map(c=>{const room=rooms.find(r=>r.id===c.room_id),latest=room?.latest_sensor||{},moist=latest.soil_moisture_percent;return `<div class="gc-list-row"><div><strong>${esc(c.name||c.device_id)}</strong><small>${esc(room?.name||'Noch keinem Raum zugewiesen')}</small></div><div><b>${moist!=null?`${fmt(moist,1)} %`:'?'}</b><small>${c.calibration_status==='valid'?'3-Punkt-Kalibrierung g?ltig':'Kalibrierung erforderlich'}</small></div>${stateBadge(c.status==='TRUSTED'&&c.calibration_status==='valid','BEREIT','PR?FEN')}</div>`}).join(''):'<div class="gc-empty">Noch kein Bodenfeuchtesensor aufgenommen.</div>'}</div></article><article class="master-panel"><div class="master-panel-head"><h3>Pumpen & Ventile</h3><span>${pumps.length} erkannt</span></div><div class="gc-list">${pumps.length?pumps.map(d=>`<div class="gc-list-row"><div><strong>${esc(d.name)}</strong><small>${esc(d.provider_id)} ? ${esc((d.capabilities||[]).join(', '))}</small></div>${stateBadge(true,'ERKANNT','')}</div>`).join(''):'<div class="gc-empty">Keine validierte Pumpe oder Ventil erkannt. Schreibzugriff bleibt sicher gesperrt.</div>'}</div></article></div>`;
  }catch(e){root.innerHTML=`<div class="gc-error">Bew?sserung konnte nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderLighting(){
  const root=mount('lighting','<div class="gc-loading">Lichtger?te werden geladen?</div>');
  try{
    const data=await api('/api/devices/discover?timeout=2');
    const lights=(data.devices||[]).filter(d=>d.device_class==='light'||(d.capabilities||[]).some(c=>['brightness','illuminance','color_temperature'].includes(c))||/light|lampe|mars hydro|spider/i.test(`${d.name} ${d.model||''}`));
    root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Leuchten & Lichtquellen</h3><span>${lights.length} erkannt</span></div><div class="gc-list">${lights.length?lights.map(d=>`<div class="gc-list-row"><div><strong>${esc(d.name)}</strong><small>${esc(d.provider_id)} ? ${esc(d.model||d.device_class)} ? ${esc((d.capabilities||[]).join(', '))}</small></div>${stateBadge(true,'ERKANNT','')}</div>`).join(''):'<div class="gc-empty">Keine kompatible Leuchte erkannt.</div>'}</div></article><article class="master-panel"><div class="master-panel-head"><h3>PPFD / Lichtst?rke</h3><span class="optional-badge">MESSQUELLE ERFORDERLICH</span></div><p class="master-copy">PPFD/Lux wird nur angezeigt, wenn ein Sensor eine echte Messgr??e liefert. Aus Lampenleistung wird kein erfundener ?mol-Wert berechnet.</p></article>`;
  }catch(e){root.innerHTML=`<div class="gc-error">Beleuchtung konnte nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderGrowlog(){
  const root=mount('growlog','<div class="gc-loading">Growtagebuch wird geladen?</div>');
  try{
    const roomData=await api('/api/v1/rooms'),rooms=roomData.rooms||[];
    const entries=(await Promise.all(rooms.map(async r=>{try{return ((await api(`/api/v1/rooms/${encodeURIComponent(r.id)}/journal`)).entries||[]).map(e=>({...e,room_name:r.name}))}catch{return []}}))).flat().sort((a,b)=>Date.parse(b.created_at||0)-Date.parse(a.created_at||0));
    root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Eintrag hinzuf?gen</h3></div><form id="growlogForm" class="gc-form"><label>Raum<select id="growlogRoom" required>${rooms.map(r=>`<option value="${esc(r.id)}">${esc(r.name)}</option>`).join('')}</select></label><label>Kategorie<select id="growlogCategory">${Object.entries(categoryLabel).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label><label class="gc-span-2">Titel<input id="growlogTitle" maxlength="120" required placeholder="z. B. Gegossen"></label><label class="gc-span-2">Notiz<textarea id="growlogText" maxlength="5000" rows="3" placeholder="Optionale Details"></textarea></label><button class="master-primary" ${rooms.length?'':'disabled'}>Eintrag speichern</button></form></article><article class="master-panel"><div class="master-panel-head"><h3>Chronik</h3><span>${entries.length} Eintr?ge</span></div><div class="gc-timeline">${entries.length?entries.slice(0,100).map(e=>`<div><time>${esc(new Date(e.created_at).toLocaleString('de-DE'))}</time><span><b>${esc(e.title)}</b><small>${esc(e.room_name)} ? ${esc(categoryLabel[e.category]||e.category)}</small>${e.text?`<p>${esc(e.text)}</p>`:''}</span></div>`).join(''):'<div class="gc-empty">Noch keine Tagebucheintr?ge.</div>'}</div></article>`;
    $('growlogForm')?.addEventListener('submit',async ev=>{ev.preventDefault();try{const room=$('growlogRoom').value;await api(`/api/v1/rooms/${encodeURIComponent(room)}/journal`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({category:$('growlogCategory').value,title:$('growlogTitle').value.trim(),text:$('growlogText').value.trim()})});toast('Tagebucheintrag gespeichert');renderGrowlog()}catch(e){toast(e.message,'error')}});
  }catch(e){root.innerHTML=`<div class="gc-error">Growtagebuch konnte nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderRecordings(){
  const root=mount('recordings','<div class="gc-loading">Kamera wird gepr?ft?</div>');
  try{
    const status=await api('/api/v1/camera/status?refresh=true');const cams=status.devices||[];
    root.innerHTML=`<div class="master-two-col"><article class="master-panel"><div class="master-panel-head"><h3>Snapshot</h3>${stateBadge(cams.some(c=>c.capture_capable),'BEREIT','NICHT BEREIT')}</div><div class="gc-snapshot"><img id="recordingSnapshot" alt="Kamera Snapshot"><div id="recordingSnapshotFallback">Noch kein Snapshot geladen.</div></div><div class="gc-actions"><button class="master-primary" id="takeSnapshot" ${cams.some(c=>c.capture_capable)?'':'disabled'}>Snapshot aktualisieren</button><a class="secondary" id="openSnapshot" href="/api/v1/camera/snapshot" target="_blank" rel="noopener">Bild ?ffnen</a></div></article><article class="master-panel"><div class="master-panel-head"><h3>Lokale Kameras</h3><span>${cams.length}</span></div><div class="gc-list">${cams.length?cams.map(c=>`<div class="gc-list-row"><div><strong>${esc(c.name||c.device||'Kamera')}</strong><small>${esc(c.device||'')} ${c.c920_match?'? Logitech C920':''}</small></div>${stateBadge(!!c.capture_capable,'CAPTURE','PR?FEN')}</div>`).join(''):'<div class="gc-empty">Keine Kamera erkannt.</div>'}</div><p class="master-copy">Videoaufzeichnung und Zeitraffer bleiben deaktiviert, bis Speichergrenzen und Aufbewahrungsregeln serverseitig umgesetzt sind.</p></article></div>`;
    const snap=()=>{const img=$('recordingSnapshot'),fb=$('recordingSnapshotFallback');img.onload=()=>{img.hidden=false;fb.hidden=true};img.onerror=()=>{img.hidden=true;fb.hidden=false;fb.textContent='Snapshot nicht verf?gbar.'};img.src=`/api/v1/camera/snapshot?_=${Date.now()}`};$('takeSnapshot')?.addEventListener('click',snap);if(cams.some(c=>c.capture_capable))snap();
  }catch(e){root.innerHTML=`<div class="gc-error">Aufnahmen konnten nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderSettings(){
  const root=mount('settings','<div class="gc-loading">Systemzustand wird geladen?</div>');
  try{
    const [sys,net,runtime]=await Promise.all([api('/api/v1/system/info'),api('/api/v1/network/status').catch(()=>null),api('/api/devices/runtime')]);
    const rows=[['Hostname',sys.hostname],['IPv4',sys.primary_ipv4],['Version',sys.version],['Build',sys.build],['Hardware',sys.model],['OS',sys.operating_system],['Kernel',sys.kernel],['Uptime',sys.uptime?.display]];
    root.innerHTML=`<div class="gc-kpis">${valueCard('CPU',sys.resources?.cpu_percent!=null?fmt(sys.resources.cpu_percent,0):'?','%')}${valueCard('CPU-Temperatur',sys.resources?.cpu_temperature_c!=null?fmt(sys.resources.cpu_temperature_c,1):'?','?C')}${valueCard('RAM',sys.resources?.memory_percent!=null?fmt(sys.resources.memory_percent,0):'?','%')}${valueCard('Datentr?ger',sys.resources?.disk_percent!=null?fmt(sys.resources.disk_percent,0):'?','%')}</div><div class="master-two-col"><article class="master-panel"><div class="master-panel-head"><h3>System</h3></div><div class="gc-kv">${rows.map(([k,v])=>`<span>${esc(k)}</span><b>${esc(v??'?')}</b>`).join('')}</div></article><article class="master-panel"><div class="master-panel-head"><h3>Netzwerk</h3></div><pre class="gc-pre">${esc(net?JSON.stringify(net,null,2):'Netzwerkstatus nicht verf?gbar')}</pre></article></div><article class="master-panel"><div class="master-panel-head"><h3>Provider Runtime</h3><span>${runtime.providers?.length||0}</span></div><div class="gc-list">${(runtime.providers||[]).map(p=>`<div class="gc-list-row"><div><strong>${esc(p.name)}</strong><small>${esc(p.id)} ? ${p.device_count} Ger?t(e)</small></div>${stateBadge(!p.error,p.error?'FEHLER':'READY',p.error?'FEHLER':'READY')}</div>`).join('')}</div></article>`;
  }catch(e){root.innerHTML=`<div class="gc-error">Einstellungen konnten nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderUsers(){
  const root=mount('users','<div class="gc-loading">Benutzerstatus wird geladen?</div>');
  try{const a=await api('/api/auth/status');root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Lokaler GUI-Zugang</h3>${stateBadge(a.authenticated,'ANGEMELDET','ABGEMELDET')}</div><div class="gc-kv"><span>Benutzer</span><b>${esc(a.username||'?')}</b><span>GUI eingerichtet</span><b>${a.configured?'Ja':'Nein'}</b><span>Sitzung</span><b>${a.authenticated?'aktiv':'nicht aktiv'}</b><span>Sitzungsdauer</span><b>12 Stunden, gleitend</b><span>Speicherung</span><b>gehasht / lokal</b></div><p class="master-copy">Grow-Central verwendet aktuell einen lokalen Appliance-Administrator. Mehrbenutzer-Rollen werden erst freigeschaltet, wenn Rechte f?r Ger?teaktionen, R?ume und Systemfunktionen vollst?ndig getrennt sind.</p></article>`}catch(e){root.innerHTML=`<div class="gc-error">Benutzerstatus: ${esc(e.message)}</div>`}
}

async function renderBackups(){
  const root=mount('backups','<div class="gc-loading">Sicherungsfunktionen werden geladen?</div>');
  root.innerHTML=`<div class="master-two-col"><article class="master-panel"><div class="master-panel-head"><h3>Konfigurations-Export</h3><span class="state-badge">LOKAL</span></div><p class="master-copy">Erstellt eine lokale JSON-Sicherung der nicht geheimen Grow-Central-Konfiguration: R?ume, Automationen, UI-Layout, Systemversion und Providerstatus. Passw?rter, Tokens, private Schl?ssel und Broker-Credentials werden nicht exportiert.</p><button class="master-primary" id="backupExport">Export erstellen</button></article><article class="master-panel"><div class="master-panel-head"><h3>Diagnosepaket</h3></div><p class="master-copy">Das vorhandene Diagnose-Bundle bleibt getrennt von Backups und dient ausschlie?lich der Fehlersuche.</p><button class="secondary" id="diagnosticsBundle">Diagnosepaket erstellen</button><div id="backupStatus" class="gc-status"></div></article></div>`;
  $('backupExport')?.addEventListener('click',async()=>{try{const [rooms,automations,layout,sys,providers]=await Promise.all([api('/api/v1/rooms'),api('/api/v1/automations'),api('/api/v1/ui-layout'),api('/api/v1/system/info'),api('/api/devices/providers')]);const bundle={schema:'grow-central-safe-export-v1',created_at:new Date().toISOString(),system:{hostname:sys.hostname,version:sys.version,build:sys.build,model:sys.model},rooms,automations,ui_layout:layout,providers};const blob=new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`grow-central-backup-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Sicherer Konfigurations-Export erstellt')}catch(e){toast(e.message,'error')}});
  $('diagnosticsBundle')?.addEventListener('click',async()=>{try{const box=$('backupStatus');box.textContent='Diagnosepaket wird angefordert?';await api('/api/v1/diagnostics/bundle',{method:'POST'});for(let i=0;i<30;i++){const state=await api('/api/v1/diagnostics/bundle/status');if(state.available&&!state.pending){box.innerHTML=`<a href="/api/v1/diagnostics/bundle/download" target="_blank" rel="noopener">Diagnosepaket herunterladen (${Math.ceil((state.size||0)/1024)} KiB)</a>`;return}box.textContent=state.pending?'Diagnosepaket wird erstellt?':'Warte auf Diagnosepaket?';await new Promise(r=>setTimeout(r,1000))}box.textContent='Erstellung l?uft l?nger als erwartet. Status sp?ter erneut ?ffnen.'}catch(e){$('backupStatus').textContent=e.message}});
}

async function renderUpdates(){
  const root=mount('updates','<div class="gc-loading">Versionsstand wird geladen?</div>');
  try{const sys=await api('/api/v1/system/info');root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Installierter Stand</h3><span class="state-badge">AKTIV</span></div><div class="gc-kv"><span>Version</span><b>${esc(sys.version||'?')}</b><span>Build</span><b>${esc(sys.build||'?')}</b><span>Release-Kanal</span><b>${esc(sys.release_channel||'local')}</b><span>Hardwareprofil</span><b>${esc(sys.hardware?.profile||sys.hardware?.family||'?')}</b><span>Live Git</span><b>${esc(sys.live_git_sha||'nicht markiert')}</b></div><p class="master-copy">Automatische Updates bleiben bewusst deaktiviert, bis Signaturpr?fung, atomarer Rollback und Image-Kompatibilit?tspr?fung vollst?ndig umgesetzt sind. Der aktuell installierte Stand kann hier aber eindeutig gepr?ft werden.</p></article>`}catch(e){root.innerHTML=`<div class="gc-error">Update-Status: ${esc(e.message)}</div>`}
}

async function renderExtensions(){
  const root=mount('extensions','<div class="gc-loading">Provider werden geladen?</div>');
  try{const [providers,runtime]=await Promise.all([api('/api/devices/providers'),api('/api/devices/runtime')]);const health=new Map((runtime.providers||[]).map(x=>[x.id,x]));root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Provider & Integrationen</h3><span>${providers.providers?.length||0}</span></div><div class="provider-grid">${(providers.providers||[]).map(p=>{const r=health.get(p.id);return `<article class="provider-card"><header><strong>${esc(p.name)}</strong>${stateBadge(!!p.runtime_available,'RUNTIME','KATALOG')}</header><small>${esc(p.id)} ? ${esc(p.support||'')}</small><p>${r?.error?esc(r.error):`${r?.device_count||0} Ger?t(e) erkannt`}</p></article>`}).join('')}</div></article>`}catch(e){root.innerHTML=`<div class="gc-error">Erweiterungen: ${esc(e.message)}</div>`}
}


async function renderAutomation(){
  const root=mount('automation','<div class="gc-loading">Zeitpl?ne werden geladen?</div>');
  try{
    const [data,smart]=await Promise.all([api('/api/v1/automations'),api('/api/v1/smarthome/overview').catch(()=>({devices:[]}))]);
    const rows=data.automations||[], devices=smart.devices||[];
    root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Neue lokale Regel</h3><span class="state-badge">DEFINITION</span></div><form id="automationForm" class="gc-form"><label>Name<input id="autoName" maxlength="60" required placeholder="z. B. Licht morgens"></label><label>Trigger<select id="autoTrigger"><option value="time">Uhrzeit</option><option value="manual">Manuell</option><option value="temperature_above">Temperatur ?ber</option><option value="temperature_below">Temperatur unter</option></select></label><label>Trigger-Wert<input id="autoTriggerValue" maxlength="32" placeholder="06:00 oder 28"></label><label>Ger?t<select id="autoDevice">${devices.map(d=>`<option value="${esc(d.id||d.device_id||'')}">${esc(d.name||d.id||d.device_id)}</option>`).join('')}</select></label><label>AIN / Ger?tekennung<input id="autoAin" maxlength="128" required placeholder="Ger?tekennung"></label><label>Zielzustand<select id="autoOn"><option value="1">Ein</option><option value="0">Aus</option></select></label><button class="master-primary" ${devices.length?'':'disabled'}>Regel speichern</button></form><p class="master-copy">Die Regeldefinition wird lokal gespeichert. Die Ausf?hrung bleibt an die vorhandene, validierte Ger?te-/FRITZ!-Integration gebunden.</p></article><article class="master-panel"><div class="master-panel-head"><h3>Gespeicherte Regeln</h3><span>${rows.length}</span></div><div class="gc-list">${rows.length?rows.map(r=>`<div class="gc-list-row"><div><strong>${esc(r.name)}</strong><small>${esc(r.trigger)} ${esc(r.trigger_value||'')} ? ${esc(r.device_id)} ? ${r.on?'EIN':'AUS'}</small></div>${stateBadge(r.enabled!==false,'AKTIV','PAUSIERT')}<button class="secondary gc-auto-delete" data-id="${esc(r.id)}">L?schen</button></div>`).join(''):'<div class="gc-empty">Noch keine Regeln.</div>'}</div></article>`;
    $('autoDevice')?.addEventListener('change',()=>{const d=devices.find(x=>(x.id||x.device_id)===$('autoDevice').value);if(d&&$('autoAin'))$('autoAin').value=d.ain||d.id||d.device_id||''});$('autoDevice')?.dispatchEvent(new Event('change'));
    $('automationForm')?.addEventListener('submit',async ev=>{ev.preventDefault();try{await api('/api/v1/automations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('autoName').value.trim(),trigger:$('autoTrigger').value,trigger_value:$('autoTriggerValue').value.trim(),device_id:$('autoDevice').value,ain:$('autoAin').value.trim(),on:$('autoOn').value==='1',enabled:true})});toast('Regel gespeichert');renderAutomation()}catch(e){toast(e.message,'error')}});
    root.querySelectorAll('.gc-auto-delete').forEach(btn=>btn.addEventListener('click',async()=>{try{await api(`/api/v1/automations/${encodeURIComponent(btn.dataset.id)}`,{method:'DELETE'});toast('Regel gel?scht');renderAutomation()}catch(e){toast(e.message,'error')}}));
  }catch(e){root.innerHTML=`<div class="gc-error">Zeitpl?ne konnten nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderRecipes(){
  const root=mount('recipes','<div class="gc-loading">Rezepte werden geladen?</div>');
  try{
    const data=await api('/api/v1/recipes'),rows=data.recipes||[];
    root.innerHTML=`<article class="master-panel"><div class="master-panel-head"><h3>Neues Grow-Rezept</h3><span class="state-badge">DEKLARATIV</span></div><form id="recipeForm" class="gc-form"><label>Name<input id="recipeName" maxlength="80" required placeholder="z. B. Bl?te Woche 3"></label><label>Phase<select id="recipePhase"><option value="germination">Keimung</option><option value="vegetative">Vegetativ</option><option value="flowering">Bl?te</option><option value="flush">Sp?lung</option><option value="harvest">Ernte</option><option value="other">Sonstiges</option></select></label><label>Zieltemperatur ?C<input id="recipeTemp" type="number" min="0" max="60" step="0.1"></label><label>Zielfeuchte %<input id="recipeRh" type="number" min="0" max="100" step="1"></label><label>Ziel-VPD kPa<input id="recipeVpd" type="number" min="0" max="5" step="0.01"></label><label>Lichtzyklus<input id="recipeLight" maxlength="32" placeholder="18/6 oder 12/12"></label><label class="gc-span-2">Bew?sserungshinweis<textarea id="recipeWater" maxlength="500" rows="2"></textarea></label><label class="gc-span-2">Notizen<textarea id="recipeNotes" maxlength="3000" rows="3"></textarea></label><button class="master-primary">Rezept speichern</button></form><p class="master-copy">Rezepte speichern Sollwerte und Ablaufwissen. Sie schalten Ger?te nicht automatisch; dadurch kann ein fehlerhaftes Rezept keine Aktoren ungepr?ft steuern.</p></article><article class="master-panel"><div class="master-panel-head"><h3>Gespeicherte Rezepte</h3><span>${rows.length}</span></div><div class="gc-list">${rows.length?rows.map(r=>`<div class="gc-list-row"><div><strong>${esc(r.name)}</strong><small>${esc(r.phase)} ? ${r.target_temperature_c??'?'} ?C ? ${r.target_humidity_percent??'?'} % ? ${r.target_vpd_kpa??'?'} kPa ? ${esc(r.light_cycle||'kein Lichtzyklus')}</small>${r.notes?`<small>${esc(r.notes)}</small>`:''}</div><span class="state-badge">PROFIL</span><button class="secondary gc-recipe-delete" data-id="${esc(r.id)}">L?schen</button></div>`).join(''):'<div class="gc-empty">Noch keine Rezepte gespeichert.</div>'}</div></article>`;
    $('recipeForm')?.addEventListener('submit',async ev=>{ev.preventDefault();const n=id=>{const v=$(id).value.trim();return v===''?null:Number(v)};try{await api('/api/v1/recipes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('recipeName').value.trim(),phase:$('recipePhase').value,target_temperature_c:n('recipeTemp'),target_humidity_percent:n('recipeRh'),target_vpd_kpa:n('recipeVpd'),light_cycle:$('recipeLight').value.trim(),watering_note:$('recipeWater').value.trim(),notes:$('recipeNotes').value.trim()})});toast('Rezept gespeichert');renderRecipes()}catch(e){toast(e.message,'error')}});
    root.querySelectorAll('.gc-recipe-delete').forEach(btn=>btn.addEventListener('click',async()=>{try{await api(`/api/v1/recipes/${encodeURIComponent(btn.dataset.id)}`,{method:'DELETE'});toast('Rezept gel?scht');renderRecipes()}catch(e){toast(e.message,'error')}}));
  }catch(e){root.innerHTML=`<div class="gc-error">Rezepte konnten nicht geladen werden: ${esc(e.message)}</div>`}
}

async function renderTimelapse(){
  const root=mount('timelapse','<div class="gc-loading">Zeitrafferstatus wird geladen?</div>');
  try{
    const [status,runs,camera]=await Promise.all([api('/api/v1/timelapse/status'),api('/api/v1/timelapse/runs'),api('/api/v1/camera/status').catch(()=>({devices:[]}))]);
    const cams=(camera.devices||[]).filter(c=>c.capture_capable);
    root.innerHTML=`<div class="master-two-col"><article class="master-panel"><div class="master-panel-head"><h3>Zeitraffer-Steuerung</h3>${stateBadge(status.active,'L?UFT','BEREIT')}</div><form id="timelapseForm" class="gc-form"><label>Intervall Sekunden<input id="tlInterval" type="number" min="15" max="86400" value="${status.interval_seconds||300}" required></label><label>Max. Frames<input id="tlFrames" type="number" min="2" max="1000" value="${status.max_frames||72}" required></label><label class="gc-span-2">Kamera<select id="tlCamera"><option value="">Automatisch</option>${cams.map(c=>`<option value="${esc(c.id||c.camera_id||'')}">${esc(c.name||c.device||c.id||'Kamera')}</option>`).join('')}</select></label><button class="master-primary" ${status.active?'disabled':''}>Starten</button><button type="button" class="secondary" id="tlStop" ${status.active?'':'disabled'}>Stoppen</button></form><div class="gc-kv"><span>Frames</span><b>${status.frames||0} / ${status.max_frames||'?'}</b><span>Letztes Bild</span><b>${status.last_frame_at?esc(new Date(status.last_frame_at).toLocaleString('de-DE')):'?'}</b><span>Fehler</span><b>${esc(status.error||'keiner')}</b></div></article><article class="master-panel"><div class="master-panel-head"><h3>Letzte L?ufe</h3><span>${runs.runs?.length||0}</span></div><div class="gc-list">${(runs.runs||[]).length?(runs.runs||[]).map(r=>`<div class="gc-list-row"><div><strong>${esc(r.run_id)}</strong><small>${r.frames||0} Frames ? ${r.started_at?esc(new Date(r.started_at).toLocaleString('de-DE')):'?'}</small></div>${stateBadge(!r.error,r.active?'L?UFT':'FERTIG','FEHLER')}${r.preview?`<a class="secondary" target="_blank" rel="noopener" href="/api/v1/timelapse/runs/${encodeURIComponent(r.run_id)}/frames/${encodeURIComponent(r.preview)}">Vorschau</a>`:''}</div>`).join(''):'<div class="gc-empty">Noch kein Zeitraffer aufgenommen.</div>'}</div></article></div>`;
    $('timelapseForm')?.addEventListener('submit',async ev=>{ev.preventDefault();try{await api('/api/v1/timelapse/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({interval_seconds:Number($('tlInterval').value),max_frames:Number($('tlFrames').value),camera_id:$('tlCamera').value||null})});toast('Zeitraffer gestartet');setTimeout(renderTimelapse,800)}catch(e){toast(e.message,'error')}});
    $('tlStop')?.addEventListener('click',async()=>{try{await api('/api/v1/timelapse/stop',{method:'POST'});toast('Zeitraffer wird gestoppt');setTimeout(renderTimelapse,800)}catch(e){toast(e.message,'error')}});
  }catch(e){root.innerHTML=`<div class="gc-error">Zeitraffer konnte nicht geladen werden: ${esc(e.message)}</div>`}
}

const renderers={climate:renderClimate,irrigation:renderIrrigation,lighting:renderLighting,automation:renderAutomation,recipes:renderRecipes,growlog:renderGrowlog,recordings:renderRecordings,timelapse:renderTimelapse,settings:renderSettings,users:renderUsers,backups:renderBackups,updates:renderUpdates,extensions:renderExtensions};
$('automationRefreshMaster')?.addEventListener('click',renderAutomation);
window.addEventListener('gc:view',e=>{const fn=renderers[e.detail?.id];if(fn)fn()});
window.addEventListener('gc:refresh',()=>{const id=document.querySelector('.view.active')?.id;const fn=renderers[id];if(fn)fn()});
})();
