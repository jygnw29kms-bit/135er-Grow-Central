(()=>{
'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api=async(path,options={})=>{const r=await fetch(path,{cache:'no-store',credentials:'same-origin',...options});const type=r.headers.get('content-type')||'';const body=type.includes('json')?await r.json():await r.text();if(!r.ok)throw new Error(body?.detail||body||`HTTP ${r.status}`);return body};
let renderTimer=null;

function status(msg,error=false){const box=$('gcDoctorStatus');if(!box)return;box.textContent=msg;box.classList.toggle('gc-error',error)}

async function loadPlants(){
  const room=$('growlogRoom')?.value,select=$('gcDoctorPlant');
  if(!room||!select)return;
  select.innerHTML='<option value="">Pflanze wählen …</option>';
  try{
    const data=await api(`/api/v1/rooms/${encodeURIComponent(room)}/plants`);
    (data.plants||[]).forEach(p=>{const o=document.createElement('option');o.value=p.id;o.textContent=`${p.name}${p.phase?` · ${p.phase}`:''}`;select.append(o)});
  }catch(e){status(e.message,true)}
}

function renderFindings(result){
  const out=$('gcDoctorResults');if(!out)return;
  const findings=result.findings||[];
  out.innerHTML=`<p class="master-copy"><b>${esc(result.disclaimer||'Mögliche Ursachen, keine sichere Diagnose.')}</b></p>${findings.map(f=>`<article class="master-panel"><div class="master-panel-head"><h3>${esc(f.title||f.code)}</h3><span class="state-badge">${esc(f.confidence||'possible')}</span></div><p class="master-copy">${esc(f.reason||'')}</p>${(f.checks||[]).length?`<div class="gc-list"><div class="gc-list-row"><div><strong>Gegenprüfen</strong><small>${(f.checks||[]).map(esc).join(' · ')}</small></div></div></div>`:''}${(f.actions||[]).length?`<div class="gc-list"><div class="gc-list-row"><div><strong>Nächste Schritte</strong><small>${(f.actions||[]).map(esc).join(' · ')}</small></div></div></div>`:''}</article>`).join('')}`;
}

async function diagnose(ev){
  ev.preventDefault();
  const room=$('growlogRoom')?.value,plant=$('gcDoctorPlant')?.value;
  if(!room||!plant){status('Bitte Raum und Pflanze wählen.',true);return}
  const button=$('gcDoctorRun');button.disabled=true;status('Messwerte und Symptome werden ausgewertet …');
  try{
    const symptoms=String($('gcDoctorSymptoms').value||'').split(',').map(v=>v.trim()).filter(Boolean).slice(0,30);
    const result=await api(`/api/v1/rooms/${encodeURIComponent(room)}/plants/${encodeURIComponent(plant)}/diagnosis`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      symptoms,
      affected_zone:$('gcDoctorZone').value,
      medium:String($('gcDoctorMedium').value||'').trim(),
      note:String($('gcDoctorNote').value||'').trim(),
      save_event:true,
    })});
    renderFindings(result);
    const snap=result.sensor_snapshot||{};
    const bits=[];
    if(snap.temperature_c!=null)bits.push(`${Number(snap.temperature_c).toFixed(1)} °C`);
    if(snap.humidity_percent!=null)bits.push(`${Number(snap.humidity_percent).toFixed(0)} % rF`);
    if(snap.vpd_kpa!=null)bits.push(`${Number(snap.vpd_kpa).toFixed(2)} kPa VPD`);
    if(snap.soil_moisture_percent!=null)bits.push(`${Number(snap.soil_moisture_percent).toFixed(1)} % Boden`);
    status(`Auswertung gespeichert${bits.length?` · ${bits.join(' · ')}`:''}`);
    window.dispatchEvent(new CustomEvent('gc:refresh'));
  }catch(e){status(e.message,true)}finally{button.disabled=false}
}

function ensureUi(){
  const section=$('growlog'),form=$('growlogForm');if(!section||!form)return;
  if($('gcPlantDoctor'))return;
  const panel=document.createElement('article');panel.id='gcPlantDoctor';panel.className='master-panel';
  panel.innerHTML=`<div class="master-panel-head"><h3>Plant Doctor</h3><span class="state-badge">REGELBASIERT · LOKAL</span></div><p class="master-copy">Symptome werden mit Pflanzenphase und echten lokalen Sensorwerten kombiniert. Ergebnis sind mögliche Ursachen, keine sichere Diagnose.</p><form id="gcDoctorForm" class="gc-form"><label>Pflanze<select id="gcDoctorPlant" required><option value="">Pflanze wählen …</option></select></label><label>Betroffene Zone<select id="gcDoctorZone"><option value="unknown">Unbekannt</option><option value="lower">Untere Blätter</option><option value="middle">Mitte</option><option value="upper">Obere Blätter / Spitze</option><option value="whole">Ganze Pflanze</option></select></label><label>Medium<input id="gcDoctorMedium" maxlength="80" placeholder="z. B. Erde, Coco"></label><label>Symptome<input id="gcDoctorSymptoms" maxlength="500" placeholder="z. B. gelb, hängend"></label><label class="gc-span-2">Notiz<input id="gcDoctorNote" maxlength="1000" placeholder="Optionaler Kontext"></label><button class="master-primary" id="gcDoctorRun">Auswerten</button></form><div id="gcDoctorStatus" class="gc-status">Noch keine Auswertung.</div><div id="gcDoctorResults" class="gc-stack"></div>`;
  const photo=$('gcPhotoTools');(photo||form.closest('.master-panel'))?.after(panel);
  $('gcDoctorForm')?.addEventListener('submit',diagnose);
  $('growlogRoom')?.addEventListener('change',loadPlants);
  loadPlants();
}

const queue=()=>{clearTimeout(renderTimer);renderTimer=setTimeout(ensureUi,60)};
window.addEventListener('gc:view',e=>{if(e.detail?.id==='growlog')queue()});
window.addEventListener('gc:refresh',queue);
new MutationObserver(queue).observe(document.documentElement,{subtree:true,childList:true});
queue();
})();
