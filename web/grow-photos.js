(()=>{
'use strict';
const MAX_BYTES=8*1024*1024;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api=async(path,options={})=>{const r=await fetch(path,{cache:'no-store',credentials:'same-origin',...options});const type=r.headers.get('content-type')||'';const body=type.includes('json')?await r.json():await r.text();if(!r.ok)throw new Error(body?.detail||body||`HTTP ${r.status}`);return body};
let busy=false;

function readDataUrl(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result||''));r.onerror=()=>reject(new Error('Bild konnte nicht gelesen werden'));r.readAsDataURL(file)})}
function status(msg,error=false){const el=document.getElementById('gcPhotoStatus');if(el){el.textContent=msg;el.classList.toggle('gc-error',error)}}

async function loadPlants(){
  const room=document.getElementById('growlogRoom')?.value;
  const select=document.getElementById('gcPhotoPlant');
  if(!room||!select)return;
  select.innerHTML='<option value="">Raumfoto / keine Pflanze</option>';
  try{
    const data=await api(`/api/v1/rooms/${encodeURIComponent(room)}/plants`);
    (data.plants||[]).forEach(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=`${p.name}${p.phase?` · ${p.phase}`:''}`;select.append(o)});
  }catch(e){status(e.message,true)}
}

async function uploadFile(file){
  if(busy||!file)return;
  if(file.size>MAX_BYTES){status('Bild ist größer als 8 MiB.',true);return}
  if(!/^image\/(jpeg|png|webp)$/i.test(file.type)){status('Nur JPEG, PNG oder WebP.',true);return}
  const room=document.getElementById('growlogRoom')?.value;
  if(!room){status('Bitte zuerst einen Raum wählen.',true);return}
  busy=true;status('Foto wird lokal gespeichert …');
  try{
    const dataUrl=await readDataUrl(file);
    const tags=String(document.getElementById('gcPhotoTags')?.value||'').split(',').map(v=>v.trim()).filter(Boolean);
    const result=await api('/api/v1/grow-photos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      room_id:room,
      plant_id:document.getElementById('gcPhotoPlant')?.value||null,
      title:'Foto',
      note:String(document.getElementById('gcPhotoNote')?.value||'').trim(),
      tags,
      image_data_url:dataUrl,
    })});
    status(`Foto gespeichert${result.cycle_day?` · Tag ${result.cycle_day}`:''}${result.phase?` · ${result.phase}`:''}`);
    const input=document.getElementById('gcPhotoFile');if(input)input.value='';
    window.dispatchEvent(new CustomEvent('gc:refresh'));
  }catch(e){status(e.message,true)}finally{busy=false}
}

function ensureUi(){
  const section=document.getElementById('growlog');
  const body=section?.querySelector('.gc-live-body');
  const form=document.getElementById('growlogForm');
  const photoButton=section?.querySelector('.gc-quick-log[data-category="photo"]');
  if(!section||!body||!form||!photoButton)return;

  let box=document.getElementById('gcPhotoTools');
  if(!box){
    box=document.createElement('article');
    box.id='gcPhotoTools';box.className='master-panel';
    box.innerHTML=`<div class="master-panel-head"><h3>Foto-Tagebuch</h3><span class="state-badge">LOKAL</span></div><div class="gc-form"><label>Pflanze<select id="gcPhotoPlant"><option value="">Raumfoto / keine Pflanze</option></select></label><label>Tags<input id="gcPhotoTags" maxlength="240" placeholder="z. B. Blüte, oben, Kontrolle"></label><label class="gc-span-2">Notiz<input id="gcPhotoNote" maxlength="5000" placeholder="Optional"></label><label class="gc-span-2">Kamera / Bild<input id="gcPhotoFile" type="file" accept="image/jpeg,image/png,image/webp" capture="environment"></label></div><div id="gcPhotoStatus" class="gc-status">Fotos bleiben lokal auf Grow Central und erhalten den aktuellen Sensor-Snapshot.</div>`;
    form.closest('.master-panel')?.after(box);
    document.getElementById('gcPhotoFile')?.addEventListener('change',e=>uploadFile(e.target.files?.[0]));
    document.getElementById('growlogRoom')?.addEventListener('change',loadPlants);
    loadPlants();
  }

  if(photoButton.dataset.gcPhotoBound!=='1'){
    photoButton.dataset.gcPhotoBound='1';
    photoButton.addEventListener('click',ev=>{
      ev.preventDefault();ev.stopImmediatePropagation();
      document.getElementById('gcPhotoFile')?.click();
    },true);
  }

  const timeline=section.querySelector('.gc-timeline');
  if(timeline&&!timeline.dataset.gcPhotoEnhanced){
    timeline.dataset.gcPhotoEnhanced='1';
    section.querySelectorAll('.gc-timeline > div').forEach(row=>{
      const text=row.textContent||'';
      if(!/Foto/.test(text))return;
      row.classList.add('gc-photo-event');
    });
  }
}

let timer=null;
const queue=()=>{clearTimeout(timer);timer=setTimeout(ensureUi,40)};
window.addEventListener('gc:view',e=>{if(e.detail?.id==='growlog')queue()});
window.addEventListener('gc:refresh',queue);
new MutationObserver(queue).observe(document.documentElement,{subtree:true,childList:true});
queue();
})();
