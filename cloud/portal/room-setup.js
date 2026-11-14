/* Room + hardware assignment, cloud-safe and local-first. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const create=$('gcRoomCreateForm'),devices=$('gcRoomDeviceList');
if(!create||!devices)return;
const api=async(path,init={})=>{
 const resp=await fetch(path,{cache:'no-store',...init,headers:{'Content-Type':'application/json'}});
 const data=await resp.json().catch(()=>({detail:'Keine Antwort'}));
 if(!resp.ok)throw Error(typeof data.detail==='string'?data.detail:'HTTP '+resp.status);
 return data;
};
const el=(tag,text,cls)=>{
 const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n
};
let inFlight=false;
async function refresh(){
 const room=$('roomPicker')?.value;
 devices.replaceChildren();
 if(!room){devices.append(el('p','Bitte einen Raum auswählen.','desc'));return}
 try{
  const data=await api('/api/v1/rooms/'+encodeURIComponent(room)+'/devices');
  const rows=(data.devices||[]).filter(d=>['mars-hydro:fc3000','mars-hydro:df150m'].includes(d.id));
  if(!rows.length){devices.append(el('p','Keine kompatiblen Mars-Hydro-Geräte bekannt.','desc'));return}
  for(const dev of rows){
   const card=el('div',undefined,'gc-assignment-row');
   const detail=el('div');
   detail.append(el('strong',dev.name||dev.id));
   const assigned=dev.assigned?'Diesem Raum zugeordnet':dev.room_id?'Anderem Raum zugeordnet':'Noch keinem Raum zugeordnet';
   detail.append(el('small',assigned+' · '+(dev.connected?'Verbunden':'Offline')));
   const action=el('button',dev.assigned?'Zugeordnet':'Raum zuordnen','primary-btn');
   action.type='button';action.disabled=!!dev.assigned||inFlight;
   action.addEventListener('click',async()=>{
    if(inFlight)return;
    inFlight=true;action.disabled=true;
    $('gcRoomDevicesStatus').textContent='Gerätezuordnung wird gespeichert …';
    try{
     await api('/api/v1/rooms/'+encodeURIComponent(room)+'/devices',{method:'POST',body:JSON.stringify({device_id:dev.id})});
     $('gcRoomDevicesStatus').textContent='Zuordnung auf dem Grow-Pi gespeichert. Keine Geräteschaltung ausgelöst.';
     await refresh();
     // Existing summary can stay stale until its next native refresh; reload on deliberate selection.
    }catch(e){$('gcRoomDevicesStatus').textContent='Zuordnung nicht bestätigt: '+e.message}
    finally{inFlight=false}
   });
   card.append(detail,action);devices.append(card);
  }
 }catch(e){devices.append(el('p','Gerätekatalog nicht erreichbar: '+e.message,'desc'))}
}
create.addEventListener('submit',async event=>{
 event.preventDefault();if(inFlight)return;
 const name=$('gcRoomName').value.trim();
 if(!name)return;
 const button=create.querySelector('button[type="submit"]');
 inFlight=true;button.disabled=true;$('gcRoomCreateStatus').textContent='Raum wird angelegt …';
 try{
  const selectedDevices=[
   $('gcNewRoomLamp')?.checked?'mars-hydro:fc3000':null,
   $('gcNewRoomFan')?.checked?'mars-hydro:df150m':null
  ].filter(Boolean);
  const result=await api('/api/v1/rooms',{method:'POST',body:JSON.stringify({name,kind:$('gcRoomKind').value})});
  const failures=[];
  for(const device_id of selectedDevices){
   try{
    await api('/api/v1/rooms/'+encodeURIComponent(result.room_id)+'/devices',
      {method:'POST',body:JSON.stringify({device_id})});
   }catch(e){failures.push(device_id+': '+e.message)}
  }
  $('gcRoomCreateStatus').textContent=failures.length?
   'Raum und Growbuch erstellt. Gerätezuordnung teilweise offen: '+failures.join('; '):
   'Raum und Growbuch erstellt; '+selectedDevices.length+' Gerät(e) zugeordnet.';
  create.reset();
  const roomList=await api('/api/v1/rooms');
  const selector=$('roomPicker');
  if(selector){
   selector.replaceChildren();
   for(const room of roomList.rooms||[]){
    const opt=el('option',room.name);opt.value=room.id;selector.append(opt);
   }
   selector.value=result.room_id||roomList.rooms?.at(-1)?.id||'';
   selector.dispatchEvent(new Event('change',{bubbles:true}));
  }
  await refresh();
 }catch(e){$('gcRoomCreateStatus').textContent='Raum nicht bestätigt: '+e.message+'. Keine automatische Wiederholung.'}
 finally{button.disabled=false;inFlight=false}
});
$('roomPicker')?.addEventListener('change',refresh);
$('plantRefresh')?.addEventListener('click',()=>{setTimeout(refresh,150)});
setTimeout(refresh,500);
})();
