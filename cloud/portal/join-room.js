'use strict';
/* Cloud invitation onboarding. No tokens in URLs sent to the server, storage,
   analytics, logs or cross-origin requests. Cloud guest transport is scoped by
   the backend to one membership and deliberately separate from owner sockets. */
const $=id=>document.getElementById(id);
const fragment=new URLSearchParams(location.hash.slice(1));
let inviteToken=fragment.get('room-invite')||'';
let accessToken='',session=null,guestSocket=null,requests=new Map();
const status=(message,kind='')=>{const el=$('status');el.textContent=message;el.className=kind;};
function authenticatedHeaders(){return {'Authorization':'Bearer '+accessToken,'Content-Type':'application/json'};}
async function api(path,{method='GET',body=null,authorized=true}={}){
 const headers=authorized?authenticatedHeaders():{'Content-Type':'application/json'};
 const response=await fetch(path,{method,headers,body:body?JSON.stringify(body):undefined,cache:'no-store',credentials:'omit'});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw Error(data.detail&&typeof data.detail==='string'?data.detail:'HTTP '+response.status);
 return data;
}
function eligibleMembership(m){
 return m&&typeof m.device_id==='string'&&typeof m.room_id==='string'&&
 /^[A-Za-z0-9-]{8,64}$/.test(m.device_id)&&/^room_[A-Za-z0-9_-]{1,110}$/.test(m.room_id)&&
 ['admin','grower','observer'].includes(m.role);
}
async function resolveMembership(){
 if(inviteToken){
  if(inviteToken.length<30||inviteToken.length>200)throw Error('Einladungslink ungültig');
  const accepted=await api('/api/v2/collaboration/accept',{method:'POST',body:{invite_token:inviteToken}});
  // The token must be used only once, and does not remain in browser history.
  inviteToken='';history.replaceState(null,'',location.pathname);
  if(!eligibleMembership(accepted))throw Error('Raumfreigabe noch nicht verfügbar');
  return accepted;
 }
 const data=await api('/api/v2/collaboration/my-rooms');
 const membership=(data.memberships||[]).find(eligibleMembership);
 if(!membership)throw Error('Keine aktive Raumfreigabe vorhanden');
 return membership;
}
function appendEntries(element,entries,formatter,empty){
 element.replaceChildren();
 if(!Array.isArray(entries)||entries.length===0){
  const row=document.createElement('li');row.textContent=empty;element.append(row);return;
 }
 for(const entry of entries.slice(0,30)){
  const row=document.createElement('li');row.textContent=formatter(entry);element.append(row);
 }
}
function closeGuest(){
 if(guestSocket){guestSocket.onclose=null;guestSocket.close();guestSocket=null;}
 for(const value of requests.values()){clearTimeout(value.timer);value.reject(Error('Verbindung beendet'));}
 requests.clear();
}
async function connectGuest(membership){
 closeGuest();
 const wsUrl=new URL('/api/v2/collaboration/remote/connect',location.origin);
 wsUrl.protocol=location.protocol==='https:'?'wss:':'ws:';
 return new Promise((resolve,reject)=>{
  const ws=new WebSocket(wsUrl.href),timer=setTimeout(()=>{ws.close();reject(Error('Zeitüberschreitung Cloud-Raumverbindung'));},12000);
  let authenticated=false;
  ws.onopen=()=>ws.send(JSON.stringify({type:'auth',access_token:accessToken,
    device_id:membership.device_id,room_id:membership.room_id}));
  ws.onmessage=event=>{
   let data;
   try{data=JSON.parse(event.data)}catch(_){return}
   if(data.type==='auth_ok'){
    if(data.guest_scoped!==true||data.room_id!==membership.room_id){ws.close(4403);return;}
    authenticated=true;clearTimeout(timer);guestSocket=ws;resolve();return;
   }
   const request=requests.get(data.request_id);
   if(!request)return;
   requests.delete(data.request_id);clearTimeout(request.timer);
   if(data.ok===true&&data.type==='read_result')request.resolve(data.data);
   else request.reject(Error(typeof data.error==='string'?data.error:'Datenabfrage fehlgeschlagen'));
  };
  ws.onerror=()=>{if(!authenticated){clearTimeout(timer);reject(Error('Cloud-Raumverbindung fehlgeschlagen'));}};
  ws.onclose=()=>{
   clearTimeout(timer);
   if(!authenticated)reject(Error('Cloud-Raumsitzung abgelehnt'));
   else{guestSocket=null;for(const p of requests.values()){clearTimeout(p.timer);p.reject(Error('Raumverbindung unterbrochen'))};requests.clear();status('Raumverbindung unterbrochen. Bitte erneut anmelden.','error');}
  };
 });
}
function guestRead(path){
 if(!guestSocket||guestSocket.readyState!==WebSocket.OPEN)return Promise.reject(Error('Raum nicht verbunden'));
 const requestId=crypto.randomUUID().replaceAll('-','');
 return new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{requests.delete(requestId);reject(Error('Raumabfrage dauerte zu lange'));},12000);
  requests.set(requestId,{resolve,reject,timer});
  guestSocket.send(JSON.stringify({type:'read',request_id:requestId,path}));
 });
}
async function showRoom(){
 const room=session.room_id;
 $('membership').textContent='Raum '+room+' · Rolle '+session.role;
 $('roomPanel').hidden=false;$('accountPanel').hidden=true;
 await loadRoom();
}
async function loadRoom(){
 if(!session)return;
 const root='/api/v1/rooms/'+encodeURIComponent(session.room_id);
 try{
  const [plants,journal]=await Promise.all([guestRead(root+'/plants'),guestRead(root+'/journal')]);
  appendEntries($('plants'),plants.plants,x=>
   String(x.name||'Pflanze').slice(0,100)+' · '+String(x.phase||'').slice(0,40),'Keine Pflanzen');
  appendEntries($('journal'),journal.entries,x=>
   String(x.title||x.category||'Eintrag').slice(0,100)+' · '+String(x.text||'').slice(0,160),'Noch keine Einträge');
  status('Deine Raumdaten wurden aktualisiert.','success');
 }catch(error){status(error.message,'error')}
}
async function signIn(email,password,registration){
 status('Anmeldung und Raumfreigabe werden geprüft …');
 const response=await api('/api/v2/account/'+(registration?'register':'login'),
  {method:'POST',body:{email,password},authorized:false});
 if(typeof response.access_token!=='string'||response.access_token.length<20)throw Error('Anmeldung nicht bestätigt');
 accessToken=response.access_token;
 session=await resolveMembership();
 await connectGuest(session);
 await showRoom();
}
for(const [formId,emailId,passwordId,registration] of [
 ['loginForm','email','password',false],['registerForm','registerEmail','registerPassword',true]
]){
 $(formId).addEventListener('submit',async event=>{
  event.preventDefault();
  const button=$(formId).querySelector('button');button.disabled=true;
  try{await signIn($(emailId).value,$(passwordId).value,registration)}
  catch(error){status(error.message,'error');accessToken='';session=null;}
  finally{$(passwordId).value='';button.disabled=false;}
 });
}
$('loadRoom').addEventListener('click',()=>loadRoom());
$('logout').addEventListener('click',()=>{closeGuest();accessToken='';session=null;
 $('roomPanel').hidden=true;$('accountPanel').hidden=false;status('Abgemeldet.','success')});
if(!inviteToken)status('Melde dich an, um deine bereits freigegebenen Räume zu öffnen.');
if(inviteToken.length>200){inviteToken='';history.replaceState(null,'',location.pathname);status('Ungültiger Einladungslink.','error')}
