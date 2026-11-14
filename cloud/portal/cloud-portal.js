'use strict';
const $=id=>document.getElementById(id);
let accessToken='',refreshToken='';
let reconnectTimer=null,reconnectAttempts=0;
async function listDevices(){
 const res=await fetch('/api/v2/account/devices',{headers:{Authorization:'Bearer '+accessToken},cache:'no-store'});
 if(!res.ok)throw Error('Geräteliste HTTP '+res.status);
 const data=await res.json(),target=$('devices');target.replaceChildren();
 const devices=(data.devices||[]).filter(d=>!d.revoked_at);
 $('summary').textContent=devices.length+' gekoppelte Installation(en)';
 for(const device of devices){
  const card=document.createElement('div'),name=document.createElement('b'),status=document.createElement('small');
  card.className='device';name.textContent=device.name||'Grow Central';
  status.textContent=device.online?'Gerätekanal verbunden · Steuerung mit Bestätigung':'Konto gekoppelt · Gerätekanal offline';
  card.append(name,status);target.append(card);
 }
 if(!devices.length)target.textContent='Noch keine aktiven Geräte gekoppelt.';
 if(devices.length)remoteOpen(devices[0].id);else remoteClose();
}
$('form').addEventListener('submit',async event=>{
 event.preventDefault();$('msg').textContent='Anmeldung wird geprüft …';
 try{
  const res=await fetch('/api/v2/account/login',{method:'POST',headers:{'Content-Type':'application/json'},cache:'no-store',body:JSON.stringify({email:$('email').value,password:$('password').value})});
  if(!res.ok)throw Error('Anmeldung fehlgeschlagen (HTTP '+res.status+')');
  const data=await res.json();accessToken=data.access_token;refreshToken=data.refresh_token||'';reconnectAttempts=0;$('password').value='';
  $('login').hidden=true;$('account').hidden=false;await listDevices();
 }catch(error){$('msg').textContent=error.message}
});
$('refresh').addEventListener('click',()=>listDevices().catch(error=>$('summary').textContent=error.message));
$('logout').addEventListener('click',()=>{remoteClose();accessToken='';refreshToken='';$('account').hidden=true;$('login').hidden=false;$('msg').textContent='Abgemeldet.';});
// Authenticated read-only telemetry. Never sends power, fan or light commands.
let remoteSocket=null,remoteInterval=null,remoteRequest=0;
const masterPending=new Map();
let masterVisible=false;
function masterStatus(value){if($('masterStatus'))$('masterStatus').textContent=value}
function masterToggle(){
 masterVisible=!masterVisible;
 $('masterMount').hidden=!masterVisible;
 $('remoteDashboard').hidden=masterVisible;
 $('masterToggle').textContent=masterVisible?'Live-Dashboard anzeigen':'Final-Master-GUI öffnen';
 if(masterVisible){
  cameraStop();
  const iframe=$('masterFrame');
  if(iframe.getAttribute('src')!=='/cloud-master.html?v=20261114-final-2')iframe.src='/cloud-master.html?v=20261114-final-2';
  masterStatus('Final Master · Verschlüsselter Cloud-Zugang');
 }else{ $('masterFrame').src='about:blank';masterStatus('Cloud-Datenbrücke bereit');}
}
$('masterToggle')?.addEventListener('click',masterToggle);
function masterReply(id,status,data){
 const frame=$('masterFrame')?.contentWindow;
 if(frame)frame.postMessage({source:'gc-cloud-parent',id,status,data},location.origin);
}
function masterHandleResult(data){
 const pending=masterPending.get(data.request_id);
 if(!pending)return false;
 masterPending.delete(data.request_id);
 if(data.ok){
  if(data.type==='camera_result'||data.type==='photo_frame_result')masterReply(data.request_id,200,{image:data.image});
  else if(data.type==='control_result')masterReply(data.request_id,200,{device_report_confirmed:data.device_report_confirmed,kind:data.kind});
  else if(data.type==='photo_result')masterReply(data.request_id,200,{photo_id:data.photo_id,ok:true});
  else masterReply(data.request_id,200,data.data||{ok:true,entry_id:data.entry_id});
 }else masterReply(data.request_id,503,{detail:data.error||'Keine Gerätebestätigung'});
 return true;
}
window.addEventListener('message',event=>{
 if(event.origin!==location.origin||event.source!==$('masterFrame')?.contentWindow)return;
 const msg=event.data;
 if(!msg||msg.source!=='gc-cloud-master'||typeof msg.id!=='string'||msg.id.length>64)return;
 if(!accessToken||!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN){
  masterReply(msg.id,503,{detail:'Cloud-Gerätekanal nicht erreichbar'});return
 }
 if(msg.kind==='photo'&&typeof msg.photo_id==='string'&&/^photo_[a-zA-Z0-9_-]{1,100}$/.test(msg.photo_id)){
  masterPending.set(msg.id,true);
  remoteSocket.send(JSON.stringify({type:'photo_frame',request_id:msg.id,photo_id:msg.photo_id}));return;
 }
 if(msg.kind==='camera'){
  masterPending.set(msg.id,true);
  remoteSocket.send(JSON.stringify({type:'camera_frame',request_id:msg.id}));return;
 }
 if(msg.kind!=='fetch'||typeof msg.path!=='string'||!msg.path.startsWith('/api/')){
  masterReply(msg.id,400,{detail:'Ungültiger API-Aufruf'});return;
 }
 const method=msg.method||'GET';
 if(method==='GET'){
  masterPending.set(msg.id,true);
  remoteSocket.send(JSON.stringify({type:'read',request_id:msg.id,path:msg.path}));return;
 }
 let payload=msg.body;
 if(typeof payload!=='object'||payload===null){masterReply(msg.id,400,{detail:'Ungültige Eingabe'});return}
 if(method==='POST'&&['/api/mars-hydro/ble/fast-lamp-control','/api/mars-hydro/ble/fast-fan-control'].includes(msg.path)){
  const kind=msg.path.includes('lamp')?'lamp':'fan';
  const action=payload.action,value=payload.value;
  if(!['power',kind==='lamp'?'brightness':'speed'].includes(action)||!Number.isInteger(value)||!payload.confirm_physical_change){
   masterReply(msg.id,400,{detail:'Ungültiger Gerätebefehl'});return;
  }
  if(!window.confirm('Grow Central Cloud: '+kind+' · '+action+' '+value+' wirklich ausführen?\\nDas physische Gerät wird verändert.')){
   masterReply(msg.id,409,{detail:'Nicht bestätigt'});return;
  }
  masterPending.set(msg.id,true);
  remoteSocket.send(JSON.stringify({type:'control',request_id:msg.id,kind,action,value,confirm_physical_change:true}));return;
 }
 if(method==='POST'&&msg.path.startsWith('/api/v1/rooms/')&&msg.path.endsWith('/journal')){
  if(!window.confirm('Neuen Growbucheintrag auf dem Pi speichern?')){masterReply(msg.id,409,{detail:'Nicht bestätigt'});return}
  const room_id=msg.path.split('/')[4];
  masterPending.set(msg.id,true);
  remoteSocket.send(JSON.stringify({type:'journal_create',request_id:msg.id,room_id,
    title:payload.title,text:payload.text,category:payload.category,confirm_write:true}));return;
 }
 if(method==='POST'&&msg.path==='/api/v1/grow-photos'){
  if(typeof payload.room_id!=='string'||typeof payload.image_data_url!=='string'
     ||!payload.image_data_url.startsWith('data:image/jpeg;base64,')
     ||payload.image_data_url.length>180000){
   masterReply(msg.id,413,{detail:'Foto zu groß oder falsches Format'});return;
  }
  if(!window.confirm('Dieses Foto im Growbuch des Pi speichern?')){
   masterReply(msg.id,409,{detail:'Nicht bestätigt'});return;
  }
  masterPending.set(msg.id,true);
  remoteSocket.send(JSON.stringify({type:'photo_create',request_id:msg.id,
   room_id:payload.room_id,title:payload.title||'Foto',note:payload.note||'',
   tags:Array.isArray(payload.tags)?payload.tags:[],image_data_url:payload.image_data_url,
   confirm_write:true}));return;
 }
 masterReply(msg.id,403,{detail:'Diese Funktion ist im Cloudmodus noch nicht freigegeben'});
});

let cameraTimer=null,cameraActive=false,cameraPending=false;
function cameraStop(){
 cameraActive=false;cameraPending=false;
 if(cameraTimer){clearInterval(cameraTimer);cameraTimer=null}
 const img=$('remoteCameraImage');if(img){img.removeAttribute('src');img.hidden=true}
 if($('cameraStart'))$('cameraStart').hidden=false;
 if($('cameraStop'))$('cameraStop').hidden=true;
 if($('cameraStatus'))$('cameraStatus').textContent='Kameravorschau beendet.';
}
function cameraPoll(){
 if(!cameraActive||cameraPending||!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN)return;
 cameraPending=true;
 remoteSocket.send(JSON.stringify({type:'camera_frame',request_id:crypto.randomUUID()}));
}
function cameraStart(){
 if(!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN){
  $('cameraStatus').textContent='Gerätekanal noch nicht verbunden.';return
 }
 cameraActive=true;$('cameraStart').hidden=true;$('cameraStop').hidden=false;
 $('cameraStatus').textContent='Lade erstes Kamerabild …';
 cameraPoll();cameraTimer=setInterval(cameraPoll,2500);
}
$('cameraStart')?.addEventListener('click',cameraStart);
$('cameraStop')?.addEventListener('click',cameraStop);
async function renewAccess(){
 if(!refreshToken)return false;
 try{
  const response=await fetch('/api/v2/account/refresh',{method:'POST',cache:'no-store',
   headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh_token:refreshToken})});
  if(!response.ok)return false;
  const values=await response.json();
  if(!values.access_token||!values.refresh_token)return false;
  accessToken=values.access_token;refreshToken=values.refresh_token;return true;
 }catch{return false}
}
function scheduleReconnect(deviceId,code=0){
 if(!accessToken||!deviceId||reconnectTimer)return;
 const delay=Math.min(30000,2000*Math.pow(2,Math.min(reconnectAttempts++,4)));
 masterStatus('Cloud-Verbindung unterbrochen · neuer Verbindungsversuch läuft');
 reconnectTimer=setTimeout(async()=>{
  reconnectTimer=null;
  if(!accessToken)return;
  if(code===4401){
   const renewed=await renewAccess();
   if(!renewed){masterStatus('Cloud-Sitzung abgelaufen · bitte neu anmelden');return}
  }
  remoteOpen(deviceId);
 },delay);
}
function remoteClose(){
 if(reconnectTimer){clearTimeout(reconnectTimer);reconnectTimer=null}
 for(const id of masterPending.keys())masterReply(id,503,{detail:'Verbindung geschlossen'});
 masterPending.clear();
 if($('masterFrame'))$('masterFrame').src='about:blank';
 if($('masterMount'))$('masterMount').hidden=true;
 masterVisible=false;
 if($('masterToggle'))$('masterToggle').textContent='Final-Master-GUI öffnen';
 selectedRoomId=null;
 if(journalPending){clearTimeout(journalPending.timeout);journalPending=null;}
 if($('journalSubmit'))$('journalSubmit').disabled=false;

 for(const [id,item] of pendingControl){clearTimeout(item.timeout);controlStatus(item.kind,'Verbindung beendet, Ergebnis unbestimmt.')}
 pendingControl.clear();busyControl.lamp=false;busyControl.fan=false;controlButtons();
 cameraStop();
 if(remoteInterval){clearInterval(remoteInterval);remoteInterval=null}
 if(remoteSocket){remoteSocket.close();remoteSocket=null}
 pendingRemote.clear()
 if($('remoteTiles'))$('remoteTiles').replaceChildren();
 const panel=$('remoteDashboard');if(panel)panel.hidden=true;
}
function remoteTile(label,value){
 const item=document.createElement('div');item.className='gc-metric';
 const head=document.createElement('small');head.textContent=label;
 const number=document.createElement('b');number.textContent=value;
 item.append(head,number);return item;
}
const latestRemote={fan:null,lamp:null};
let selectedRoomId=null,journalPending=null;
function requestPath(path){
 if(!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN)return;
 const id=crypto.randomUUID();pendingRemote.set(id,path);
 remoteSocket.send(JSON.stringify({type:'read',request_id:id,path}));
}
function requestJournal(){
 if(!selectedRoomId)return;
 const base='/api/v1/rooms/'+selectedRoomId;
 requestPath(base+'/journal');requestPath(base+'/plants');requestPath(base+'/events?limit=7');
}
function renderJournal(data){
 const target=$('journalDisplay');target.replaceChildren();
 const rows=Array.isArray(data.entries)?data.entries:[];
 if(!rows.length){target.textContent='Noch keine Growbucheinträge vorhanden.';return}
 for(const entry of rows.slice(0,12)){
  const item=document.createElement('div');item.className='gc-journal-item';
  const title=document.createElement('strong');title.textContent=entry.title||'Eintrag';
  const date=document.createElement('small');const when=new Date(entry.created_at);
  date.textContent=(entry.category||'Notiz')+' · '+(Number.isFinite(when.getTime())?when.toLocaleString('de-DE'):'');
  const body=document.createElement('p');body.textContent=entry.text||'';
  item.append(title,date,body);target.append(item);
 }
}
function submitJournal(event){
 event.preventDefault();
 if(!selectedRoomId||journalPending){$('journalStatus').textContent='Bitte einen verbundenen Raum auswählen.';return}
 if(!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN){$('journalStatus').textContent='Cloud-Verbindung unterbrochen.';return}
 const title=$('journalTitle').value.trim(),note=$('journalText').value,category=$('journalCategory').value;
 if(!title||title.length>120||note.length>5000)return;
 const id=crypto.randomUUID();
 $('journalSubmit').disabled=true;$('journalStatus').textContent='Speichere auf dem Grow-Pi …';
 const timeout=setTimeout(()=>{
  if(journalPending?.id!==id)return;
  journalPending=null;$('journalSubmit').disabled=false;
  $('journalStatus').textContent='Speicherbestätigung fehlt. Bitte Growbuch prüfen, nicht blind erneut senden.';
 },16000);
 journalPending={id,timeout};
 remoteSocket.send(JSON.stringify({type:'journal_create',request_id:id,room_id:selectedRoomId,title,text:note,category,confirm_write:true}));
}
$('journalForm')?.addEventListener('submit',submitJournal);
function journalResult(data){
 if(journalPending?.id!==data.request_id)return;
 clearTimeout(journalPending.timeout);journalPending=null;$('journalSubmit').disabled=false;
 if(data.ok){$('journalForm').reset();$('journalStatus').textContent='Auf dem Grow-Pi gespeichert.';requestJournal()}
 else{$('journalStatus').textContent='Speichern nicht bestätigt ('+(data.error||'Fehler')+'). Kein automatischer Wiederholungsversuch.'}
}

const pendingControl=new Map();
const busyControl={lamp:false,fan:false};
function controlButtons(){
 for(const kind of ['lamp','fan']){
  const latest=latestRemote[kind];
  for(const btn of document.querySelectorAll('[data-control-kind="'+kind+'"]')){
   const active=!!latest;
   btn.disabled=!active||busyControl[kind]||(btn.dataset.controlAction!=='power'&&!latest.power_on);
  }
 }
}
function controlStatus(kind,message){
 const p=$(kind+'ControlStatus');if(p)p.textContent=message;
}
function remoteControl(kind,action){
 if(!['lamp','fan'].includes(kind)||!['power','brightness','speed'].includes(action)||busyControl[kind])return;
 if(kind==='lamp'&&action==='speed'||kind==='fan'&&action==='brightness')return;
 const latest=latestRemote[kind];
 if(!latest||!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN)return;
 const value=action==='power'?(latest.power_on?0:1):Number($(kind+'Slider').value);
 if(!Number.isInteger(value))return;
 if(action!=='power'&&!latest.power_on){controlStatus(kind,'Das Gerät ist ausgeschaltet.');return}
 const model=kind==='lamp'?'Mars Hydro FC3000':'Mars Hydro DF150-M';
 const label=action==='power'?(value?'einschalten':'ausschalten'):('auf '+value+' % stellen');
 if(!window.confirm(model+' wirklich '+label+'?\\nDer physische Gerätezustand wird verändert.'))return;
 const request_id=crypto.randomUUID();
 busyControl[kind]=true;controlButtons();
 controlStatus(kind,'Befehl gesendet, warte auf echte Gerätebestätigung …');
 const timeout=setTimeout(()=>{
  if(!pendingControl.has(request_id))return;
  pendingControl.delete(request_id);busyControl[kind]=false;controlButtons();
  controlStatus(kind,'Keine eindeutige Bestätigung. NICHT erneut automatisch gesendet.');
 },30000);
 pendingControl.set(request_id,{kind,timeout});
 remoteSocket.send(JSON.stringify({type:'control',request_id,kind,action,value,confirm_physical_change:true}));
}
document.addEventListener('click',e=>{
 const btn=e.target.closest('[data-control-kind][data-control-action]');
 if(btn)remoteControl(btn.dataset.controlKind,btn.dataset.controlAction);
});
for(const kind of ['lamp','fan']){
 $(kind+'Slider')?.addEventListener('input',e=>{$(kind+'SliderLabel').textContent=e.target.value+' %'});
}
function controlResult(data){
 const entry=pendingControl.get(data.request_id);if(!entry)return;
 pendingControl.delete(data.request_id);clearTimeout(entry.timeout);
 busyControl[entry.kind]=false;controlButtons();
 if(data.ok&&data.device_report_confirmed===true){
  controlStatus(entry.kind,'Vom Controller bestätigt · '+new Date().toLocaleTimeString('de-DE'));
  const path=entry.kind==='lamp'?'/api/mars-hydro/ble/fast-lamp-status':'/api/mars-hydro/ble/fast-fan-status';
  if(remoteSocket?.readyState===WebSocket.OPEN){
   const id=crypto.randomUUID();pendingRemote.set(id,path);
   remoteSocket.send(JSON.stringify({type:'read',request_id:id,path}));
  }
 }else{
  controlStatus(entry.kind,'Gerätebestätigung fehlt ('+(data.error||'unbekannter Fehler')+'). Kein automatischer Wiederholungsversuch.');
 }
}

function metric(value,unit='',precision=0){
 return Number.isFinite(value)?Number(value).toLocaleString('de-DE',{minimumFractionDigits:precision,maximumFractionDigits:precision})+unit:'—';
}
function textRow(label,value){
 const row=document.createElement('div');row.className='gc-system-row';
 const a=document.createElement('span');a.textContent=label;
 const b=document.createElement('strong');b.textContent=value;
 row.append(a,b);return row;
}
function renderTelemetry(){
 const f=latestRemote.fan,l=latestRemote.lamp;
 controlButtons();
 $('remoteTiles').replaceChildren(
  remoteTile('Temperatur',metric(f?.temperature_c,' °C',1)),
  remoteTile('Luftfeuchte',metric(f?.humidity_rh,' % rF',1)),
  remoteTile('Lüfterdrehzahl',metric(f?.rpm,' RPM')),
  remoteTile('FC3000 Licht',l?(l.power_on?metric(l.brightness_percent,' %'):'Aus'):'—')
 );
 $('lampDisplay').replaceChildren(
  textRow('Gerätestatus',l?(l.power_on?'Eingeschaltet':'Ausgeschaltet'):'Keine BLE-Werte'),
  textRow('Helligkeit',l?metric(l.brightness_percent,' %'):'—')
 );
 $('fanDisplay').replaceChildren(
  textRow('Gerätestatus',f?(f.power_on?'Eingeschaltet':'Ausgeschaltet'):'Keine BLE-Werte'),
  textRow('Sollstufe',f?metric(f.setpoint_percent,' %'):'—'),
  textRow('Ist-Drehzahl',metric(f?.rpm,' RPM'))
 );
}
function renderRooms(data){
 const target=$('roomsDisplay');target.replaceChildren();
 const rooms=Array.isArray(data.rooms)?data.rooms:[];
 if(!rooms.length){target.textContent='Noch keine Räume vorhanden';return}
 for(const room of rooms.slice(0,12))target.append(textRow(room.name||'Raum',String(room.plant_count??0)+' Pflanzen'));
 selectedRoomId=rooms[0]?.id||null;requestJournal();
}
function renderHistory(data){
 const target=$('historyDisplay');target.replaceChildren();
 const rows=Array.isArray(data.latest)?data.latest:[];
 if(!rows.length){target.textContent='Noch keine Messhistorie vorhanden.';return}
 for(const entry of rows.slice(0,7)){
  const el=document.createElement('div');el.className='gc-history-row';
  const name=document.createElement('span');name.textContent=entry.device==='fan'?'DF150-M':entry.device==='lamp'?'FC3000':'Messung';
  const detail=document.createElement('span');
  detail.textContent=entry.device==='fan'?[metric(entry.temperature_c,' °C',1),metric(entry.humidity_rh,' %',1)].join(' · '):entry.power_on?'Licht Ein':'Licht Aus';
  const stamp=document.createElement('time');const dt=new Date(entry.recorded_at);
  stamp.textContent=Number.isFinite(dt.getTime())?dt.toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}):'—';
  el.append(name,detail,stamp);target.append(el);
 }
}
function displayRemote(message){
 if(!message.ok){$('remoteState').textContent='Lesezugriff: '+(message.error||'Fehler');return}
 const info=message.data||{};
 if(typeof message.path==='string'&&message.path.startsWith('/api/v1/rooms/')){
  if(message.path.endsWith('/journal')){renderJournal(info);return}
  if(message.path.endsWith('/plants')||message.path.endsWith('/events?limit=7'))return;
 }
 switch(message.path){
 case '/api/mars-hydro/ble/fast-fan-status':
  latestRemote.fan=info.fresh?info.latest:null;renderTelemetry();break;
 case '/api/mars-hydro/ble/fast-lamp-status':
  latestRemote.lamp=info.fresh?info.latest:null;renderTelemetry();break;
 case '/api/v1/rooms':renderRooms(info);break;
 case '/api/mars-history/summary':renderHistory(info);break;
 case '/api/cloud/status':
  $('systemDisplay').replaceChildren(
   textRow('Cloud-Kopplung',info.pairing?.status==='paired'?'Gekoppelt':'Prüfe …'),
   textRow('Cloud-Steuerkanal','Verschlüsselt'),
   textRow('Fernschalten','Deaktiviert')
  );break;
 }
 $('remoteState').textContent='LIVE · '+new Date().toLocaleTimeString('de-DE');
}
const pendingRemote=new Map();
function remoteOpen(deviceId){
 remoteClose();
 if(!deviceId||!accessToken)return;
 const panel=$('remoteDashboard');panel.hidden=false;
 $('remoteState').textContent='Authentifiziere Gerätekanal …';
 const socket=new WebSocket('wss://'+location.host+'/api/v2/remote/connect');
 remoteSocket=socket;
 socket.addEventListener('open',()=>{
  socket.send(JSON.stringify({type:'auth',access_token:accessToken,device_id:deviceId}));
 });
 socket.addEventListener('message',event=>{
  let data;try{data=JSON.parse(event.data)}catch{return}
  if(['read_result','control_result','journal_result','camera_result','photo_result','photo_frame_result'].includes(data.type)&&masterHandleResult(data))return;
  if(data.type==='journal_result'){journalResult(data);return}
  if(data.type==='control_result'){controlResult(data);return}
  if(data.type==='camera_result'){
   cameraPending=false;
   if(!cameraActive)return;
   if(data.ok&&typeof data.image==='string'&&data.image.startsWith('data:image/jpeg;base64,')&&data.image.length<220000){
    const img=$('remoteCameraImage');
    img.src=data.image;img.hidden=false;
    $('cameraStatus').textContent='Bild aktualisiert · '+new Date().toLocaleTimeString('de-DE');
   }else{$('cameraStatus').textContent='Kamera derzeit nicht verfügbar: '+(data.error||'Keine Bilddaten')}
   return;
  }
  if(data.type==='auth_ok'){
   if(!data.device_online){$('remoteState').textContent='Grow-Pi ist offline';socket.close();return}
   reconnectAttempts=0;
   const poll=()=>{
    pendingRemote.clear();
    if(socket.readyState!==WebSocket.OPEN)return;
    for(const path of ['/api/mars-hydro/ble/fast-fan-status','/api/mars-hydro/ble/fast-lamp-status','/api/v1/rooms','/api/mars-history/summary','/api/cloud/status']){
     const id=crypto.randomUUID();pendingRemote.set(id,path);
     socket.send(JSON.stringify({type:'read',request_id:id,path}));
    }
   };
   poll();remoteInterval=setInterval(poll,15000);if(!masterVisible)masterToggle();return;
  }
  if(data.type==='read_result'){
   const path=pendingRemote.get(data.request_id);
   if(!path||data.path&&data.path!==path)return;
   pendingRemote.delete(data.request_id);
   displayRemote({...data,path});
  }else if(data.type==='error'&&data.error==='device_offline'){
   $('remoteState').textContent='Grow-Pi-Gerätekanal offline';
  }
 });
 socket.addEventListener('close',event=>{if(remoteSocket===socket){masterStatus('Verbindung unterbrochen · Daten werden nicht aktualisiert');cameraStop();$('remoteState').textContent='Cloud-Fernkanal unterbrochen';if(remoteInterval)clearInterval(remoteInterval);remoteInterval=null;scheduleReconnect(deviceId,event.code)}});
 socket.addEventListener('error',()=>{$('remoteState').textContent='WebSocket-Verbindung fehlgeschlagen'});
}