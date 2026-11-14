/* Grow Central: indicative, stage-specific climate reference ranges.
   Only active when the user chooses a cannabis stage; no guessed plant identity.
   References: Cannabis Workforce Initiative 2023; Conviron 2017.
*/
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const root=$('stageClimate');if(!root)return;
const stages={
 germination:{label:'Keimung / Sämling',t:[21,27],h:[65,80]},
 seedling:{label:'Sämling / Steckling',t:[21,27],h:[65,80]},
 vegetative:{label:'Wachstum',t:[23,28],h:[55,70]},
 flowering:{label:'Blüte',t:[21,27],h:[40,60]},
 finish:{label:'Späte Blüte / Reife',t:[20,26],h:[40,55]}
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
function build(label,current,min,max,unit,tolerance,danger,lo,hi){
 const row=node('div',undefined,'gc-range-item');
 const heading=node('div',undefined,'gc-range-title');
 heading.append(node('strong',label),node('span',Number.isFinite(current)?current.toLocaleString('de-DE',{maximumFractionDigits:1})+' '+unit:'Kein Messwert'));
 const track=node('div',undefined,'gc-range-track');
 const good=node('div',undefined,'gc-range-good');
 const left=(min-lo)/(hi-lo)*100,right=(max-lo)/(hi-lo)*100;
 good.style.left=left+'%';good.style.width=(right-left)+'%';
 const pointer=node('span',undefined,'gc-range-pointer');
 if(Number.isFinite(current)){pointer.style.left=Math.min(100,Math.max(0,(current-lo)/(hi-lo)*100))+'%';pointer.classList.add(classify(current,min,max,tolerance,danger))}
 else pointer.hidden=true;
 track.append(good,pointer);
 const status=classify(current,min,max,tolerance,danger);
 const descriptions={good:'Im Richtbereich',warning:'Knapp außerhalb',danger:'Deutlich außerhalb',unknown:'Keine Daten'};
 const note=node('small','Orientierung: '+min+'–'+max+' '+unit+' · '+descriptions[status],'gc-range-'+status);
 row.append(heading,track,note);return row;
}
function parseValue(id){const raw=$(id)?.textContent||'';const val=Number.parseFloat(raw.replace(',','.'));return Number.isFinite(val)?val:NaN}
function paint(){
 items.replaceChildren();
 if(!stage||!stages[stage]){items.append(node('p','Wähle die Kulturphase, um Klima-Richtbereiche anzuzeigen. Ohne Profil wird nichts als optimal bewertet.','desc'));return}
 const profile=stages[stage];
 items.append(build('Temperatur',parseValue('tempValue'),...profile.t,'°C',2,5,10,40));
 items.append(build('Luftfeuchte',parseValue('humidityValue'),...profile.h,'% rF',5,15,0,100));
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
