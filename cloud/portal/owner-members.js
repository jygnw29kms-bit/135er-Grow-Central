/* Beta 1.0: One-room owner management. Server is authoritative for every action.
   No bearer access tokens, QR links, or session secrets are persisted in this view. */
(()=>{
 'use strict';
 const $=id=>document.getElementById(id);
 const root=$('gcMembers');if(!root)return;
 const cloud=location.pathname.includes('cloud-master');
 const room=()=>document.getElementById('roomPicker')?.value||'';
 const roleLabels={admin:'Administrator',grower:'Grower',observer:'Beobachter'};
 const message=(s)=>{$('gcMembersStatus').textContent=s;};
 let shownOnce=null,loading=false;
 const enc=encodeURIComponent;
 async function request(method,part,body){
  const id=room();
  if(!/^room_[A-Za-z0-9_-]{1,110}$/.test(id))throw Error('Kein gültiger Raum ausgewählt');
  const suffix=part?'/'+part:'';
  if(cloud){
   if(typeof window.gcCloudOwnerRequest!=='function')throw Error('Geschützter Cloud-Zugang nicht verfügbar');
   return window.gcCloudOwnerRequest(method,id,suffix,body);
  }
  const url='/api/v1/'+(part.startsWith('members')?
    'room-members/owner/'+enc(id)+'/members'+(part==='members'?'':'/'+enc(part.slice(8))):
    'room-sharing/'+enc(id)+'/invitations'+(part==='invitations'?'':'/'+enc(part.slice(12))));
  const options={method,credentials:'same-origin',cache:'no-store',headers:{'Accept':'application/json'}};
  if(body!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
  const res=await fetch(url,options);
  let payload={};try{payload=await res.json()}catch{}
  if(!res.ok)throw Error(typeof payload.detail==='string'?payload.detail:'HTTP '+res.status);
  return payload;
 }
 function node(tag,text){const el=document.createElement(tag);if(text!==undefined)el.textContent=String(text);return el;}
 function action(text,fn){const b=node('button',text);b.type='button';b.className='subtle';b.addEventListener('click',fn);return b;}
 function clearOnce(){
  shownOnce=null;
  $('gcInvitationOnce').replaceChildren();
 }
 function rowInvite(item){
  const box=node('div');box.className='gc-member-row';
  const info=node('span',(roleLabels[item.role]||item.role)+' · läuft ab '+new Date(item.expires_at*1000).toLocaleString('de-DE'));
  box.append(info,action('Einladung widerrufen',async()=>{
   if(!confirm('Diese noch nicht eingelöste Einladung wirklich widerrufen?'))return;
   try{await request('DELETE','invitations/'+enc(item.id));await refresh()}catch(e){message(e.message)}
  }));
  return box;
 }
 function rowMember(item){
  const id=item.id||item.account_id;
  const box=node('div');box.className='gc-member-row';
  const label=node('span',item.username||item.account_id||'Mitglied');box.append(label);
  const select=node('select');select.setAttribute('aria-label','Rolle von '+label.textContent);
  for(const [value,name] of Object.entries(roleLabels)){const opt=node('option',name);opt.value=value;select.append(opt)}
  select.value=item.role;
  select.addEventListener('change',async()=>{
   if(!confirm('Rolle für '+label.textContent+' ändern?')){select.value=item.role;return}
   try{await request('PATCH','members/'+enc(id),{role:select.value});await refresh()}catch(e){message(e.message);select.value=item.role}
  });
  box.append(select,action('Zugriff entziehen',async()=>{
   if(!confirm('Zugriff sofort widerrufen und aktive Sitzungen ungültig machen?'))return;
   try{await request('DELETE','members/'+enc(id));await refresh()}catch(e){message(e.message)}
  }));
  return box;
 }
 async function refresh(){
  if(loading)return;
  loading=true;clearOnce();message('Mitglieder und Einladungen laden …');
  try{
   const [inv,member]=await Promise.all([request('GET','invitations'),request('GET','members')]);
   $('gcInvitationList').replaceChildren();
   $('gcMemberList').replaceChildren();
   const invitations=inv.pending||inv.invitations||[];
   const members=member.members||[];
   if(!invitations.length)$('gcInvitationList').append(node('p','Keine offenen Einladungen'));
   for(const row of invitations)$('gcInvitationList').append(rowInvite(row));
   if(!members.length)$('gcMemberList').append(node('p','Keine weiteren Mitglieder'));
   for(const row of members)$('gcMemberList').append(rowMember(row));
   message('Besitzerverwaltung geladen · '+members.length+' Mitglieder · '+invitations.length+' offene Einladungen');
  }catch(e){message('Geschützter Zugriff nicht verfügbar: '+e.message)}
  finally{loading=false}
 }
 $('gcOwnerRefresh').addEventListener('click',refresh);
 $('gcCreateInvitation').addEventListener('click',async()=>{
  if(loading)return;
  const role=$('gcInviteRole').value;
  if(!Object.hasOwn(roleLabels,role))return;
  try{
   const expires=Number($('gcInviteTtl').value)||48;
   const result=await request('POST','invitations',{role,ttl_hours:expires,delivery_hint:'link'});
   const url=result.share_url_once;
   if(typeof url!=='string'||!url.startsWith(cloud?'https://':'http'))throw Error('Einladungsadresse fehlt');
   shownOnce=url;
   const box=$('gcInvitationOnce');box.replaceChildren();
   box.append(node('p','Einmaliger Einladungslink. Nur an die gewünschte Person weitergeben.'));
   const link=node('input');link.readOnly=true;link.value=url;link.setAttribute('aria-label','Einmaliger Einladungslink');box.append(link);
   box.append(action('Link kopieren',()=>navigator.clipboard.writeText(shownOnce).catch(()=>message('Kopieren nicht möglich'))));
   if(result.qr_svg_once){
    // SVG from trusted owner API only, inserted as an image (no HTML execution).
    const blob=new Blob([result.qr_svg_once],{type:'image/svg+xml'});
    const objectUrl=URL.createObjectURL(blob),img=node('img');img.alt='Einmaliger Einladungs-QR-Code';
    img.width=160;img.height=160;img.src=objectUrl;img.addEventListener('load',()=>URL.revokeObjectURL(objectUrl),{once:true});box.append(img);
   }
   message('Einladung erstellt. Der Link wird nach Neuladen nicht erneut angezeigt.');
  }catch(e){message('Einladung fehlgeschlagen: '+e.message)}
 });
 $('roomPicker')?.addEventListener('change',()=>{clearOnce();if(root.closest('.page.active'))refresh()});
 document.querySelectorAll('[data-page="members"]').forEach(b=>b.addEventListener('click',()=>{clearOnce();refresh()}));
 window.addEventListener('pagehide',clearOnce);
})();
