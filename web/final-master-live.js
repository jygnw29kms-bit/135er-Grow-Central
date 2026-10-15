(()=>{
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api=async(path,options={})=>{const r=await fetch(path,{cache:'no-store',credentials:'same-origin',...options});const type=r.headers.get('content-type')||'';const body=type.includes('json')?await r.json():await r.text();if(!r.ok)throw new Error(body?.detail||body||`${r.status} ${r.statusText}`);return body};
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



  function normalizedPoints(values){
    const nums=values.map(Number).filter(Number.isFinite);if(nums.length<2)return '';
    const lo=Math.min(...nums),hi=Math.max(...nums),span=Math.max(.001,hi-lo);
    return nums.map((v,i)=>`${(i/(nums.length-1)*100).toFixed(2)},${(100-(v-lo)/span*100).toFixed(2)}`).join(' ');
  }
  async function loadOverviewHistory(){
    const climate=$('overviewClimateHistory'),energy=$('overviewEnergyHistory');if(!climate&&!energy)return;
    try{
      const roomData=await api('/api/v1/rooms'),rooms=(roomData.rooms||[]).filter(r=>r.latest_sensor);
      rooms.sort((a,b)=>Date.parse(b.latest_sensor?.timestamp||0)-Date.parse(a.latest_sensor?.timestamp||0));
      const room=rooms[0];
      if(!room){if(climate)climate.innerHTML='<div class="fm-chart-empty">Noch keine Raumhistorie.</div>';if(energy)energy.innerHTML='<div class="fm-chart-empty">Noch keine Leistungshistorie.</div>';return}
      const history=(await api(`/api/v1/rooms/${encodeURIComponent(room.id)}/sensors?limit=288`)).samples||[];
      if(climate){
        const t=normalizedPoints(history.map(x=>x.temperature_c)),h=normalizedPoints(history.map(x=>x.humidity_percent));
        climate.innerHTML=(t||h)?`<div class="chart-grid"></div><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Klima-Verlauf ${esc(room.name)}">${t?`<polyline class="line-a" points="${t}"/>`:''}${h?`<polyline class="line-b" points="${h}"/>`:''}</svg><div class="chart-legend"><span><i class="a"></i>Temperatur</span><span><i class="b"></i>Luftfeuchte</span><span>${esc(room.name)}</span></div>`:'<div class="fm-chart-empty">Noch nicht genug Klimahistorie.</div>';
      }
      if(energy){
        const p=history.map(x=>x.power_w).filter(v=>v!=null&&Number.isFinite(Number(v))).map(Number),pts=normalizedPoints(p);
        energy.innerHTML=pts?`<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Leistungs-Verlauf ${esc(room.name)}"><polyline points="${pts}"/></svg><span class="gc-history-label">${esc(room.name)} ? ${p.length} Messpunkte</span>`:'<div class="fm-chart-empty">Keine Leistungshistorie in den Raumdaten.</div>';
      }
    }catch(e){if(climate)climate.innerHTML='<div class="fm-chart-empty">Historie nicht erreichbar.</div>';if(energy)energy.innerHTML='<div class="fm-chart-empty">Leistungshistorie nicht erreichbar.</div>'}
  }

  const QUICK_POWER_PROVIDERS=new Set(['shelly','tapo','fritz','home_assistant','tuya','zigbee','mqtt']);
  const QUICK_SPEED_PROVIDERS=new Set(['tuya','mqtt']);
  async function deviceCommand(device,capability,value){
    return api(`/api/devices/${encodeURIComponent(device.provider_id)}/${encodeURIComponent(device.native_id)}/command`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({capability,value})});
  }
  function bindQuickPower(rootId,device,onLabel='Ein',offLabel='Aus'){
    const root=$(rootId);if(!root)return;const buttons=[...root.querySelectorAll('button')];
    if(!device||!(device.capabilities||[]).includes('power')||!QUICK_POWER_PROVIDERS.has(device.provider_id)){buttons.forEach(b=>b.disabled=true);return}
    const values=[true,false];buttons.slice(0,2).forEach((button,index)=>{button.disabled=false;button.title=device.name||device.native_id;button.onclick=async()=>{try{buttons.forEach(b=>b.disabled=true);await deviceCommand(device,'power',values[index]);button.textContent=index===0?onLabel:offLabel;window.dispatchEvent(new Event('gc:refresh'))}catch(e){buttons.forEach(b=>b.disabled=false);console.warn('Quick control',e)}}});
  }
  function bindQuickSpeed(rootId,device,values){
    const root=$(rootId);if(!root)return;const buttons=[...root.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
    if(!device||!(device.capabilities||[]).includes('fan_speed')||!QUICK_SPEED_PROVIDERS.has(device.provider_id))return;
    values.forEach((value,index)=>{const button=buttons[index+1];if(!button)return;button.disabled=false;button.title=device.name||device.native_id;button.onclick=async()=>{try{buttons.forEach(b=>b.disabled=true);await deviceCommand(device,'fan_speed',value);window.dispatchEvent(new Event('gc:refresh'))}catch(e){buttons.forEach((b,i)=>b.disabled=i===0);console.warn('Quick fan control',e)}}});
  }
  async function loadQuickControls(){
    try{
      const d=await api('/api/devices/discover?timeout=2'),rows=d.devices||[];
      const light=rows.find(x=>x.device_class==='light'&&(x.capabilities||[]).includes('power')&&QUICK_POWER_PROVIDERS.has(x.provider_id));
      const pump=rows.find(x=>x.device_class==='pump'&&(x.capabilities||[]).includes('power')&&QUICK_POWER_PROVIDERS.has(x.provider_id));
      const fans=rows.filter(x=>x.device_class==='fan'&&(x.capabilities||[]).includes('fan_speed')&&QUICK_SPEED_PROVIDERS.has(x.provider_id));
      bindQuickPower('quickLight',light,'Ein','Aus');
      bindQuickPower('quickIrrigation',pump,'Start','Stopp');
      bindQuickSpeed('quickCirculation',fans[0], [33,66,100]);
      bindQuickSpeed('quickExhaust',fans[1]||fans[0], [25,50,75,100]);
    }catch(e){console.warn('Quick controls unavailable',e)}
  }

  async function refresh(){await Promise.allSettled([loadRoomsAndPlants(),loadNextAction(),loadEvents(),loadQuickControls(),loadOverviewHistory()]);}
  $('overviewSnapshotBtn')?.addEventListener('click',refreshSnapshot);
  window.addEventListener('gc:refresh',refresh);
  window.addEventListener('gc:core-refreshed',refresh);
  applyOptionalMetrics();refresh();
  setInterval(refresh,60000);
})();
