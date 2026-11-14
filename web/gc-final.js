(()=>{
'use strict';
const $=id=>document.getElementById(id);
const text=(id,v)=>{const e=$(id);if(e)e.textContent=v;};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=(v,d=0)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d});
const state={page:'home',lamp:null,fan:null,smart:null,hk:null,activeCam:null,busy:{lamp:false,fan:false},sliderEdit:{lamp:false,fan:false},refreshBusy:false};
const pages={home:'Dashboard',growbook:'Growbuch',devices:'Geräte',climate:'Klima',camera:'Live-Kamera',history:'Verlauf',rooms:'Räume',homekit:'Apple Home',cloud:'Cloud',more:'Mehr'};
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
 if(id==='climate'){loadClimateOverview();loadClimateHistory();}
 if(id==='growbook'){loadRoomPlants();loadJournal();}
 if(id==='history')loadHistory();
 if(id==='homekit')loadHomekit();
 if(id==='cloud')cloudRefresh();
 if(id==='more')api('/api/health').then(x=>text('aboutVersion',x.version||'—')).catch(()=>text('aboutVersion','Nicht verfügbar'));
 if(id==='devices'){loadSmart(true);loadSoilUsb();}
 window.scrollTo(0,0);
}
function controlMarkup(kind){
 const lamp=kind==='lamp',model=lamp?'FC3000':'DF150-M';
 const src=lamp?'/static/mars-fc3000-transparent.png':'/static/mars-df150m-hires.jpg';
 return '<article class="control" data-control="'+kind+'">'+
  '<div class="controlhead"><div class="name"><h3>Mars Hydro '+model+'</h3><small>'+(lamp?'LED Grow Light':'Inline-Lüfter · BLE')+'</small></div>'+
  '<span class="switch" data-power-status="'+kind+'" aria-live="polite">Status —</span></div>'+
  '<div class="control-image"><img src="'+src+'" alt="Original Mars Hydro '+model+'" loading="eager" decoding="async"></div>'+
  '<div class="control-bottom"><div class="ctlrow"><span>'+(lamp?'Helligkeit':'Lüftergeschwindigkeit')+'</span><strong data-level-label="'+kind+'">—</strong></div>'+
  '<input class="slider" aria-label="'+model+' Sollstufe" data-slider="'+kind+'" type="range" min="'+(lamp?10:25)+'" max="100" value="'+(lamp?10:25)+'" step="1">'+
  '<div class="ctlrow control-actions"><span data-status-label="'+kind+'">Prüfe …</span><div class="control-buttons"><button class="apply" type="button" data-apply="'+kind+'" aria-label="'+model+' Stufe übernehmen">Übernehmen</button><button class="power-action" type="button" data-power="'+kind+'" aria-label="'+model+' ein- oder ausschalten" title="Gerät ein-/ausschalten">⏻</button></div></div></div>'+
  '<div class="ctlfoot"><span>'+(lamp?'Status:':'Drehzahl:')+' <b data-live-detail="'+kind+'">—</b></span><span data-read-age="'+kind+'">—</span></div>'+
  '<div class="ctlmsg" data-control-msg="'+kind+'"></div></article>';
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
   const sw=root.querySelector('[data-power]'),badge=root.querySelector('[data-power-status]'),slider=root.querySelector('[data-slider]'),apply=root.querySelector('[data-apply]');
   if(badge){badge.textContent=active?(latest.power_on?'● Ein':'Aus'):'Keine Daten';badge.classList.toggle('on',active&&latest.power_on);}
   if(sw){sw.classList.toggle('on',active&&latest.power_on);sw.disabled=!active||state.busy[kind];sw.setAttribute('aria-pressed',String(active&&!!latest.power_on));}
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
const soilOnboard={devices:[],busy:false,broker:null};
function soilStageLabel(device){
 const stages={DETECTED:'USB erkannt',CHECKING:'Prüfe Identität und Kalibrierung',NEEDS_FIRMWARE:'Firmware-Aktualisierung erforderlich',FLASHING:'Firmware wird installiert',CALIBRATION:'Kalibrierung prüfen',CALIBRATING:'Kalibrierung läuft',NETWORK:'WLAN/MQTT einrichten',PROVISIONING:'WLAN/TLS-MQTT wird eingerichtet',CONNECTING:'Prüfe Netzwerk-Identität',ASSIGN:'Bereit für Raumzuordnung',READY:'Sensor angenommen',ERROR:'Einrichtung unterbrochen',BLOCKED:'Sensor gesperrt'};
 return stages[device.state]||device.state||'USB erkannt';
}
function soilFormEditing(holder){
 if(!holder)return false;
 const current=document.activeElement;
 return !!(current&&holder.contains(current)&&current.closest('[data-soil-network], [data-soil-assign]'))||
  !!holder.querySelector('[data-soil-network][data-editing="true"], [data-soil-assign][data-editing="true"]');
}
async function loadSoilUsb(force=false){
 const holder=$('soilUsbDevices');if(!holder||soilOnboard.busy||(!force&&soilFormEditing(holder)))return;
 try{
  const [found,broker]=await Promise.all([api('/api/devices/usb'),api('/api/devices/usb/broker')]);
  if(!force&&soilFormEditing(holder))return;
  soilOnboard.devices=found.devices||[];
  soilOnboard.broker=broker;
  if(!soilOnboard.devices.length){
   holder.innerHTML='<p class="desc">Aktuell kein USB-Sensor angeschlossen. Bereits angenommene WLAN-Sensoren bleiben unabhängig vom USB-Anschluss registriert.</p>';return;
  }
  holder.innerHTML=soilOnboard.devices.map(d=>{
   const id=esc(d.id),name=esc(d.name||'Grow-Central ESP32-C3'),phase=esc(soilStageLabel(d));
   const message=esc(d.message||'');
   const firmware=esc(d.firmware||'Nicht bestätigt');
   const calibration=d.calibration_ready?'3-Punkt-Kalibrierung bestätigt':
     (d.air_calibrated||d.wet_calibrated||d.substrate_calibrated?'Kalibrierung unvollständig':'Kalibrierung noch nicht geprüft');
   const network=d.mqtt_connected?'MQTT verbunden':d.wifi_configured?'WLAN gespeichert · MQTT offline':'Netzwerk nicht eingerichtet';
   const actions='<button type="button" class="subtle" data-soil-inspect="'+id+'">Identität prüfen</button>'+
      (d.state==='NEEDS_FIRMWARE'&&found.firmware_ready?'<button type="button" class="subtle" data-soil-flash="'+id+'">Firmware '+esc(found.firmware_version)+' installieren</button>':'')+
      (d.device_id&&d.calibration_ready&&['NETWORK','ERROR','ASSIGN','READY'].includes(d.state)?'<button type="button" class="subtle" data-soil-connect="'+id+'">Verbindung prüfen</button>':'');
   const canNetwork=d.device_id&&d.calibration_ready&&['NETWORK','ERROR','ASSIGN'].includes(d.state);
   const hosts=(soilOnboard.broker?.hosts||[]).filter(v=>/^\d{1,3}(?:\.\d{1,3}){3}$/.test(v));
   const defaultHost=hosts[0]||'';
   const wifiForm=canNetwork?'<form data-soil-network="'+id+'"><label>WLAN-Name (2,4 GHz)<input name="ssid" maxlength="32" autocomplete="off" required placeholder="WLAN-Name"></label>'+
      '<label>WLAN-Kennwort<input name="password" type="password" autocomplete="off" required minlength="8" maxlength="63" placeholder="Nur an den Pi senden"></label>'+
      '<label>Broker auf dem Pi<select name="broker_host">'+hosts.map(v=>'<option value="'+esc(v)+'" '+(v===defaultHost?'selected':'')+'>'+esc(v)+'</option>').join('')+'</select></label>'+
      '<button type="submit" class="primary-btn" '+(!defaultHost?'disabled':'')+'>WLAN und sicheres MQTT einrichten</button></form>':'';
   const rooms=(state.rooms||[]);
   const assignForm=d.state==='ASSIGN'?'<form data-soil-assign="'+id+'"><label>Sensorname<input name="name" maxlength="120" value="'+name+'" required></label>'+
      '<label>Raum<select name="room_id" required>'+rooms.map(r=>'<option value="'+esc(r.id)+'">'+esc(r.name)+'</option>').join('')+'</select></label>'+
      '<button type="submit" class="primary-btn" '+(!rooms.length?'disabled':'')+'>Sensor diesem Raum zuordnen</button></form>'+
      (!rooms.length?'<p class="desc">Bitte unter Räume zunächst ein Growzelt wiederherstellen oder anlegen.</p>':''):'';
   return '<div class="smartitem" style="display:block"><strong>'+name+'</strong><p class="desc">'+phase+' · Firmware '+firmware+' · '+esc(calibration)+' · '+esc(network)+'</p>'+
      '<p class="desc">'+message+'</p><div class="control-buttons">'+actions+'</div>'+wifiForm+assignForm+'</div>';
  }).join('');
 }catch(e){holder.textContent='USB-Sensorprüfung nicht möglich: '+e.message;}
}
async function soilCommand(id,step,body){
 if(soilOnboard.busy)return;
 soilOnboard.busy=true;
 try{
  const d=soilOnboard.devices.find(x=>x.id===id);if(!d)throw Error('USB-Sensor nicht mehr verbunden');
  const result=await api('/api/devices/usb/'+encodeURIComponent(id)+'/'+step,body);
  notify(result.message||'Einrichtungsschritt gestartet');
 }catch(e){notify('Sensor: '+e.message);}
 finally{soilOnboard.busy=false;loadSoilUsb(true);}
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
  text('homekitRow',d.paired?'Verbunden':d.running?'Bereit':'Getrennt');
 text('homeLinkStatus',d.paired?'Verbunden':d.running?'Bereit':'Nicht verbunden');
  $('hkData').innerHTML='<div class="statusrow"><span>Kopplung</span><strong>'+(d.paired?'Verbunden':'Nicht verbunden')+'</strong></div><div class="statusrow"><span>Veröffentlichte Geräte</span><strong>'+n(d.accessories_exported??0)+'</strong></div>'+ (d.accessories||[]).map(a=>'<div class="statusrow"><span>'+esc(a.name)+'</span><strong>'+esc((a.services||[]).join(' · '))+'</strong></div>').join('');
 }catch(e){text('homekitRow','Nicht erreichbar');text('hkData','Bridge-Status nicht erreichbar');}
}
async function loadRooms(){
 try{
  const data=await api('/api/v1/rooms'),rooms=data.rooms||[];
  state.rooms=rooms;
  const selector=$('roomPicker');
  const previous=growJournal.roomId;
  if(selector){
   selector.replaceChildren();
   for(const room of rooms){const option=document.createElement('option');option.value=room.id;option.textContent=room.name;selector.add(option);}
  }
  growJournal.roomId=rooms.some(x=>x.id===previous)?previous:rooms[0]?.id||null;
  if(selector&&growJournal.roomId)selector.value=growJournal.roomId;
  const selected=rooms.find(x=>x.id===growJournal.roomId);
  text('currentRoom',selected?.name||'Kein Raum');text('heroRoom',selected?.name||'Kein Raum');
  const activeMarkup=rooms.length?rooms.map(x=>'<article class="panel"><h3>'+esc(x.name)+'</h3><p class="desc">Pflanzen: '+n(x.plant_count)+' · Geräte: '+n(x.device_count)+'</p><p class="desc">Growbuch ist diesem Raum automatisch zugeordnet.</p><button type="button" class="subtle" data-room-manage="'+esc(x.id)+'">Geräte zuordnen oder freigeben</button><button type="button" class="subtle" data-room-journal="'+esc(x.id)+'">Growbuch öffnen</button><button type="button" class="subtle" data-room-delete="'+esc(x.id)+'">Raum löschen (rückgängig)</button><div id="roomDevices-'+esc(x.id)+'"></div></article>').join(''):'<article class="panel"><p>Es ist noch kein aktiver Raum angelegt.</p></article>';
  const archived=data.archived_rooms||[];
  if(state.page==='climate')renderClimateRoomChoices();
  const archivedMarkup=archived.length?'<section class="panel"><h3>Archivierte Räume</h3><p class="desc">Pflanzen, Fotos, Growbuch und Messhistorie bleiben erhalten. Geräte werden nicht automatisch erneut zugewiesen.</p>'+archived.map(r=>'<div class="statusrow"><span>'+esc(r.name)+'</span><button type="button" class="subtle" data-room-restore="'+esc(r.id)+'">Wiederherstellen</button></div>').join('')+'</section>':'';
  $('roomData').innerHTML=activeMarkup+archivedMarkup;
  await Promise.all([loadJournal(),loadRecentEvents(),loadClimateOverview()]);
 }catch(e){text('roomData','Raumdaten nicht erreichbar');text('recentEvents','Raumdaten nicht erreichbar');}
}
async function manageRoomDevices(roomId){
 const holder=$('roomDevices-'+roomId);if(!holder)return;
 holder.textContent='Geräte werden geladen …';
 try{
  const result=await api('/api/v1/rooms/'+encodeURIComponent(roomId)+'/devices');
  const devices=result.devices||[];
  holder.innerHTML=devices.map(d=>'<label class="statusrow"><span>'+esc(d.name||d.id)+(d.room_id&&d.room_id!==roomId?' (anderem Raum zugeordnet)':!d.room_id?' (nicht zugeordnet)':'')+'</span><input type="checkbox" data-room-device="'+esc(d.id)+'" data-room-id="'+esc(roomId)+'" '+(d.assigned?'checked':'')+'></label>').join('')||'<p class="desc">Keine erkannten Geräte.</p>';
 }catch(e){holder.textContent='Geräte nicht erreichbar: '+e.message;}
}
async function roomDeviceChange(input){
 const roomId=input.dataset.roomId,deviceId=input.dataset.roomDevice,checked=input.checked;
 input.disabled=true;
 try{
  const base='/api/v1/rooms/'+encodeURIComponent(roomId)+'/devices';
  await journalRequest(checked?'POST':'DELETE',checked?base:base+'/'+encodeURIComponent(deviceId),checked?{device_id:deviceId}:undefined);
  await loadRooms();await manageRoomDevices(roomId);
  notify('Raumzuordnung gespeichert');
 }catch(e){input.checked=!checked;notify('Zuordnung fehlgeschlagen: '+e.message);}
 finally{input.disabled=false;}
}
async function archiveGrowRoom(roomId){
 const room=(state.rooms||[]).find(x=>x.id===roomId);if(!room)return;
 const reason='Raum „'+room.name+'“ archivieren? Alle Geräte werden freigegeben. Pflanzen, Fotos, Growbuch und Messhistorie bleiben erhalten. Der Raum kann wiederhergestellt werden.';
 if(!confirm(reason))return;
 try{await journalRequest('DELETE','/api/v1/rooms/'+encodeURIComponent(roomId));await loadRooms();notify('Raum archiviert, Hardware nicht zugeordnet');}
 catch(e){notify('Archivierung fehlgeschlagen: '+e.message);}
}
async function restoreGrowRoom(roomId){
 try{await journalRequest('POST','/api/v1/rooms/'+encodeURIComponent(roomId)+'/restore',{});await loadRooms();notify('Raum wiederhergestellt. Hardware bitte neu zuordnen.');}
 catch(e){notify('Wiederherstellen fehlgeschlagen: '+e.message);}
}
async function createGrowRoom(){
 const name=prompt('Name des neuen Grow-Raums');
 if(!name||!name.trim())return;
 try{await journalRequest('POST','/api/v1/rooms',{name:name.trim(),kind:'grow_tent'});await loadRooms();notify('Raum mit Growbuch angelegt');}
 catch(e){notify('Raum konnte nicht angelegt werden: '+e.message);}
}
let climateOverview={rooms:[]};
let climateHistoryRequest=0;
const chartMetricNames={
 temperature_c:['Temperatur','°C'],humidity_percent:['Luftfeuchtigkeit','% rF'],
 soil_moisture_percent:['Bodenfeuchte','%'],soil_temperature_c:['Bodentemperatur','°C'],
 vpd_kpa:['VPD','kPa'],co2_ppm:['CO₂','ppm'],ppfd_umol_m2_s:['PPFD','µmol/m²/s'],
 ec_ms_cm:['EC','mS/cm'],ph:['pH','pH'],power_w:['Leistung','W'],
 energy_wh:['Energie','Wh'],fan_rpm:['Lüfterdrehzahl','RPM'],
 fan_setpoint_percent:['Lüfter Sollstufe','%'],fan_power_on:['Lüfter Ein/Aus','bool'],
 lamp_brightness_percent:['Lampenstufe','%'],lamp_power_on:['Lampe Ein/Aus','bool'],
 airflow_cfm:['Luftmenge (geschätzt)','CFM'],pressure_pa:['Druck (geschätzt)','Pa']
};
function renderClimateRoomChoices(){
 const picker=$('climateRoomSelect');if(!picker)return;
 const prior=picker.value;
 const rooms=state.rooms||[];
 picker.innerHTML=rooms.map(r=>'<option value="'+esc(r.id)+'">'+esc(r.name)+'</option>').join('');
 if(rooms.some(r=>r.id===prior))picker.value=prior;
 else if(rooms.some(r=>r.id===growJournal.roomId))picker.value=growJournal.roomId;
}
function climateMetricRow(m){
 const title=chartMetricNames[m.metric]?.[0]||m.metric;
 if(m.status==='unknown')return '';
 const status=m.status==='target'?'Im Zielbereich':m.status==='low'?'Unter dem Zielbereich':'Über dem Zielbereich';
 return '<span class="'+(m.status==='target'?'good':'bad')+'">'+esc(title)+': '+esc(status)+' · '+n(m.value,1)+
  ' (Ziel '+n(m.target_min,1)+'–'+n(m.target_max,1)+')</span>';
}
function climateJudgementMarkup(items){
 if(!items.length)return '<p class="desc">Noch keine Pflanze im Raum. Zuerst unter Räume eine Pflanze mit Phase anlegen.</p>';
 return items.map(p=>{
  const label=p.status==='target'?'Klima passt zur Phase':p.status==='warning'?'Klima außerhalb des Phasenbereichs':
    p.status==='stale'?'Messwerte veraltet':'Keine vollständige Klimabewertung möglich';
  const tag=p.source==='grow_profile'?'Individuelles Kulturprofil':p.source==='cannabis_orientation'?'Cannabis-Orientierungswerte':'Noch keine phasenspezifischen Sollwerte';
  return '<div class="statusrow" style="display:block"><strong>'+esc(p.plant_name)+' · '+esc(phaseNames[p.phase]||p.phase)+
   '</strong><p class="'+(p.status==='target'?'good':p.status==='warning'?'bad':'desc')+'">'+esc(label)+'</p>'+
   '<p class="desc">'+esc(tag)+(p.age_seconds!=null?' · Messung '+Math.round(p.age_seconds/60)+' Min. alt':'')+'</p>'+
   '<div class="desc">'+(p.metrics||[]).map(climateMetricRow).filter(Boolean).join(' · ')+'</div></div>';
 }).join('');
}
async function loadClimateOverview(){
 try{
  const data=await api('/api/v1/rooms/climate-overview');
  climateOverview=data;
  const rooms=data.rooms||[];
  const first=rooms.find(r=>r.room_id===growJournal.roomId)||rooms[0];
  const all=rooms.flatMap(r=>r.plants||[]);
  text('homePhaseClimate','');
  $('homePhaseClimate').innerHTML=climateJudgementMarkup(all);
  $('climatePhasePanel').innerHTML=climateJudgementMarkup(all);
  const picked=$('climateRoomSelect')?.value;
  const room=rooms.find(r=>r.room_id===picked)||first;
  const soil=room?.snapshot?.soil_moisture_percent;
  const captured=Date.parse(room?.snapshot?.timestamp||'');
  const fresh=Number.isFinite(captured)&&Date.now()-captured>=0&&Date.now()-captured<=15*60*1000;
  const validCalibration=room?.snapshot?.soil_calibration_status!=='required';
  const show=Number.isFinite(soil)&&fresh&&validCalibration;
  $('homeSoilPanel').hidden=!show;
  if(show){
   text('homeSoilValue',n(soil,1)+' %');
   text('homeSoilSource',room.room_name+' · reale Messung · '+Math.round((Date.now()-captured)/60000)+' Min. alt');
  }
  const status=room?.snapshot?.soil_measurement_status;
  const unavailable=status==='sensor_fault'?'Sensorfehler: ADC-Signal instabil. Messung ungültig.':
    status==='out_of_calibration_range'?'Bodensensor außerhalb des kalibrierten Bereichs. Messung ungültig.':
    'Kein frischer, kalibrierter und einem aktiven Raum zugeordneter Bodensensorwert.';
  text('climateSoilValue',show?room.room_name+' · '+n(soil,1)+' % · gemessen':unavailable);
 }catch(e){
  text('homePhaseClimate','Klimabewertung nicht erreichbar.');
  text('climatePhasePanel','Klimabewertung nicht erreichbar: '+e.message);
  $('homeSoilPanel').hidden=true;
  text('climateSoilValue','Bodenfeuchte derzeit nicht erreichbar.');
 }
}
function climateCurve(metric,rows){
 if(!rows.length)return '';
 const title=chartMetricNames[metric]||[metric,''];
 const series=rows.filter(r=>Number.isFinite(Number(r.value))&&Number.isFinite(Date.parse(r.recorded_at)));
 if(!series.length)return '';
 const vals=series.map(r=>Number(r.value));
 const low=Math.min(...vals),high=Math.max(...vals),pad=(high-low)||1;
 const first=Date.parse(series[0].recorded_at),last=Date.parse(series[series.length-1].recorded_at),span=Math.max(last-first,1);
 const points=series.map(r=>{
  const x=36+568*(Date.parse(r.recorded_at)-first)/span;
  const y=116-96*(Number(r.value)-low)/pad;
  return x.toFixed(1)+','+y.toFixed(1);
 }).join(' ');
 const timeline=series.length>1?'<polyline points="'+points+'" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>':
 '<circle cx="36" cy="116" r="3" fill="currentColor"/>';
 const startLabel=new Date(first).toLocaleDateString('de-DE'),endLabel=new Date(last).toLocaleDateString('de-DE');
 const estimation=series.some(r=>r.source_kind==='estimated_show_only')?' · Nur berechnet, kein Sensorwert':'';
 return '<article class="panel"><h4>'+esc(title[0])+' · '+esc(title[1])+'</h4>'+
  '<p class="desc">'+series.length+' echte Archivpunkte · Min '+n(low,1)+' · Max '+n(high,1)+estimation+'</p>'+
  '<svg viewBox="0 0 640 152" role="img" aria-label="'+esc(title[0])+' als historische Messkurve" style="width:100%;max-height:210px">'+
  '<path d="M36 15V116H604" fill="none" stroke="currentColor" opacity=".4"/>'+
  '<text x="32" y="13" font-size="11" fill="currentColor">'+n(high,1)+'</text>'+
  '<text x="32" y="131" font-size="11" fill="currentColor">'+n(low,1)+'</text>'+timeline+
  '<text x="36" y="147" font-size="11" fill="currentColor">'+esc(startLabel)+'</text>'+
  '<text x="604" y="147" text-anchor="end" font-size="11" fill="currentColor">'+esc(endLabel)+'</text></svg></article>';
}
async function loadClimateHistory(){
 const holder=$('climateHistoryCharts');if(!holder)return;
 renderClimateRoomChoices();
 const roomId=$('climateRoomSelect')?.value;
 if(!roomId){holder.textContent='Kein aktiver Raum. Bitte unter Räume einen Raum anlegen oder wiederherstellen.';return;}
 const seq=++climateHistoryRequest;
 holder.textContent='Lade Langzeitmesswerte …';
 try{
  const hours=Number($('climateTimeSelect')?.value||24);
  const start=hours?new Date(Date.now()-hours*3600000).toISOString():null;
  const url='/api/v1/history/points?room_id='+encodeURIComponent(roomId)+'&limit=10000'+(start?'&start='+encodeURIComponent(start):'');
  const d=await api(url);
  if(seq!==climateHistoryRequest)return;
  const grouped=new Map();
  for(const row of d.points||[]){
   if(!grouped.has(row.metric))grouped.set(row.metric,[]);
   grouped.get(row.metric).push(row);
  }
  const html=[...grouped.entries()].map(([metric,rows])=>climateCurve(metric,rows)).filter(Boolean).join('');
  holder.innerHTML=html||'<p class="desc">Für diesen Raum liegen im ausgewählten Zeitraum noch keine archivierten Messwerte vor. Diagramme erscheinen erst mit echten Messpunkten.</p>';
  if((d.points||[]).length===10000)holder.insertAdjacentHTML('beforeend','<p class="desc">Anzeige auf die letzten 10.000 Messpunkte begrenzt; ältere Daten bleiben im Archiv erhalten.</p>');
 }catch(e){if(seq===climateHistoryRequest)holder.textContent='Messverlauf nicht verfügbar: '+e.message;}
}
async function loadHistory(){
 try{const d=await api('/api/mars-history/summary');const rows=d.latest||[];
 $('historyData').innerHTML=rows.length?rows.map(x=>'<div class="archiverow"><span>'+esc(x.device==='fan'?'DF150-M':x.device==='lamp'?'FC3000':x.device)+'</span><span>'+esc(x.recorded_at?new Date(x.recorded_at).toLocaleString('de-DE'):'Ohne Zeitstempel')+'</span><span>'+esc(x.device==='fan'?[x.temperature_c!=null?n(x.temperature_c,1)+' °C':null,x.humidity_rh!=null?n(x.humidity_rh,1)+' %':null,x.rpm!=null?n(x.rpm)+' RPM':null].filter(Boolean).join(' · '):x.power_on?'Ein':'Aus')+'</span></div>').join(''):'<p class="desc">Noch keine Archivdaten verfügbar.</p>';
 }catch(e){text('historyData','Archivdaten derzeit nicht erreichbar');}
}
function updateCamera(force=false){
 const target=state.page==='camera'?'largeCam':state.page==='home'?'homeCam':null;
 if(state.activeCam===target&&!force)return;
 document.querySelectorAll('.camframe img').forEach(img=>img.remove());
 state.activeCam=target;
 if(target){
 const container=$(target),img=document.createElement('img');img.alt='Growzelt Live-Kamera';img.loading='eager';img.onerror=()=>{img.remove();container.querySelector('.camblank').textContent='Kamera derzeit nicht verfügbar';container.querySelector('.camblank').style.display='block';};
 container.prepend(img);img.src='/api/v1/camera/stream'+(cam.resolution&&cam.cameraId?'?camera_id='+encodeURIComponent(cam.cameraId)+'&width='+encodeURIComponent(cam.resolution.split('x')[0])+'&height='+encodeURIComponent(cam.resolution.split('x')[1]):'');
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
setInterval(()=>{tick();if(!document.hidden)refreshLive();},1600);
setInterval(()=>{if(!document.hidden){loadSmart();loadHomekit();}},30000);
document.addEventListener('visibilitychange',()=>{if(document.hidden){state.activeCam=null;document.querySelectorAll('.camframe img').forEach(img=>img.remove());}else{updateCamera();refreshLive();}});
if('serviceWorker' in navigator&&location.protocol==='https:')navigator.serviceWorker.register('/gc-worker.js',{scope:'/'}).catch(()=>{});

// Camera settings use existing V4L2 API; no mock sliders or unsupported fields.
const cam={cameraId:null,modes:[],resolution:'',settingsLoaded:false};
const names={brightness:'Helligkeit',contrast:'Kontrast',saturation:'Farbsättigung',
 sharpness:'Schärfe',gain:'Verstärkung',white_balance_automatic:'Automatischer Weißabgleich',
 white_balance_temperature:'Farbtemperatur',power_line_frequency:'Netzfrequenz',
 backlight_compensation:'Gegenlichtausgleich',auto_exposure:'Belichtung',
 exposure_time_absolute:'Belichtungszeit',exposure_dynamic_framerate:'Dynamische Bildrate',
 pan_absolute:'Horizontal bewegen',tilt_absolute:'Vertikal bewegen',
 focus_absolute:'Fokus',focus_automatic_continuous:'Autofokus',zoom_absolute:'Zoom'};
async function cameraLoad(){
 try{
  const d=await api('/api/v1/camera/status');
  const device=(d.devices||[]).find(x=>x.id===d.selected_camera_id)||d.devices?.[0];
  if(!device||!d.ready)throw Error('Keine betriebsbereite Kamera');
  cam.cameraId=device.id;cam.modes=device.mjpeg_modes||[];
  const select=$('cameraMode');
  if(select){const chosen=cam.resolution;select.replaceChildren();
    for(const mode of cam.modes){const op=document.createElement('option');op.value=mode.width+'x'+mode.height;op.textContent=mode.width+' × '+mode.height;select.append(op);}
    select.value=chosen&&[...select.options].some(o=>o.value===chosen)?chosen:([ ...select.options].some(o=>o.value==='1280x720')?'1280x720':(select.options[0]?.value||''));
    cam.resolution=select.value;
  }
  text('cameraSettingsStatus',device.name+' · '+cam.modes.length+' unterstützte Auflösungen');
  if(state.page==='camera')updateCamera(true);
 }catch(e){text('cameraSettingsStatus','Kamera: '+e.message);}
}
function cameraInput(c){
 if(!c.writable)return '';
 const name=names[c.name]||c.name;
 const min=Number(c.min),max=Number(c.max),step=Number(c.step)||1;
 let field='';
 if(c.menu?.length){
  field='<select data-camera-input="'+esc(c.name)+'">'+c.menu.map(o=>'<option value="'+o.value+'" '+(o.value===c.value?'selected':'')+'>'+esc(o.label)+'</option>').join('')+'</select>';
 }else if(min===0&&max===1){
  field='<select data-camera-input="'+esc(c.name)+'"><option value="1" '+(c.value===1?'selected':'')+'>Ein</option><option value="0" '+(c.value===0?'selected':'')+'>Aus</option></select>';
 }else if(Number.isFinite(min)&&Number.isFinite(max)&&max>min){
  field='<input data-camera-input="'+esc(c.name)+'" type="number" min="'+min+'" max="'+max+'" step="'+step+'" value="'+c.value+'">';
 }else return '';
 return '<div class="camera-setting"><label>'+esc(name)+'</label><div class="camera-setting-actions">'+field+'<button type="button" class="subtle" data-camera-apply="'+esc(c.name)+'">Setzen</button></div></div>';
}
async function cameraLoadControls(){
 try{
  const d=await api('/api/v1/camera/controls?camera_id='+encodeURIComponent(cam.cameraId||'cam0'));
  const controls=(d.controls||[]).filter(c=>c.writable);
  $('cameraControls').innerHTML=controls.length?controls.map(cameraInput).join(''):'<p>Keine veränderbaren Kameraeinstellungen vorhanden.</p>';
  cam.settingsLoaded=true;
  text('cameraSettingsStatus',controls.length+' verfügbare Kameraeinstellungen');
 }catch(e){text('cameraSettingsStatus','Bildeinstellungen nicht verfügbar: '+e.message);}
}
async function cameraApply(control){
 const input=[...document.querySelectorAll('[data-camera-input]')].find(x=>x.dataset.cameraInput===control);
 if(!input||!cam.cameraId)return;
 const value=Number(input.value);if(!Number.isInteger(value))return;
 const button=[...document.querySelectorAll('[data-camera-apply]')].find(x=>x.dataset.cameraApply===control);
 if(button)button.disabled=true;
 try{
  await api('/api/v1/camera/controls',{camera_id:cam.cameraId,control,value});
  notify('Kameraeinstellung übernommen');await cameraLoadControls();
 }catch(e){notify('Kamera: '+e.message);}finally{if(button)button.disabled=false;}
}
$('cameraMode')?.addEventListener('change',e=>{cam.resolution=e.target.value;updateCamera(true);});
$('cameraRefresh')?.addEventListener('click',()=>cameraLoad());
$('cameraSettingsToggle')?.addEventListener('click',async()=>{
 const panel=$('cameraSettingsPanel');panel.hidden=!panel.hidden;
 $('cameraSettingsToggle').setAttribute('aria-expanded',String(!panel.hidden));
 if(!panel.hidden&&!cam.settingsLoaded)await cameraLoadControls();
});
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-camera-apply]');
 if(b)cameraApply(b.dataset.cameraApply);
});

const accessMode={local:false,remote:false,lastCheck:0,busy:false};
async function detectAccessMode(){
 if(accessMode.busy)return;
 accessMode.busy=true;
 const fromCloud=location.protocol==='https:'&&location.hostname==='135ercloud.grow-central.de';
 const localOrigin=location.hostname.endsWith('.local')||location.hostname==='localhost'||location.hostname.startsWith('192.168.')||location.hostname.startsWith('10.');
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),2200);
 try{
   if(!navigator.onLine){
     accessMode.local=false;accessMode.remote=false;
     text('networkMode','Offline');text('cloudAccessMode','Keine Netzwerkverbindung');
     text('cloudRemoteStatus','Nicht erreichbar');return;
   }
   if(fromCloud){
     accessMode.local=false;
     text('networkMode','Cloud');text('cloudAccessMode','HTTPS-Cloudzugang');
     // The authenticated cloudRefresh result owns the actual remote-channel status.
     return;
   }
   const result=await fetch('/api/health',{cache:'no-store',credentials:'same-origin',signal:controller.signal});
   const type=result.headers.get('content-type')||'';
   const data=type.includes('json')?await result.json():{};
   accessMode.local=result.ok&&data&&typeof data==='object'&&data.status!=='error';
   text('networkMode',accessMode.local?'Direkt · Heimnetz':'Lokal nicht erreichbar');
   text('cloudAccessMode',accessMode.local?'Lokaler Grow-Pi':'Lokale Verbindung unterbrochen');
   text('cloudRemoteStatus',accessMode.local?'Cloud-Status wird geprüft':'Nicht verfügbar');
   if(!accessMode.local&&localOrigin)text('cloudFeedback','Lokaler Zugriff unterbrochen. Der HTTPS-Fernzugriff ist noch nicht freigegeben.');
 }catch(e){
   accessMode.local=false;
   text('networkMode','Verbindung getrennt');
   text('cloudAccessMode','Grow-Pi nicht erreichbar');
   text('cloudRemoteStatus','Nicht verfügbar');
 }finally{
   clearTimeout(timeout);accessMode.lastCheck=Date.now();accessMode.busy=false;
 }
}
window.addEventListener('online',detectAccessMode);
window.addEventListener('offline',detectAccessMode);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)detectAccessMode();});
setInterval(()=>{if(!document.hidden)detectAccessMode();},12000);

let cloudBusy=false;
function cloudPairDisplay(pair){
 const status=pair?.status||'not_started';
 const linked=status==='paired';
 const pending=status==='authorization_pending';
 text('cloudPairState',linked?'Mit Cloud-Konto verbunden':pending?'Freigabe ausstehend':status==='not_started'?'Noch nicht zugeordnet':status);
 const code=$('cloudPairCodeBox');
 if(code)code.hidden=!pending;
 text('cloudPairCode',pending?(pair.user_code||'—'):'—');
 text('cloudExpiry',pending&&pair.expires_at?'Gültig bis '+new Date(Number(pair.expires_at)*1000).toLocaleTimeString('de-DE'):'');
 const href=String(pair?.verification_uri_complete||pair?.verification_uri||'');
 const link=$('cloudPairUrl');
 if(link){
  try{
   const u=new URL(href);
   if(u.protocol==='https:'&&u.hostname==='135ercloud.grow-central.de'){link.href=u.href;link.hidden=!pending;}
   else{link.hidden=true;}
  }catch{link.hidden=true;}
 }
 $('cloudPairStart').hidden=linked||pending;
 $('cloudPairCancel').hidden=!pending;
}
async function cloudRefresh(){
 try{
  const result=await api('/api/cloud/status');
  text('cloudServer',result.host||'Nicht konfiguriert');
  text('cloudDetail',result.detail||'Keine Statusmeldung');
  const reachable=result.connected===true;
  text('cloudState',reachable?'Cloud-Fernkanal verbunden':result.health_reachable?'Cloud-Server online · Gerät getrennt':'Cloud-Verbindung getrennt');
  $('cloudState').classList.toggle('good',reachable);
  $('cloudState').classList.toggle('bad',!reachable);
  cloudPairDisplay(result.pairing||{});
  text('cloudRemoteStatus',result.connected?'Cloud-Fernkanal verbunden':result.health_reachable?'Cloud erreichbar · Fernkanal getrennt':'Cloud nicht erreichbar');
  text('cloudLinkRow',result.connected?'Verbunden':'Getrennt');
  text('cloudHomeStatus',result.connected?'Verbunden':'Getrennt');
 }catch(e){text('cloudState','Nicht erreichbar');text('cloudFeedback','Cloud-Status konnte nicht geladen werden: '+e.message);}
}
async function cloudPairStart(){
 if(cloudBusy)return;
 cloudBusy=true;$('cloudPairStart').disabled=true;
 text('cloudFeedback','Erstelle sicheren Kopplungscode …');
 try{
  const result=await api('/api/cloud/pair/start',{name:'Grow Central Grow-Pi'});
  if(result.status==='already_paired'){text('cloudFeedback','Dieses Gerät ist bereits zugeordnet.');}
  else{text('cloudFeedback','Code im Cloud-Konto bestätigen. Danach wird die Zuordnung automatisch übernommen.');}
  cloudPairDisplay(result);await cloudRefresh();
 }catch(e){text('cloudFeedback','Kopplung fehlgeschlagen: '+e.message);}
 finally{cloudBusy=false;$('cloudPairStart').disabled=false;}
}
async function cloudPairCancel(){
 if(cloudBusy)return;
 cloudBusy=true;
 try{await api('/api/cloud/pair/cancel',{});text('cloudFeedback','Kopplung abgebrochen.');await cloudRefresh();}
 catch(e){text('cloudFeedback','Abbruch fehlgeschlagen: '+e.message);}
 finally{cloudBusy=false;}
}
$('cloudPairStart')?.addEventListener('click',cloudPairStart);
$('cloudPairRefresh')?.addEventListener('click',cloudRefresh);
$('cloudPairCancel')?.addEventListener('click',cloudPairCancel);
setInterval(()=>{if(!document.hidden&&state.page==='cloud')cloudRefresh();},10000);

// Final Master: inline scalable SVG icons, no icon fonts or raster scaling.
const svgPaths={
home:'<path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-7h6v7"/>',
layers:'<path d="m12 2 9 5-9 5-9-5z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
thermometer:'<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0z"/><path d="M12 11v7"/>',
droplets:'<path d="M12 2C10 5 5 10 5 14a7 7 0 0 0 14 0c0-4-5-9-7-12z"/>',
fan:'<path d="M12 12c-4-9-8-8-8-4 0 2 2 4 8 4zm0 0c9-4 8-8 4-8-2 0-4 2-4 8zm0 0c4 9 8 8 8 4 0-2-2-4-8-4zm0 0c-9 4-8 8-4 8 2 0 4-2 4-8z"/><circle cx="12" cy="12" r="2"/>',
sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
camera:'<rect x="2" y="5" width="15" height="14" rx="2"/><path d="m17 10 5-3v10l-5-3"/><circle cx="9" cy="12" r="3"/>',
book:'<path d="M12 6C9 4 5 4 2 5v14c4-1 7 0 10 2 3-2 6-3 10-2V5c-3-1-7-1-10 1z"/><path d="M12 6v15"/>',
grid:'<rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/>',
house:'<path d="m3 11 9-8 9 8v10H3z"/><path d="M9 21v-7h6v7"/>',
cloud:'<path d="M5 19a5 5 0 0 1-1-10 8 8 0 0 1 15 1 4 4 0 0 1-1 9z"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="M9 2h6l1 3 2 1 3-1 2 5-3 2v2l3 2-2 5-3-1-2 1-1 3H9l-1-3-2-1-3 1-2-5 3-2v-2L1 10l2-5 3 1 2-1z"/>',
wifi:'<path d="M2 8a15 15 0 0 1 20 0M5 12a10 10 0 0 1 14 0m-11 4a5 5 0 0 1 8 0"/><circle cx="12" cy="20" r="1"/>',
history:'<path d="M3 12a9 9 0 1 0 3-7"/><path d="M3 3v5h5M12 7v5l4 3"/>'
};
function renderIcons(root=document){
 root.querySelectorAll('[data-icon]').forEach(el=>{
  const paths=svgPaths[el.dataset.icon];if(!paths)return;
  el.innerHTML='<svg class="gc-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true">'+paths+'</svg>';
 });
}
const growJournal={roomId:null,entries:[],selectedId:null,tab:'entries',editingId:null,loading:false,sequence:0,plants:[]};
const catLabels={note:'Notiz',watering:'Bewässerung',feeding:'Düngung',training:'Training',defoliation:'Entlaubung',pest:'Schädlingskontrolle',flowering:'Blüte',photo:'Foto',observation:'Beobachtung',diagnosis:'Diagnose',repotting:'Umtopfen',harvest:'Ernte',other:'Sonstiges'};
const niceDate=value=>{const time=new Date(value||'');return isNaN(time)?'Ohne Datum':time.toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});};
const shortDate=value=>{const time=new Date(value||'');return isNaN(time)?'—':time.toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric'});};
function journalPath(){return growJournal.roomId?'/api/v1/rooms/'+encodeURIComponent(growJournal.roomId):null;}
async function loadJournal(){
 const root=journalPath();
 if(!root){$('journalPreview').innerHTML='<p class="empty-text">Zuerst einen Raum auswählen.</p>';text('journalFullList','Kein Raum gewählt.');return;}
 const seq=++growJournal.sequence;
 try{
  const [journal,plants]=await Promise.all([api(root+'/journal'),api(root+'/plants')]);
  if(seq!==growJournal.sequence)return;
  growJournal.entries=(journal.entries||[]).slice().sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||'')));
  growJournal.plants=plants.plants||[];
  renderRoomPlantProfiles();
  if(!growJournal.entries.find(x=>x.id===growJournal.selectedId))growJournal.selectedId=growJournal.entries[0]?.id||null;
  renderJournal();
 }catch(e){$('journalPreview').innerHTML='<p class="empty-text">Growbuch nicht erreichbar: '+esc(e.message)+'</p>';text('journalFullList','Growbuchdaten konnten nicht geladen werden.');}
}
function journalEntryPreview(row){
 return '<button type="button" class="journal-entry '+(row.id===growJournal.selectedId?'active':'')+'" data-journal-select="'+esc(row.id)+'">'+
 '<span>'+esc(catLabels[row.category]||row.category||'Eintrag')+'</span><small>'+shortDate(row.created_at)+'</small><span aria-hidden="true">›</span></button>';
}
function journalEntryDetail(row){
 if(!row)return '<p class="empty-text">Noch keine Einträge vorhanden. Über „Eintrag“ kannst du die erste Beobachtung anlegen.</p>';
 const safeId=esc(row.id);
 const photo=row.photo_id?'<img class="journal-photo" src="/api/v1/grow-photos/'+encodeURIComponent(row.photo_id)+'" alt="Foto des Growbucheintrags" loading="lazy">':'';
 const editor=row.photo_id?'':'<button type="button" data-journal-edit="'+safeId+'">Bearbeiten</button>';
 return '<header><h4>'+esc(row.title||catLabels[row.category]||'Eintrag')+'</h4><div class="toolbar">'+editor+
 '<button type="button" data-journal-delete="'+safeId+'">Löschen</button></div></header>'+
 '<small>'+niceDate(row.created_at)+' · '+esc(catLabels[row.category]||row.category||'')+'</small>'+
 '<p>'+esc(row.text||row.note||'Keine weiteren Notizen.')+'</p>'+photo;
}
function renderJournal(){
 const entries=growJournal.entries;
 const active=growJournal.tab;
 document.querySelectorAll('[data-journal-tab]').forEach(b=>b.classList.toggle('active',b.dataset.journalTab===active));
 let filtered=entries;
 if(active==='notes')filtered=entries.filter(x=>['note','observation'].includes(x.category));
 if(active==='phases'){
  const plants=growJournal.plants;
  $('journalPreview').innerHTML=plants.length?plants.map(x=>'<div class="journal-entry"><span>'+esc(x.name)+'</span><small>'+esc(x.phase||'Keine Phase')+'</small></div>').join(''):'<p class="empty-text">Noch keine Pflanzen erfasst.</p>';
  $('journalSelected').innerHTML='<h4>Pflanzenphasen</h4><p>Hier werden ausschließlich die tatsächlich angelegten Pflanzen und deren gespeicherte Phasen angezeigt.</p>';
 }else if(active==='overview'){
  $('journalPreview').innerHTML='<div class="journal-entry"><span>Journal</span><small>'+entries.length+' Einträge</small></div><div class="journal-entry"><span>Pflanzen</span><small>'+growJournal.plants.length+' vorhanden</small></div>';
  $('journalSelected').innerHTML='<h4>Grow-Übersicht</h4><p>'+entries.length+' dokumentierte Einträge in diesem Raum. '+growJournal.plants.length+' Pflanzen hinterlegt.</p>';
 }else{
  $('journalPreview').innerHTML=filtered.length?filtered.slice(0,8).map(journalEntryPreview).join(''):'<p class="empty-text">Noch keine '+(active==='notes'?'Notizen':'Growbucheinträge')+' gespeichert.</p>';
  const row=filtered.find(x=>x.id===growJournal.selectedId)||filtered[0]||null;
  $('journalSelected').innerHTML=journalEntryDetail(row);
 }
 const full=$('journalFullList');
 if(full)full.innerHTML=entries.length?entries.map(row=>'<article class="journal-item"><h4>'+esc(catLabels[row.category]||row.category||'')+' · '+esc(row.title)+'</h4><small>'+niceDate(row.created_at)+'</small><p>'+esc(row.text||row.note||'')+'</p>'+ (row.photo_id?'<img class="journal-photo" src="/api/v1/grow-photos/'+encodeURIComponent(row.photo_id)+'" alt="Growfoto" loading="lazy">':'')+
 '<div class="toolbar">'+(row.photo_id?'':'<button class="subtle" data-journal-edit="'+esc(row.id)+'">Bearbeiten</button>')+'<button class="subtle" data-journal-delete="'+esc(row.id)+'">Löschen</button></div></article>').join(''):'<p class="empty-text">Keine Einträge vorhanden. Nutze „Neuer Eintrag“.</p>';
}

const phaseNames={germination:'Keimung',seedling:'Sämling',vegetative:'Wachstum',flowering:'Blüte',flush:'Spülen',finish:'Abschluss',harvest:'Ernte',completed:'Abgeschlossen',other:'Sonstige'};
const substrateNames={peat_mix:'Torf-/Erdmischung',coco_mix:'Kokos-/Perlitmischung',living_soil:'Living Soil',compost_mix:'Kompost-/Humusmischung',mineral_mix:'Mineralisches Substrat',rockwool:'Steinwolle',hydroponic:'Hydrokultur',custom:'Eigene Mischung'};
const containerNames={plastic:'Kunststofftopf',fabric:'Stofftopf',air_pruning:'Air-Pruning-Topf',self_watering:'Selbstbewässerung',high_tech:'Hightech-Growtopf',hydro_system:'Hydro-System',other:'Sonstiger Topf'};
function renderRoomPlantProfiles(){
 const holder=$('roomPlantProfiles');if(!holder)return;
 const room=(state.rooms||[]).find(r=>r.id===growJournal.roomId);
 text('journalRoomInfo',room?'Growbuch · '+room.name:'Raum auswählen');
 holder.innerHTML=growJournal.plants.length?growJournal.plants.map(p=>{
  const ready=!!(p.crop&&p.phase&&p.substrate_type&&p.substrate_components&&p.container_type&&p.nutrition_plan&&p.substrate_pre_fertilized);
  return '<div class="statusrow"><span><strong>'+esc(p.name)+'</strong> · '+esc(phaseNames[p.phase]||p.phase)+' · '+esc(substrateNames[p.substrate_type]||'Substrat fehlt')+
   ' · '+esc(containerNames[p.container_type]||'Topf fehlt')+'</span><button type="button" class="subtle" data-plant-edit="'+esc(p.id)+'">'+(ready?'Bearbeiten':'Profil vervollständigen')+'</button></div>';
 }).join(''):'<p class="desc">Noch keine Pflanze vorhanden. Lege zuerst eine Pflanze mit Phase, Substrat, Düngung und Topf an.</p>';
}
async function loadRoomPlants(){
 if(!growJournal.roomId)return;
 try{
  const result=await api('/api/v1/rooms/'+encodeURIComponent(growJournal.roomId)+'/plants');
  growJournal.plants=result.plants||[];
  renderRoomPlantProfiles();
 }catch(e){text('roomPlantProfiles','Pflanzen nicht verfügbar: '+e.message);}
}
const substratePresets={
 coco70:['coco_mix','Kokos 70 %, Perlit 30 %'],
 peat60:['peat_mix','Torf 60 %, Perlit 20 %, Vermiculit 20 %'],
 coco50:['coco_mix','Kokos 50 %, Perlit 17 %, Vermiculit 17 %, Wurmhumus 16 %'],
 cocopeat:['coco_mix','Kokos 60 %, Torf 30 %, Perlit 10 %'],
 soilcompost:['compost_mix','Torf 60 %, Perlit 30 %, Kompost 10 %'],
 living:['living_soil',''],
 rockwool:['rockwool','Steinwolle 100 %']
};
function useSubstratePreset(){
 const preset=substratePresets[$('plantMixPreset')?.value];
 if(!preset)return;
 $('plantSubstrate').value=preset[0];
 if(preset[1])$('plantComposition').value=preset[1];
 // Do not infer pre-fertilization from ingredients or overwrite the operator's feeding strategy.
}
function updatePlantCropInput(value=''){
 const select=$('plantCropSelect');
 const custom=$('plantCropOther');
 const hidden=$('plantCrop');
 const choices=[...select.options].map(o=>o.value).filter(v=>v&&v!=='__custom__');
 const known=choices.includes(value);
 select.value=known?value:value?'__custom__':'';
 const isCustom=select.value==='__custom__';
 $('plantCropOtherWrap').hidden=!isCustom;
 custom.required=isCustom;
 custom.value=isCustom?(value==='__custom__'?'':value):'';
 hidden.value=isCustom?custom.value:(select.value||'');
}
function syncPlantCropInput(){
 const select=$('plantCropSelect');
 const isCustom=select.value==='__custom__';
 $('plantCropOtherWrap').hidden=!isCustom;
 $('plantCropOther').required=isCustom;
 $('plantCrop').value=isCustom?$('plantCropOther').value.trim():select.value;
}
function editRoomPlant(id){
 const p=growJournal.plants.find(x=>x.id===id);if(!p)return;
 const fields={plantEditId:p.id,plantName:p.name,plantPhase:p.phase,plantSubstrate:p.substrate_type,
 plantComposition:p.substrate_components,plantPreFert:p.substrate_pre_fertilized,plantNutrition:p.nutrition_plan,
 plantContainer:p.container_type,plantVolume:p.container_volume_l};
 Object.entries(fields).forEach(([key,val])=>{if($(key))$(key).value=val??'';});
 updatePlantCropInput(p.crop||'');
 $('roomPlantForm')?.scrollIntoView({behavior:'smooth',block:'start'});
}
function resetRoomPlantForm(){
 $('roomPlantForm')?.reset();text('plantFormError','');
 $('plantEditId').value='';
 updatePlantCropInput('');
}
async function saveRoomPlant(e){
 e.preventDefault();if(!growJournal.roomId)return;
 syncPlantCropInput();
 const data={name:$('plantName').value.trim(),crop:$('plantCrop').value.trim(),phase:$('plantPhase').value,
  substrate_type:$('plantSubstrate').value,substrate_components:$('plantComposition').value.trim(),
  substrate_pre_fertilized:$('plantPreFert').value,nutrition_plan:$('plantNutrition').value,
  container_type:$('plantContainer').value,
  container_volume_l:$('plantVolume').value?Number($('plantVolume').value):null};
 const id=$('plantEditId').value;
 const old=growJournal.plants.find(p=>p.id===id);
 const payload={...old,...data};
 delete payload.id;delete payload.room_id;delete payload.created_at;delete payload.updated_at;
 try{
  if(!data.name||!data.crop||!data.substrate_type||!data.substrate_components||!data.substrate_pre_fertilized||
     !data.nutrition_plan||!data.container_type)throw Error('Pflanze, Phase, Substrat, Vordüngung, Düngekonzept und Topf sind Pflicht.');
  const path='/api/v1/rooms/'+encodeURIComponent(growJournal.roomId)+'/plants'+(id?'/'+encodeURIComponent(id):'');
  await journalRequest(id?'PUT':'POST',path,payload);
  resetRoomPlantForm();await loadRoomPlants();await loadJournal();await loadClimateOverview();
  notify('Pflanzenprofil gespeichert');
 }catch(err){text('plantFormError','Pflanze konnte nicht gespeichert werden: '+err.message);}
}
function openJournalForm(id=null){
 const row=growJournal.entries.find(x=>x.id===id);
 if(!growJournal.plants.some(p=>p.crop&&p.phase&&p.substrate_type&&p.substrate_components&&p.container_type&&p.nutrition_plan&&p.substrate_pre_fertilized)){notify('Zuerst Pflanzenprofil mit Phase, Substrat, Topf und Düngung vollständig ausfüllen.');return;}
 growJournal.editingId=row?.id||null;
 const form=$('journalForm');form.reset();
 $('journalCategory').value=row?.category||'observation';
 $('journalTitle').value=row?.title||'';
 $('journalText').value=row?.text||'';
 $('journalPhoto').disabled=!!row;
 const eligible=growJournal.plants.filter(p=>p.crop&&p.phase&&p.substrate_type&&p.substrate_components&&p.container_type&&p.nutrition_plan&&p.substrate_pre_fertilized);
 $('journalPlant').innerHTML='<option value="">Pflanze wählen</option>'+eligible.map(p=>'<option value="'+esc(p.id)+'">'+esc(p.name)+' · '+esc(p.phase)+'</option>').join('');
 $('journalPlant').value=row?.plant_id||'';
 text('journalDialogTitle',row?'Eintrag bearbeiten':'Neuer Growbucheintrag');
 text('journalError','');
 if(!growJournal.roomId){notify('Erst einen Raum auswählen');return;}
 $('journalDialog').showModal();
}
async function journalRequest(method,path,body){
 const opts={method,credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'}};
 if(body!==undefined)opts.body=JSON.stringify(body);
 const response=await fetch(path,opts);
 let data={};try{data=await response.json();}catch{}
 if(!response.ok)throw new Error(typeof data?.detail==='string'?data.detail:'HTTP '+response.status);
 return data;
}
async function saveJournal(event){
 event.preventDefault();
 if(!growJournal.roomId)return;
 const button=$('journalSave');button.disabled=true;
 text('journalError','');
 const payload={category:$('journalCategory').value,title:$('journalTitle').value.trim(),text:$('journalText').value.trim(),plant_id:$('journalPlant').value};
 try{
  if(!payload.title)throw Error('Bitte einen Titel eingeben.');
  if(!payload.plant_id)throw Error('Bitte zuerst eine Pflanze auswählen.');
  const photo=$('journalPhoto').files[0];
  if(photo&&!growJournal.editingId){
   if(!['image/jpeg','image/png','image/webp'].includes(photo.type))throw Error('Nur JPG, PNG oder WebP erlaubt.');
   if(photo.size>8*1024*1024)throw Error('Foto größer als 8 MiB.');
   const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(photo)});
   await api('/api/v1/grow-photos',{room_id:growJournal.roomId,plant_id:payload.plant_id,title:payload.title,note:payload.text,tags:[payload.category],image_data_url:dataUrl});
  }else if(growJournal.editingId){
   await journalRequest('PUT',journalPath()+'/journal/'+encodeURIComponent(growJournal.editingId),payload);
  }else{
   await api(journalPath()+'/journal',payload);
  }
  $('journalDialog').close();growJournal.editingId=null;
  await loadJournal();await loadRecentEvents();
  notify('Growbucheintrag gespeichert');
 }catch(e){text('journalError','Speichern fehlgeschlagen: '+e.message);}
 finally{button.disabled=false;}
}
async function deleteJournal(id){
 const row=growJournal.entries.find(x=>x.id===id);
 if(!row||!confirm('Diesen Growbucheintrag wirklich löschen?'))return;
 try{
  const path=row.photo_id?'/api/v1/grow-photos/'+encodeURIComponent(row.photo_id):journalPath()+'/journal/'+encodeURIComponent(id);
  await journalRequest('DELETE',path);
  await loadJournal();await loadRecentEvents();
  notify('Eintrag gelöscht');
 }catch(e){notify('Löschen fehlgeschlagen: '+e.message);}
}
async function loadRecentEvents(){
 const root=journalPath();if(!root)return;
 try{
  const result=await api(root+'/events?limit=7');
  const entries=result.events||[];
  $('recentEvents').innerHTML=entries.length?entries.map(x=>{
   const time=new Date(x.created_at||x.timestamp||'');
   const dateText=isNaN(time)?'—':time.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});
   const label=catLabels[x.type]||x.type||'Ereignis';
   const note=x.note||label;
   return '<div class="recent-event"><time>'+dateText+'</time><span>'+esc(note)+'</span></div>';
  }).join(''):'<p class="empty-text">Noch keine Grow-Ereignisse vorhanden.</p>';
 }catch(e){text('recentEvents','Verlauf derzeit nicht erreichbar.');}
}
document.addEventListener('click',e=>{
 const soilRefresh=e.target.closest('[data-soil-refresh]');if(soilRefresh){loadSoilUsb(true);return;}
 const soilInspect=e.target.closest('[data-soil-inspect]');if(soilInspect){soilCommand(soilInspect.dataset.soilInspect,'inspect',{});return;}
 const soilConnect=e.target.closest('[data-soil-connect]');if(soilConnect){soilCommand(soilConnect.dataset.soilConnect,'connection',{});return;}
 const soilFlash=e.target.closest('[data-soil-flash]');if(soilFlash){
  if(confirm('Firmware auf dem XIAO ESP32-C3 aktualisieren? Dies startet das USB-Flashen. Vorhandene Kalibrierung wird anschließend erneut geprüft. USB bis zum Abschluss nicht abziehen.'))soilCommand(soilFlash.dataset.soilFlash,'flash',{board:'seeed_xiao_esp32c3',confirmed:true});
  return;
 }
 const plantEdit=e.target.closest('[data-plant-edit]');if(plantEdit){editRoomPlant(plantEdit.dataset.plantEdit);return;}
 const create=e.target.closest('[data-create-room]');if(create){createGrowRoom();return;}
 const archive=e.target.closest('[data-room-delete]');if(archive){archiveGrowRoom(archive.dataset.roomDelete);return;}
 const restore=e.target.closest('[data-room-restore]');if(restore){restoreGrowRoom(restore.dataset.roomRestore);return;}
 const manage=e.target.closest('[data-room-manage]');if(manage){manageRoomDevices(manage.dataset.roomManage);return;}
 const roombook=e.target.closest('[data-room-journal]');if(roombook){growJournal.roomId=roombook.dataset.roomJournal;page('growbook');return;}
 const add=e.target.closest('[data-add-journal]');if(add){openJournalForm();return;}
 const tab=e.target.closest('[data-journal-tab]');if(tab){growJournal.tab=tab.dataset.journalTab;renderJournal();return;}
 const selected=e.target.closest('[data-journal-select]');if(selected){growJournal.selectedId=selected.dataset.journalSelect;renderJournal();return;}
 const edit=e.target.closest('[data-journal-edit]');if(edit){openJournalForm(edit.dataset.journalEdit);return;}
 const del=e.target.closest('[data-journal-delete]');if(del){deleteJournal(del.dataset.journalDelete);}
});
document.addEventListener('input',e=>{
 const form=e.target.closest('[data-soil-network], [data-soil-assign]');
 if(form)form.dataset.editing='true';
});
document.addEventListener('submit',async e=>{
 const network=e.target.closest('[data-soil-network]');
 if(network){
  e.preventDefault();const data=new FormData(network);const body={ssid:String(data.get('ssid')||''),password:String(data.get('password')||''),broker_host:String(data.get('broker_host')||'')};
  network.dataset.editing='false';network.reset();await soilCommand(network.dataset.soilNetwork,'network',body);return;
 }
 const assign=e.target.closest('[data-soil-assign]');
 if(assign){e.preventDefault();const data=new FormData(assign);assign.dataset.editing='false';await soilCommand(assign.dataset.soilAssign,'assign',{name:String(data.get('name')||''),room_id:String(data.get('room_id')||''),confirmed:true});}
});
document.addEventListener('change',e=>{if(e.target.matches('[data-room-device]'))roomDeviceChange(e.target);});
$('climateRoomSelect')?.addEventListener('change',loadClimateHistory);
$('climateTimeSelect')?.addEventListener('change',loadClimateHistory);
$('roomPlantForm')?.addEventListener('submit',saveRoomPlant);
$('plantFormReset')?.addEventListener('click',resetRoomPlantForm);
$('plantCropSelect')?.addEventListener('change',()=>{syncPlantCropInput();if($('plantCropSelect').value==='__custom__')$('plantCropOther').focus();});
$('plantCropOther')?.addEventListener('input',syncPlantCropInput);
$('plantMixPreset')?.addEventListener('change',useSubstratePreset);
$('journalForm')?.addEventListener('submit',saveJournal);
$('journalClose')?.addEventListener('click',()=>$('journalDialog').close());
$('journalCancel')?.addEventListener('click',()=>$('journalDialog').close());
$('roomPicker')?.addEventListener('change',async e=>{
 growJournal.roomId=e.target.value;
 const row=(state.rooms||[]).find(x=>x.id===growJournal.roomId);
 text('currentRoom',row?.name||'—');text('heroRoom',row?.name||'—');
 growJournal.selectedId=null;
 await Promise.all([loadJournal(),loadRecentEvents()]);
});
setInterval(()=>{if(!document.hidden&&growJournal.roomId)loadRecentEvents();},60000);
setInterval(()=>{if(!document.hidden)loadClimateOverview();},30000);
setInterval(()=>{if(!document.hidden&&state.page==='devices')loadSoilUsb();},6000);

renderControls();tick();page('home');refreshLive();loadRooms();loadSmart();loadHomekit();detectAccessMode();renderIcons();cloudRefresh();
cameraLoad();

})();
