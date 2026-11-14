/* Grow Central: indicative, stage-specific climate reference ranges.
   Only active when the user chooses a cannabis stage; no guessed plant identity.
   References: University of Saskatchewan cannabis seedling/vegetative/flowering guidance; phase-dependent orientation.
*/
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const root=$('stageClimate');if(!root)return;
const stages={
 germination:{label:'Keimung / Sämling',t:[21,27],h:[60,70]},
 seedling:{label:'Sämling / Steckling',t:[21,27],h:[60,70]},
 vegetative:{label:'Wachstum',t:[21,26],h:[50,60]},
 flowering:{label:'Blüte',t:[21,26],h:[45,55]},
 finish:{label:'Späte Blüte / Reife',t:[21,26],h:[35,45]}
};
const phases={germination:'germination',seedling:'seedling',vegetative:'vegetative',flowering:'flowering',flush:'finish',finish:'finish',harvest:'finish'};
const select=$('stageClimateSelect'),source=$('stageClimateSource'),items=$('stageClimateRows');
let planted=[],stage='',room='';
function node(tag,text,className){const el=document.createElement(tag);if(text!=null)el.textContent=text;if(className)el.className=className;return el}
function classify(value,min,max,tolerance,danger){
 if(!Number.isFinite(value))return 'unknown';
 if(value>=min&&value<=max)return 'good';
 const distance=value<min?min-value:value-max;
 return distance<=tolerance?'warning':'danger';
}
function build(label,current,min,max,unit,tolerance,danger,axisMin,axisMax){
 const row=node('div',undefined,'gc-range-item');
 const heading=node('div',undefined,'gc-range-title');
 heading.append(node('strong',label),node('span',Number.isFinite(current)?current.toLocaleString('de-DE',{maximumFractionDigits:1})+' '+unit:'Kein Messwert'));
 const span=axisMax-axisMin;
 const fraction=v=>Math.min(100,Math.max(0,(v-axisMin)/span*100));
 const track=node('div',undefined,'gc-range-track');
 // Each segment is derived from this phase's actual limits, not a fixed background gradient.
 const stops=[
  [axisMin,min-tolerance,'danger'],[min-tolerance,min,'warning'],
  [min,max,'good'],[max,max+tolerance,'warning'],[max+tolerance,axisMax,'danger']
 ];
 for(const [from,to,tone] of stops){
  const left=fraction(Math.max(axisMin,from)),right=fraction(Math.min(axisMax,to));
  if(right<=left)continue;
  const segment=node('span',undefined,'gc-range-segment '+tone);
  segment.style.left=left+'%';segment.style.width=(right-left)+'%';
  track.append(segment);
 }
 const pointer=node('span',undefined,'gc-range-pointer');
 if(Number.isFinite(current)){
  pointer.style.left=fraction(current)+'%';
  pointer.classList.add(classify(current,min,max,tolerance,danger));
 }else pointer.hidden=true;
 track.append(pointer);
 const labels=node('div',undefined,'gc-range-ticks');
 labels.append(node('span',axisMin.toLocaleString('de-DE')+' '+unit),node('span',min.toLocaleString('de-DE')+'–'+max.toLocaleString('de-DE')+' '+unit),node('span',axisMax.toLocaleString('de-DE')+' '+unit));
 const status=classify(current,min,max,tolerance,danger);
 const descriptions={good:'Im Richtbereich',warning:'Knapp außerhalb',danger:'Deutlich außerhalb',unknown:'Keine Daten'};
 const note=node('small','Orientierung: '+min+'–'+max+' '+unit+' · '+descriptions[status],'gc-range-'+status);
 row.append(heading,track,labels,note);
 return row;
}
function parseValue(id){const raw=$(id)?.textContent||'';const val=Number.parseFloat(raw.replace(',','.'));return Number.isFinite(val)?val:NaN}
function paint(){
 items.replaceChildren();
 if(!stage||!stages[stage]){items.append(node('p','Wähle die Kulturphase, um Klima-Richtbereiche anzuzeigen. Ohne Profil wird nichts als optimal bewertet.','desc'));return}
 const profile=stages[stage];
 const t=parseValue('tempValue'),h=parseValue('humidityValue');
 const temperatureMin=Math.max(0,Math.floor(Math.min(profile.t[0]-6,Number.isFinite(t)?t-2:profile.t[0]-6)));
 const temperatureMax=Math.min(45,Math.ceil(Math.max(profile.t[1]+6,Number.isFinite(t)?t+2:profile.t[1]+6)));
 const humidityMin=Math.max(0,Math.floor(Math.min(profile.h[0]-15,Number.isFinite(h)?h-5:profile.h[0]-15)/5)*5);
 const humidityMax=Math.min(100,Math.ceil(Math.max(profile.h[1]+15,Number.isFinite(h)?h+5:profile.h[1]+15)/5)*5);
 items.append(build('Temperatur',t,...profile.t,'°C',2,5,temperatureMin,temperatureMax));
 items.append(build('Luftfeuchte',h,...profile.h,'% rF',5,15,humidityMin,humidityMax));
}
async function loadRoomPlants(){
 const next=$('roomPicker')?.value||'';
 room=next;
 if(!next){planted=[];source.textContent='Kein Raum ausgewählt';paint();return}
 try{
  const r=await fetch('/api/v1/rooms/'+encodeURIComponent(next)+'/plants',{cache:'no-store'});
  if(!r.ok)throw Error('HTTP '+r.status);
  const d=await r.json();if(room!==next)return;
  planted=Array.isArray(d.plants)?d.plants:[];
  const cannabis=planted.filter(p=>/cannabis|hanf/i.test([p.strain,p.name].join(' ')));
  if(cannabis.length===1&&phases[cannabis[0].phase]){
   stage=phases[cannabis[0].phase];select.value=stage;
   source.textContent='Richtwert für '+cannabis[0].name+' · '+stages[stage].label;
  }else{
   stage='';select.value='';
   source.textContent=cannabis.length>1?'Mehrere Cannabis-Pflanzen · Phase manuell auswählen':planted.length?'Pflanzen erfasst · Cannabis-Phase manuell auswählen':'Noch keine Pflanzen erfasst · Vorschau nach Phase';
  }
 }catch(e){stage='';select.value='';source.textContent='Pflanzenprofil nicht abrufbar · manuelle Richtwertvorschau'}
 paint();
}
select.addEventListener('change',()=>{stage=select.value;source.textContent=stage?'Manuelle Richtwertvorschau · '+stages[stage].label:'Keine Phase ausgewählt';paint()});
$('roomPicker')?.addEventListener('change',loadRoomPlants);
$('stageClimateReload')?.addEventListener('click',loadRoomPlants);
const observer=new MutationObserver(paint);
for(const id of ['tempValue','humidityValue'])if($(id))observer.observe($(id),{childList:true,characterData:true,subtree:true});
loadRoomPlants();paint();
})();
