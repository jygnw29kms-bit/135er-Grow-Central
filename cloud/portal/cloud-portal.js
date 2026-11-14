'use strict';
const $=id=>document.getElementById(id);
let accessToken='';
async function listDevices(){
 const res=await fetch('/api/v2/account/devices',{headers:{Authorization:'Bearer '+accessToken},cache:'no-store'});
 if(!res.ok)throw Error('Geräteliste HTTP '+res.status);
 const data=await res.json(),target=$('devices');target.replaceChildren();
 const devices=(data.devices||[]).filter(d=>!d.revoked_at);
 $('summary').textContent=devices.length+' gekoppelte Installation(en)';
 for(const device of devices){
  const card=document.createElement('div'),name=document.createElement('b'),status=document.createElement('small');
  card.className='device';name.textContent=device.name||'Grow Central';
  status.textContent=device.online?'Gerätekanal verbunden · Fernsteuerung noch nicht freigegeben':'Konto gekoppelt · Gerätekanal offline';
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
  const data=await res.json();accessToken=data.access_token;$('password').value='';
  $('login').hidden=true;$('account').hidden=false;await listDevices();
 }catch(error){$('msg').textContent=error.message}
});
$('refresh').addEventListener('click',()=>listDevices().catch(error=>$('summary').textContent=error.message));
$('logout').addEventListener('click',()=>{remoteClose();accessToken='';$('account').hidden=true;$('login').hidden=false;$('msg').textContent='Abgemeldet.';});
// Authenticated read-only telemetry. Never sends power, fan or light commands.
let remoteSocket=null,remoteInterval=null,remoteRequest=0;
function remoteClose(){
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
  if(data.type==='auth_ok'){
   if(!data.device_online){$('remoteState').textContent='Grow-Pi ist offline';return}
   const poll=()=>{
    pendingRemote.clear();
    if(socket.readyState!==WebSocket.OPEN)return;
    for(const path of ['/api/mars-hydro/ble/fast-fan-status','/api/mars-hydro/ble/fast-lamp-status','/api/v1/rooms','/api/mars-history/summary','/api/cloud/status']){
     const id=crypto.randomUUID();pendingRemote.set(id,path);
     socket.send(JSON.stringify({type:'read',request_id:id,path}));
    }
   };
   poll();remoteInterval=setInterval(poll,15000);return;
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
 socket.addEventListener('close',()=>{if(remoteSocket===socket){$('remoteState').textContent='Cloud-Fernkanal unterbrochen';if(remoteInterval)clearInterval(remoteInterval);remoteInterval=null}});
 socket.addEventListener('error',()=>{$('remoteState').textContent='WebSocket-Verbindung fehlgeschlagen'});
}