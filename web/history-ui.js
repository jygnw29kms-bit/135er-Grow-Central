/* Grow Central durable grow history: UI only, no hardware control. */
(()=>{
  const el=id=>document.getElementById(id);
  const html=x=>String(x??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const dates=x=>x?new Date(x).toLocaleString('de-DE'):'Noch keine Datensätze';
  const room=()=>typeof activeRoom==='object'&&activeRoom?activeRoom:null;

  async function archiveRefresh(){
    const output=el('historyArchiveStatus'),metrics=el('historyArchiveMetrics');
    if(!output||!metrics)return;
    try{
      const [s,b]=await Promise.all([api('/api/v1/history/status'),api('/api/v1/history/bindings')]);
      const active=room(),bindings=b.devices||[];
      const list=bindings.filter(x=>x.room_id===active?.id).map(x=>x.device.replace('mars-hydro-','')).join(', ');
      output.textContent=s.total_points+' dauerhaft gespeicherte Messwerte · zuletzt '+dates(s.last)+
        ' · diesem Raum zugeordnet: '+(list||'noch keine Mars-Hydro-Geräte');
      if(!active){metrics.textContent='Raum auswählen.';return;}
      const r=await api('/api/v1/history/summary?room_id='+encodeURIComponent(active.id));
      const names={temperature_c:'Lufttemperatur',humidity_percent:'Luftfeuchte',
         soil_moisture_percent:'Bodenfeuchte',fan_rpm:'Lüfterdrehzahl',
         fan_setpoint_percent:'Lüfter-Sollwert',lamp_brightness_percent:'Licht-Sollwert',
         vpd_kpa:'VPD',airflow_cfm:'Luftvolumen (geschätzt)',pressure_pa:'Druck (geschätzt)'};
      metrics.innerHTML='<div style="display:flex;flex-wrap:wrap;gap:12px">'+
        Object.entries(r.metrics||{}).filter(([k])=>names[k]).map(([k,v])=>
          '<div style="padding:8px;border:1px solid #315258;border-radius:8px"><small>'+
          html(names[k])+'</small><strong style="display:block">'+Number(v.mean).toLocaleString('de-DE')+
          ' '+html(v.unit)+'</strong><small>'+v.count+' Punkte · '+html(v.source_kind)+'</small></div>'
        ).join('')+'</div>'+(Object.keys(r.metrics||{}).length===0?'Noch keine archivierten Werte für diesen Raum.':'');
    }catch(e){output.textContent='Archiv nicht verfügbar: '+e.message;}
  }
  async function bindDevice(device){
    const active=room();if(!active){alert('Zuerst Raum auswählen.');return;}
    if(!confirm(device+' für künftige Messungen dem Raum "'+active.name+'" zuordnen?'))return;
    try{
      await writeApi('/api/v1/history/bind-device',{method:'POST',
        body:JSON.stringify({device,room_id:active.id})});
      await archiveRefresh();
    }catch(e){alert('Zuordnung fehlgeschlagen: '+e.message);}
  }
  el('historyRefresh')?.addEventListener('click',archiveRefresh);
  el('historyBindFan')?.addEventListener('click',()=>bindDevice('mars-hydro-mzf002'));
  el('historyBindLamp')?.addEventListener('click',()=>bindDevice('mars-hydro-fc3000'));
  el('historyExport')?.addEventListener('click',async()=>{
    const active=room();if(!active)return;
    try{
      const url='/api/v1/history/export.csv?room_id='+encodeURIComponent(active.id);
      const res=await fetch(url,{cache:'no-store',credentials:'same-origin'});
      if(!res.ok)throw Error('HTTP '+res.status);
      const object=URL.createObjectURL(await res.blob());
      const link=document.createElement('a');link.href=object;
      link.download='grow-central-langzeit-'+active.id+'.csv';
      link.click();setTimeout(()=>URL.revokeObjectURL(object),1000);
    }catch(e){alert('CSV-Export nicht möglich: '+e.message);}
  });
  async function loadPlantChoices(){
    const a=el('historyPlantA'),b=el('historyPlantB');if(!a||!b)return;
    try{
      const data=await api('/api/v1/rooms');
      const lists=await Promise.all((data.rooms||[]).map(async r=>{
        try{const p=await api('/api/v1/rooms/'+encodeURIComponent(r.id)+'/plants');
          return(p.plants||[]).map(x=>({...x,room_name:r.name}));}
        catch{return[];}
      }));
      const plants=lists.flat().sort((x,y)=>(x.start_date||'').localeCompare(y.start_date||''));
      const oldA=a.value,oldB=b.value;
      const options='<option value="">Pflanze wählen</option>'+plants.map(p=>
        '<option value="'+html(p.id)+'">'+html(p.name)+' · '+html(p.start_date||'unbekannt')+
        ' · '+html(p.room_name)+'</option>').join('');
      a.innerHTML=options;b.innerHTML=options;
      if(plants.some(p=>p.id===oldA))a.value=oldA;
      else if(plants.length)a.value=plants[0].id;
      if(plants.some(p=>p.id===oldB))b.value=oldB;
      else if(plants.length>1)b.value=plants.at(-1).id;
      el('historyCompareStatus').textContent=plants.length<2?
        'Für einen Vergleich werden zwei gespeicherte Pflanzen mit Startdatum benötigt.':'Wähle zwei Pflanzen und starte den Vergleich.';
    }catch(e){el('historyCompareStatus').textContent='Pflanzen nicht geladen: '+e.message;}
  }
  async function comparePlants(){
    const a=el('historyPlantA').value,b=el('historyPlantB').value;
    const weeks=Math.max(1,Math.min(104,Number(el('historyWeeks').value)||16));
    const output=el('historyCompareStatus'),body=el('historyCompareRows');
    if(!a||!b||a===b){output.textContent='Zwei unterschiedliche Pflanzen auswählen.';return;}
    output.textContent='Vergleiche nach Pflanzenalter…';body.replaceChildren();
    try{
      const q=new URLSearchParams({plant_a:a,plant_b:b,weeks:String(weeks)});
      const result=await api('/api/v1/history/compare-plants?'+q);
      const rows=[];
      const preferred=['temperature_c','humidity_percent','soil_moisture_percent',
        'vpd_kpa','fan_rpm','fan_setpoint_percent','lamp_brightness_percent',
        'airflow_cfm','pressure_pa'];
      for(const week of result.differences||[]){
        for(const metric of preferred){
          const p=week.metrics?.[metric];if(!p)continue;
          rows.push([week.week,metric,p.a,p.b,p.delta_b_minus_a,p.unit,p.source_kind]);
        }
      }
      for(const r of rows.slice(0,250)){
        const tr=document.createElement('tr');
        for(const value of [r[0],r[1],r[2]+' '+r[5],r[3]+' '+r[5],
          (r[4]>0?'+':'')+r[4]+' '+r[5]]){
          const td=document.createElement('td');td.textContent=String(value);tr.appendChild(td);
        }
        body.appendChild(tr);
      }
      output.textContent=rows.length?rows.length+' vergleichbare Wochen-Messgrößen · Showwerte ausdrücklich nur geschätzt.':
        'Für diese beiden Pflanzen gibt es in den gleichen Grow-Wochen noch keine vergleichbaren archivierten Messwerte.';
    }catch(e){output.textContent='Vergleich fehlgeschlagen: '+e.message;}
  }
  el('historyCompareRun')?.addEventListener('click',comparePlants);
  document.querySelector('[data-room-tab="sensors"]')?.addEventListener('click',archiveRefresh);
  document.querySelector('[data-room-tab="plants"]')?.addEventListener('click',loadPlantChoices);
  document.querySelectorAll('[data-target="rooms:plants"]').forEach(x=>x.addEventListener('click',loadPlantChoices));
  document.querySelectorAll('[data-target="rooms:sensors"]').forEach(x=>x.addEventListener('click',archiveRefresh));
})();
