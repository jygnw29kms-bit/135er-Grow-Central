(()=>{
'use strict';
const $=id=>document.getElementById(id);
const text=(id,v)=>{const e=$(id);if(e)e.textContent=v;};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=(v,d=0)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d});
const state={page:'home',lamp:null,fan:null,smart:null,hk:null,activeCam:null,busy:{lamp:false,fan:false},sliderEdit:{lamp:false,fan:false},refreshBusy:false};
const pages={home:'Übersicht',devices:'Geräte',climate:'Klima',camera:'Live-Kamera',history:'Verlauf',rooms:'Räume',homekit:'Apple Home',more:'Mehr'};
let timer=0;
function notify(message){const e=$('toast');e.textContent=message;e.classList.add('show');clearTimeout(timer);timer=setTimeout(()=>e.classList.remove('show'),4200);}
async function api(url,body){
 const opts={cache:'no-store',credentials:'same-origin'};
 if(body!==undefined){opts.method='POST';opts.headers={'Content-Type':'application/json'};opts.body=JSON.stringify(body);}
 const response=await fetch(url,opts);
 let data;try{data=await response.json();}catch{data={};}
 if(!response.ok)throw Error(typeof data?.detail==='string'?data.detail:'HTTP '+response.status);
 return data;
}
function page(id){
 if(!pages[id])id='home';
 state.page=id;
 document.querySelectorAll('.page').forEach(e=>e.classList.toggle('active',e.id===id));
 document.querySelectorAll('button[data-page]').forEach(e=>{e.classList.toggle('selected',e.dataset.page===id);if(e.dataset.page===id)e.setAttribute('aria-current','page');else e.removeAttribute('aria-current')});
 text('pageTitle',pages[id]);
 document.title='Grow Central · '+pages[id];
 updateCamera();
 if(id==='rooms')loadRooms();
 if(id==='history')loadHistory();
 if(id==='homekit')loadHomekit();
 if(id==='more')api('/api/health').then(x=>text('aboutVersion',x.version||'—')).catch(()=>text('aboutVersion','Nicht verfügbar'));
 if(id==='devices')loadSmart(true);
 window.scrollTo(0,0);
}
function controlMarkup(kind){
 const lamp=kind==='lamp',title=lamp?'FC3000':'DF150-M';
 return '<article class="control" data-control="'+kind+'"><div class="controlhead"><div class="name"><div class="symbol">'+(lamp?'☼':'✳')+'</div><div><h3>'+title+'</h3><small>Mars Hydro · '+(lamp?'Licht':'Abluft')+'</small></div></div><button class="switch" data-power="'+kind+'" type="button">—</button></div><div class="ctlrow"><span>'+(lamp?'Helligkeit':'Lüfterstufe')+'</span><strong data-level-label="'+kind+'">—</strong></div><input aria-label="'+(lamp?'Helligkeit FC3000':'Lüfterstufe DF150-M')+'" data-slider="'+kind+'" class="slider" type="range" min="'+(lamp?10:25)+'" max="100" step="1" value="'+(lamp?10:25)+'"><div class="ctlrow"><span data-status-label="'+kind+'">Prüfe Verbindung …</span><button class="apply" data-apply="'+kind+'" type="button">Übernehmen</button></div><div class="ctlfoot"><span>'+(lamp?'Status: ':'Drehzahl: ')+'<b data-live-detail="'+kind+'">—</b></span><span data-read-age="'+kind+'">—</span></div><div class="ctlmsg" data-control-msg="'+kind+'"></div></article>';
}
function renderControls(){
 $('controlMount').innerHTML='<div class="controls">'+controlMarkup('lamp')+controlMarkup('fan')+'</div>';
 $('deviceControls').innerHTML='<div class="controls">'+controlMarkup('lamp')+controlMarkup('fan')+'</div>';
}
function setAll(selector,value){document.querySelectorAll(selector).forEach(e=>e.textContent=value);}
function setMessages(kind,message,error=false){document.querySelectorAll('[data-control-msg="'+kind+'"]').forEach(e=>{e.textContent=message;e.classList.toggle('err',error)})}
function setControls(kind,status){
 const latest=status?.fresh?status.latest:null;state[kind]=latest;
 const active=!!latest,level=kind==='lamp'?'brightness_percent':'setpoint_percent';
 const percent=active?latest[level]:null;
 document.querySelectorAll('[data-control="'+kind+'"]').forEach(root=>{
   const sw=root.querySelector('[data-power]'),slider=root.querySelector('[data-slider]'),apply=root.querySelector('[data-apply]');
   if(sw){sw.textContent=active?(latest.power_on?'Ein':'Aus'):'Keine Daten';sw.classList.toggle('on',active&&latest.power_on);sw.disabled=!active||state.busy[kind];}
   if(slider){slider.disabled=!active||!latest.power_on||state.busy[kind];if(!state.sliderEdit[kind]&&percent!=null)slider.value=percent;}
   if(apply)apply.disabled=!active||!latest.power_on||state.busy[kind];
 });
 if(!state.sliderEdit[kind])setAll('[data-level-label="'+kind+'"]',percent==null?'—':n(percent)+' %');
 setAll('[data-status-label="'+kind+'"]',active?'BLE live · '+(latest.power_on?'Ein':'Aus'):(status?.connected?'Warte auf Messung':'Nicht verbunden'));
 setAll('[data-live-detail="'+kind+'"]',!active?'—':kind==='lamp'?(latest.power_on?'Eingeschaltet':'Ausgeschaltet'):n(latest.rpm)+' RPM');
 setAll('[data-read-age="'+kind+'"]',active&&Number.isFinite(status.age_ms)?n(status.age_ms/1000,1)+' s alt':active?'Live':'Kein aktueller Wert');
}
function setMetrics(fan,lamp){
 const f=fan?.fresh?fan.latest:null,l=lamp?.fresh?lamp.latest:null;
 text('tempValue',f&&Number.isFinite(f.temperature_c)?n(f.temperature_c,1)+' °C':'—');
 text('humidityValue',f&&Number.isFinite(f.humidity_rh)?n(f.humidity_rh,1)+' % rF':'—');
 text('rpmValue',f&&Number.isFinite(f.rpm)?n(f.rpm)+' RPM':'—');
 text('lightValue',l?(l.power_on?n(l.brightness_percent)+' %':'Aus'):'—');
 text('tempAge',f?'Frischer BLE-Wert · '+n((fan.age_ms||0)/1000,1)+' s alt':'Kein frischer Sensorwert');
 let tiles=$('liveTiles').cloneNode(true);
 tiles.querySelectorAll('[id]').forEach(e=>e.removeAttribute('id'));
 tiles.querySelectorAll('.metric strong').forEach((e,i)=>e.textContent=[f?n(f.temperature_c,1)+' °C':'—',f?n(f.humidity_rh,1)+' % rF':'—',f?n(f.rpm)+' RPM':'—',l?(l.power_on?n(l.brightness_percent)+' %':'Aus'):'—'][i]);
 $('climateTiles').replaceChildren(tiles);
 const overlay=f?'🌡 '+n(f.temperature_c,1)+' °C    ◇ '+n(f.humidity_rh,1)+' % rF':'Keine aktuellen Klimamesswerte';
 document.querySelectorAll('.osdClimate').forEach(e=>e.textContent=overlay);
 text('climateDetails',f?'DF150-M · reale BLE-Messung, '+n((fan.age_ms||0)/1000,1)+' s alt.':'Keine frischen DF150-M-Messwerte.');
 text('bleRow',f&&l?'Beide BLE live':f||l?'Ein Gerät live':'Keine aktuellen Gerätewerte');
}
async function refreshLive(){
 if(state.refreshBusy)return;state.refreshBusy=true;
 try{
 const [fl,ff]=await Promise.allSettled([api('/api/mars-hydro/ble/fast-lamp-status'),api('/api/mars-hydro/ble/fast-fan-status')]);
 const lamp=fl.status==='fulfilled'?fl.value:{connected:false,fresh:false};
 const fan=ff.status==='fulfilled'?ff.value:{connected:false,fresh:false};
 setControls('lamp',lamp);setControls('fan',fan);setMetrics(fan,lamp);
 const ok=lamp.fresh&&fan.fresh;
 text('heroConnection',ok?'BEIDE GERÄTE LIVE':lamp.fresh||fan.fresh?'EIN GERÄT LIVE':'KEINE AKTUELLEN WERTE');
 text('systemBadge',ok?'Live verbunden':'Verbindung prüfen');
 $('systemBadge').classList.toggle('good',ok);$('systemBadge').classList.toggle('bad',!ok);
 text('coreStatus','Grow-Pi '+(ok?'verbunden':'erreichbar'));text('coreRow','Online');
 }catch(e){text('systemBadge','Verbindungsfehler');}finally{state.refreshBusy=false;}
}
async function command(kind,action,value){
 if(state.busy[kind])return;
 const current=state[kind];if(!current){notify('Gerät nicht erreichbar');return;}
 if(action!=='power'&&!current.power_on){notify('Gerät ist ausgeschaltet. Erst einschalten.');return;}
 state.busy[kind]=true;setMessages(kind,'Warte auf Gerätebestätigung …');
 document.querySelectorAll('[data-control="'+kind+'"] button').forEach(e=>e.disabled=true);
 try{
  const url=kind==='lamp'?'/api/mars-hydro/ble/fast-lamp-control':'/api/mars-hydro/ble/fast-fan-control';
  const response=await api(url,{action,value,confirm_physical_change:true});
  if(!response.device_report_confirmed)throw Error('Controller hat Änderung nicht bestätigt. Keine Wiederholung.');
  setMessages(kind,'Vom Controller bestätigt');
  state.sliderEdit[kind]=false;
  notify((kind==='lamp'?'FC3000':'DF150-M')+' · Änderung bestätigt');
 }catch(e){setMessages(kind,e.message,true);notify('Steuerung: '+e.message);}
 finally{state.busy[kind]=false;refreshLive();}
}
async function loadSmart(force=false){
 try{
 const data=await api('/api/v1/smarthome/overview'+(force?'?refresh=true':''));
 state.smart=data;const rows=(data.devices||[]).filter(x=>x.adapter==='fritz'||x.adapter==='tapo');
 if(!rows.length){const v='<p class="desc">Noch keine FRITZ!- oder Tapo-Geräte registriert. Die Adapter sind vorbereitet. Geräte in der erweiterten Verwaltung verbinden.</p>'; $('smartDevices').innerHTML=v;$('smartPreview').innerHTML=v;return;}
 const html=rows.map(x=>{
  const st=x.state||{},approved=!!x.approved,online=!!x.online;
  const subtitle=(x.adapter==='fritz'?'AVM FRITZ!':'TP-Link Tapo')+' · '+(online?'Online':approved?'Nicht erreichbar':'Nicht freigegeben');
  const values=[st.temperature_c!=null?n(st.temperature_c,1)+' °C':null,st.power_w!=null?n(st.power_w,1)+' W':null,st.energy_wh!=null?n(st.energy_wh/1000,2)+' kWh':null].filter(Boolean).join(' · ');
  return '<div class="smartitem"><div><b>'+esc(x.name)+'</b><small>'+esc(subtitle)+(values?' · '+esc(values):'')+'</small></div><div class="right"><button data-smart-id="'+esc(x.id)+'" '+(!approved||!x.writable||!online?'disabled':'')+' class="'+(st.on?'on':'')+'">'+(st.on===true?'Ein':st.on===false?'Aus':'Status —')+'</button></div></div>';
 }).join('');
 $('smartDevices').innerHTML=html;$('smartPreview').innerHTML=html;
 }catch(e){const m='FRITZ!/Tapo-Daten derzeit nicht erreichbar';$('smartDevices').textContent=m;$('smartPreview').textContent=m;}
}
async function switchSmart(id){
 const row=(state.smart?.devices||[]).find(x=>x.id===id);if(!row||!row.approved||!row.writable||!row.online||typeof row.state?.on!=='boolean')return;
 document.querySelectorAll('[data-smart-id]').forEach(e=>{if(e.dataset.smartId===id)e.disabled=true});
 try{await api('/api/v1/smarthome/devices/'+encodeURIComponent(id)+'/switch',{on:!row.state.on});notify('Gerätebefehl bestätigt');await loadSmart(true);}
 catch(e){notify('Schalten fehlgeschlagen: '+e.message);await loadSmart(true);}
}
async function loadHomekit(){
 try{
  const d=await api('/api/v1/homekit/status');state.hk=d;
  text('homekitRow',d.paired?'Gekoppelt':d.running?'Bereit zur Kopplung':'Nicht verbunden');
  $('hkData').innerHTML='<div class="statusrow"><span>Kopplung</span><strong>'+(d.paired?'Verbunden':'Nicht verbunden')+'</strong></div><div class="statusrow"><span>Veröffentlichte Geräte</span><strong>'+n(d.accessories_exported??0)+'</strong></div>'+ (d.accessories||[]).map(a=>'<div class="statusrow"><span>'+esc(a.name)+'</span><strong>'+esc((a.services||[]).join(' · '))+'</strong></div>').join('');
 }catch(e){text('homekitRow','Nicht erreichbar');text('hkData','Bridge-Status nicht erreichbar');}
}
async function loadRooms(){
 try{const d=await api('/api/v1/rooms');const rows=d.rooms||[];
 $('roomData').innerHTML=rows.length?rows.map(r=>'<article class="panel"><h3>'+esc(r.name||'Unbenannter Raum')+'</h3><p class="desc">Grow-Central Raum · '+esc(r.id)+'</p></article>').join(''):'<article class="panel"><p>Keine Räume angelegt.</p></article>';
 text('currentRoom',rows.length?(rows[0].name||'Growzelt'):'Growzelt');
 text('heroRoom',rows.length?'RAUM: '+(rows[0].name||'Growzelt'):'KEIN RAUM EINGERICHTET');
 }catch(e){text('roomData','Raumliste derzeit nicht erreichbar');}
}
async function loadHistory(){
 try{const d=await api('/api/mars-history/summary');const rows=d.latest||[];
 $('historyData').innerHTML=rows.length?rows.map(x=>'<div class="archiverow"><span>'+esc(x.device==='fan'?'DF150-M':x.device==='lamp'?'FC3000':x.device)+'</span><span>'+esc(x.recorded_at?new Date(x.recorded_at).toLocaleString('de-DE'):'Ohne Zeitstempel')+'</span><span>'+esc(x.device==='fan'?[x.temperature_c!=null?n(x.temperature_c,1)+' °C':null,x.humidity_rh!=null?n(x.humidity_rh,1)+' %':null,x.rpm!=null?n(x.rpm)+' RPM':null].filter(Boolean).join(' · '):x.power_on?'Ein':'Aus')+'</span></div>').join(''):'<p class="desc">Noch keine Archivdaten verfügbar.</p>';
 }catch(e){text('historyData','Archivdaten derzeit nicht erreichbar');}
}
function updateCamera(){
 const target=state.page==='camera'?'largeCam':state.page==='home'?'homeCam':null;
 if(state.activeCam===target)return;
 document.querySelectorAll('.camframe img').forEach(img=>img.remove());
 state.activeCam=target;
 if(target){
 const container=$(target),img=document.createElement('img');img.alt='Growzelt Live-Kamera';img.loading='eager';img.onerror=()=>{img.remove();container.querySelector('.camblank').textContent='Kamera derzeit nicht verfügbar';container.querySelector('.camblank').style.display='block';};
 container.prepend(img);img.src='/api/v1/camera/stream';
 container.querySelector('.camblank').style.display='none';
 }
}
function tick(){
 document.querySelectorAll('.osdClock').forEach(e=>e.textContent=new Date().toLocaleString('de-DE',{dateStyle:'short',timeStyle:'medium'}));
 text('clock',new Date().toLocaleString('de-DE',{dateStyle:'short',timeStyle:'short'}));
}
document.addEventListener('click',e=>{
 const pg=e.target.closest('[data-page],[data-open]');if(pg){page(pg.dataset.page||pg.dataset.open);return;}
 const pw=e.target.closest('[data-power]');if(pw){const k=pw.dataset.power;if(state[k])command(k,'power',state[k].power_on?0:1);return;}
 const apply=e.target.closest('[data-apply]');if(apply){const k=apply.dataset.apply;const slider=apply.closest('[data-control]').querySelector('[data-slider]');if(slider)command(k,k==='lamp'?'brightness':'speed',Number(slider.value));return;}
 const smart=e.target.closest('[data-smart-id]');if(smart){switchSmart(smart.dataset.smartId);return;}
});
document.addEventListener('input',e=>{if(!e.target.matches('[data-slider]'))return;const k=e.target.dataset.slider;state.sliderEdit[k]=true;document.querySelectorAll('[data-slider="'+k+'"]').forEach(s=>{if(s!==e.target)s.value=e.target.value});setAll('[data-level-label="'+k+'"]',e.target.value+' %');});
renderControls();tick();page('home');refreshLive();loadRooms();loadSmart();loadHomekit();
setInterval(()=>{tick();if(!document.hidden)refreshLive();},1600);
setInterval(()=>{if(!document.hidden){loadSmart();loadHomekit();}},30000);
document.addEventListener('visibilitychange',()=>{if(document.hidden){state.activeCam=null;document.querySelectorAll('.camframe img').forEach(img=>img.remove());}else{updateCamera();refreshLive();}});
if('serviceWorker' in navigator&&location.protocol==='https:')navigator.serviceWorker.register('/gc-worker.js',{scope:'/'}).catch(()=>{});
})();