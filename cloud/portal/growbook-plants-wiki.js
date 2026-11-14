/* Grow Central Growbuch cultures: scoped plant records and original, sourced wiki. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const root=$('plantWikiExtension');
if(!root)return;
const api=async(path,options={})=>{
 const r=await fetch(path,{...options,headers:{'Content-Type':'application/json'},cache:'no-store'});
 const data=await r.json().catch(()=>({detail:'Keine Antwort'}));
 if(!r.ok)throw Error(data.detail||'HTTP '+r.status);
 return data;
};
function roomId(){return $('roomPicker')?.value||''}
const phaseNames={germination:'Keimung',seedling:'Sämling',vegetative:'Wachstum',flowering:'Blüte',flush:'Endphase',finish:'Reife',harvest:'Ernte',completed:'Abgeschlossen',other:'Sonstige'};
const typeNames={automatic:'Automatisch',feminized:'Feminisiert',mother:'Mutterpflanze',clone:'Steckling',other:'Sonstige'};
const cropNames={cannabis:'Cannabis / Hanf',tomato:'Tomate',basil:'Basilikum',pepper:'Paprika / Chili',herbs:'Kräuter',other:'Andere Kultur'};
let plants=[],edited=null;
function node(tag,text,className){
 const el=document.createElement(tag);
 if(text!==undefined)el.textContent=text;
 if(className)el.className=className;
 return el;
}
function render(){
 const list=$('plantCards');list.replaceChildren();
 if(!plants.length){list.append(node('p','Noch keine Pflanzen erfasst. Über „Pflanze anlegen“ kannst du die erste hinzufügen.','desc'));return}
 for(const p of plants){
  const card=node('article',undefined,'gc-plant-card');
  card.append(node('h4',p.name),node('p',[cropNames[p.crop]||p.crop||'Kultur nicht angegeben',p.strain||'Sorte offen',typeNames[p.plant_type]||'Sonstige',phaseNames[p.phase]||'Andere Phase'].join(' · '),'desc'));
  if(p.start_date)card.append(node('small','Start: '+p.start_date));
  if(p.notes)card.append(node('p',p.notes));
  const btn=node('button','Bearbeiten','primary-btn');btn.type='button';btn.addEventListener('click',()=>edit(p));card.append(btn);
  list.append(card);
 }
}
async function load(){
 const id=roomId();if(!id){$('plantCards').textContent='Bitte einen Raum auswählen.';return}
 try{
  const data=await api('/api/v1/rooms/'+encodeURIComponent(id)+'/plants');
  plants=Array.isArray(data.plants)?data.plants:[];render();
 }catch(e){$('plantCards').textContent='Pflanzen nicht erreichbar: '+e.message}
}
function edit(plant=null){
 edited=plant?.id||null;
 const dialog=$('plantDialog');
 $('plantDialogTitle').textContent=plant?'Pflanze bearbeiten':'Pflanze anlegen';
 $('plantName').value=plant?.name||'';
 $('plantStrain').value=plant?.strain||'';
 $('plantCrop').value=plant?.crop||(/cannabis|hanf|autoflower|indica|sativa/i.test([plant?.name,plant?.strain].join(' '))?'cannabis':'');
 $('plantType').value=plant?.plant_type||'other';
 $('plantPhase').value=plant?.phase||'vegetative';
 $('plantStartDate').value=plant?.start_date||'';
 $('plantNotes').value=plant?.notes||'';
 $('plantError').textContent='';
 dialog.showModal();
}
$('plantAdd').addEventListener('click',()=>edit());
$('plantCancel').addEventListener('click',()=>$('plantDialog').close());
$('plantForm').addEventListener('submit',async e=>{
 e.preventDefault();
 const id=roomId(),button=$('plantSave');
 if(!id)return;
 const payload={name:$('plantName').value.trim(),strain:$('plantStrain').value.trim(),crop:$('plantCrop').value,plant_type:$('plantType').value,
 phase:$('plantPhase').value,start_date:$('plantStartDate').value,notes:$('plantNotes').value};
 if(!payload.name){$('plantError').textContent='Name fehlt.';return}
 button.disabled=true;
 try{
  const path='/api/v1/rooms/'+encodeURIComponent(id)+'/plants'+(edited?'/'+encodeURIComponent(edited):'');
  await api(path,{method:edited?'PUT':'POST',body:JSON.stringify(payload)});
  $('plantDialog').close();
  await load();
  window.dispatchEvent(new CustomEvent('gc:plants-updated',{detail:{room_id:id}}));
 }catch(error){$('plantError').textContent=error.message}
 finally{button.disabled=false}
});
$('roomPicker')?.addEventListener('change',load);
$('plantRefresh')?.addEventListener('click',load);
const wiki=[
 {title:'Kultur & Botanik',body:'Cannabis sativa ist eine einjährige Kulturpflanze. Wuchsform, Entwicklungsdauer und Reaktion auf Licht unterscheiden sich stark je nach Genetik. Das Kulturprofil dokumentiert Art, Sorte, Herkunft und beobachtete Eigenschaften.'},
 {title:'Keimung & Sämling',body:'Während der Keimung entwickeln sich Keimwurzel und Spross. Bei Sämlingen stehen vorsichtige Bewässerung, Luftaustausch und die Beobachtung der Substratfeuchte im Vordergrund. Maßnahmen werden pflanzenbezogen im Growbuch protokolliert.'},
 {title:'Vegetative Phase',body:'In der Wachstumsphase entwickeln sich Blattfläche, Sprosse und Wurzeln. Photoperiodische Sorten werden üblicherweise bei längeren Tagen vegetativ gehalten. Das Wiki trennt Beleuchtungsdauer, gemessene Lichtstärke und Pflanzenreaktion.'},
 {title:'Blüte und Genetik',body:'Bei photoperiodischen Sorten wird der Übergang zur Blüte vor allem durch längere ununterbrochene Dunkelperioden ausgelöst. Autoflowering-Genetik ist weniger abhängig von diesem Tageslängensignal. Der Zeitpunkt ist sortenabhängig und nicht pauschal festzulegen.'},
 {title:'Klima, Bewässerung & Dokumentation',body:'Temperatur, relative Luftfeuchte, Licht, Wassergaben, Substrat und Auffälligkeiten sollten mit Zeitstempel erfasst werden. Ziel ist der Vergleich verschiedener Kulturdurchläufe anhand realer Messdaten, statt aus pauschalen Richtwerten Erfolge abzuleiten.'},
 {title:'Pflanzengesundheit',body:'Blattverfärbungen, Welke, Schädlingsspuren und untypische Wachstumsmuster werden zuerst beschrieben und fotografiert. Ursachen können überlappen: Wasserhaushalt, Nährstoffversorgung, Licht, Klima oder Schaderreger. Eine Diagnose erfolgt nicht allein anhand eines einzelnen Symptoms.'}
];
const sections=$('cannabisWikiSections');
for(const item of wiki){
 const el=node('details');const summary=node('summary',item.title),p=node('p',item.body);
 el.append(summary,p);sections.append(el);
}
load();
})();
