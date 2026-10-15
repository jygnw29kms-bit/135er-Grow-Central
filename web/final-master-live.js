(()=>{
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api=async path=>{const r=await fetch(path,{cache:'no-store',credentials:'same-origin'});if(!r.ok)throw new Error(`${r.status} ${r.statusText}`);return r.json()};
  const num=(v,d=0)=>v!=null&&Number.isFinite(Number(v))?Number(v).toFixed(d):'?';
  const phaseLabels={germination:'Keimung',vegetative:'Vegetativ',flowering:'Bl?te',flush:'Sp?lung',harvest:'Ernte',other:'Sonstiges'};
  const categoryLabels={note:'Notiz',watering:'Bew?sserung',feeding:'D?ngung',training:'Training',defoliation:'Entlaubung',pest:'Sch?dlinge',flowering:'Bl?te',harvest:'Ernte',other:'Ereignis'};

  function applyOptionalMetrics(){
    const show=localStorage.getItem('gc.optional.co2')==='1';
    document.documentElement.dataset.showCo2=show?'true':'false';
    document.querySelectorAll('[data-optional-metric="co2"]').forEach(node=>node.hidden=!show);
  }
  window.GrowCentralOptionalMetrics={setCO2(enabled){localStorage.setItem('gc.optional.co2',enabled?'1':'0');applyOptionalMetrics();}};

  async function loadRoomsAndPlants(){
    try{
      const data=await api('/api/v1/rooms'),rooms=data.rooms||[];
      const freshest=rooms.filter(r=>r.latest_sensor).sort((a,b)=>Date.parse(b.latest_sensor?.timestamp||0)-Date.parse(a.latest_sensor?.timestamp||0))[0]||rooms[0]||null;
      const latest=freshest?.latest_sensor||{};
      const co2=$('co2Value'),co2Climate=$('climateCo2Value'),co2Hint=$('co2Hint');
      if(co2)co2.textContent=num(latest.co2_ppm,0);
      if(co2Climate)co2Climate.textContent=num(latest.co2_ppm,0);
      if(co2Hint)co2Hint.textContent=latest.co2_ppm!=null?(freshest?.name||'Raumsensor'):'Optionaler Sensor';

      const plantResults=await Promise.allSettled(rooms.map(r=>api(`/api/v1/rooms/${encodeURIComponent(r.id)}/plants`)));
      const plants=plantResults.flatMap(r=>r.status==='fulfilled'?(r.value.plants||[]):[]);
      const counts={};for(const p of plants)counts[p.phase]=(counts[p.phase]||0)+1;
      const phase=Object.entries(counts).sort((a,b)=>b[1]-a[1])[0]?.[0];
      if($('heroPhase'))$('heroPhase').textContent=phase?phaseLabels[phase]||phase:'Keine Pflanzen';
      if($('heroPhaseMeta'))$('heroPhaseMeta').textContent=plants.length?`${plants.length} Pflanze${plants.length===1?'':'n'} erfasst`:'Noch keine Pflanzendaten';
    }catch{
      if($('heroPhase'))$('heroPhase').textContent='Nicht verf?gbar';
      if($('heroPhaseMeta'))$('heroPhaseMeta').textContent='Raumdaten nicht erreichbar';
    }
  }

  async function loadNextAction(){
    try{
      const data=await api('/api/v1/automations'),rows=(data.automations||[]).filter(r=>r.enabled!==false);
      const timed=rows.find(r=>r.trigger==='time'&&String(r.trigger_value||'').trim());
      if($('heroNextAction'))$('heroNextAction').textContent=timed?String(timed.trigger_value):'?';
      if($('heroNextActionMeta'))$('heroNextActionMeta').textContent=timed?(timed.name||'Zeitregel'):'Keine Zeitregel aktiv';
    }catch{
      if($('heroNextAction'))$('heroNextAction').textContent='?';
      if($('heroNextActionMeta'))$('heroNextActionMeta').textContent='Automationen nicht erreichbar';
    }
  }

  async function loadEvents(){
    const root=$('overviewEvents');if(!root)return;
    try{
      const data=await api('/api/v1/rooms'),rooms=data.rooms||[];
      const results=await Promise.allSettled(rooms.map(r=>api(`/api/v1/rooms/${encodeURIComponent(r.id)}/journal`)));
      const events=[];
      results.forEach((result,index)=>{if(result.status!=='fulfilled')return;(result.value.entries||[]).forEach(e=>events.push({...e,room_name:rooms[index]?.name||''}))});
      events.sort((a,b)=>Date.parse(b.created_at||0)-Date.parse(a.created_at||0));
      root.innerHTML=events.length?events.slice(0,4).map(e=>{
        const when=Date.parse(e.created_at||0),time=Number.isFinite(when)?new Date(when).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'}):'?';
        return `<div><i class="${e.category==='pest'?'warn':e.category==='note'?'info':'good'}"></i><time>${esc(time)}</time><span>${esc(e.title||categoryLabels[e.category]||'Ereignis')}${e.room_name?` ? ${esc(e.room_name)}`:''}</span></div>`;
      }).join(''):'<div><i class="info"></i><time>?</time><span>Noch keine erfassten Ereignisse.</span></div>';
    }catch{root.innerHTML='<div><i class="warn"></i><time>?</time><span>Ereignisse nicht erreichbar.</span></div>'}
  }

  function refreshSnapshot(){
    const img=$('overviewCameraSnapshot'),fallback=$('overviewCameraFallback'),state=$('overviewCameraState');if(!img)return;
    img.onload=()=>{img.hidden=false;if(fallback)fallback.hidden=true;if(state)state.textContent='? LIVE'};
    img.onerror=()=>{img.hidden=true;if(fallback)fallback.hidden=false;if(state)state.textContent='NICHT VERF?GBAR'};
    img.src=`/api/v1/camera/snapshot?_=${Date.now()}`;
  }

  async function refresh(){await Promise.allSettled([loadRoomsAndPlants(),loadNextAction(),loadEvents()]);}
  $('overviewSnapshotBtn')?.addEventListener('click',refreshSnapshot);
  window.addEventListener('gc:refresh',refresh);
  window.addEventListener('gc:core-refreshed',refresh);
  applyOptionalMetrics();refresh();
  setInterval(refresh,60000);
})();
