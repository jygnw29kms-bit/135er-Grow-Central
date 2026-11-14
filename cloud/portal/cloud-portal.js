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
 const panel=$('remoteDashboard');if(panel)panel.hidden=true;
}
function remoteTile(label,value){
 const item=document.createElement('div');item.className='device';
 const head=document.createElement('small');head.textContent=label;
 const number=document.createElement('b');number.textContent=value;
 item.append(head,number);return item;
}
function remoteRead(path){
 if(!remoteSocket||remoteSocket.readyState!==WebSocket.OPEN)return;
 remoteSocket.send(JSON.stringify({type:'read',request_id:String(++remoteRequest)+'-'+crypto.randomUUID(),path}));
}
function displayRemote(message){
 if(!message.ok){$('remoteState').textContent='Lesezugriff: '+(message.error||'Fehler');return}
 const info=message.data||{};
 if(message.path.includes('fan-status')){
  const d=info.fresh?info.latest:null;
  const target=$('remoteTiles');target.replaceChildren();
  target.append(remoteTile('Temperatur',d&&Number.isFinite(d.temperature_c)?d.temperature_c.toFixed(1)+' °C':'Keine Daten'));
  target.append(remoteTile('Luftfeuchte',d&&Number.isFinite(d.humidity_rh)?d.humidity_rh.toFixed(1)+' %':'Keine Daten'));
  target.append(remoteTile('Lüfterdrehzahl',d&&Number.isFinite(d.rpm)?d.rpm+' RPM':'Keine Daten'));
 }else if(message.path.includes('lamp-status')){
  const d=info.fresh?info.latest:null;
  $('remoteTiles').append(remoteTile('FC3000 Licht',d?(d.power_on?d.brightness_percent+' %':'Aus'):'Keine Daten'));
 }
 $('remoteState').textContent='Live-Lesekanal verbunden · '+new Date().toLocaleTimeString('de-DE');
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
    for(const path of ['/api/mars-hydro/ble/fast-fan-status','/api/mars-hydro/ble/fast-lamp-status']){
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