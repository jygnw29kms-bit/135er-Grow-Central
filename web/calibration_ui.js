(()=>{
  const list=document.getElementById('calibrationList');
  if(!list)return;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  async function api(path){const r=await fetch(path,{cache:'no-store',credentials:'same-origin'});if(!r.ok)throw new Error(`${r.status} ${r.statusText}`);return r.json()}
  function when(value){if(!value)return 'noch nie';try{return new Date(value).toLocaleString('de-DE')}catch{return value}}
  async function load(){
    list.innerHTML='<div class="empty">Kalibrierstatus wird geladen…</div>';
    try{
      const [data,roomData]=await Promise.all([api('/api/v1/sensor-calibration'),api('/api/v1/rooms')]);
      const rooms=new Map((roomData.rooms||[]).map(r=>[r.id,r.name]));
      const rows=data.devices||[];
      if(!rows.length){list.innerHTML='<div class="empty">Noch keine Grow-Central Bodenfeuchtesensoren erkannt.</div>';return;}
      list.innerHTML=rows.map(row=>{
        const cal=row.calibration||{},q=cal.quality||{},points=cal.points||{};
        const valid=row.calibration_status==='valid';
        const reason=valid?'Kalibriert · '+when(cal.calibrated_at):esc(row.reason||'Kalibrierung erforderlich');
        const detail=valid?`Luft ${esc(points.air_raw)} · Wasser ${esc(points.wet_raw)} · Substrat ${esc(points.substrate_raw)} · Span ${esc(points.span_raw)}${q.signal_quality?' · '+esc(q.signal_quality):''}`:'Produktive Bodenfeuchte bleibt gesperrt.';
        return `<article class="device-row calibration-row"><div><strong>${esc(row.name)}</strong><small>${esc(row.device_id)} · FP ${esc(row.fingerprint||'—')} · FW ${esc(row.firmware||'—')}</small></div><div><strong>${esc(rooms.get(row.room_id)||'Noch nicht zugewiesen')}</strong><small>${row.online?'Online':'Offline'}</small></div><div><span class="state-badge ${row.online?'':'offline'}">${row.online?'ONLINE':'OFFLINE'}</span><small>${esc(row.status)}</small></div><div><span class="state-badge ${valid?'':'offline'}">${valid?'KALIBRIERT':'ERFORDERLICH'}</span><small>${reason}</small><small>${detail}</small><button type="button" class="secondary calibration-open" data-device="${esc(row.device_id)}">${valid?'Alle 3 Punkte neu kalibrieren':'Kalibrieren'}</button></div></article>`;
      }).join('');
      list.querySelectorAll('.calibration-open').forEach(btn=>btn.addEventListener('click',()=>{
        document.querySelector('#mainNav [data-view="devices"]')?.click();
        window.dispatchEvent(new CustomEvent('gc:usb-open',{detail:{device_id:btn.dataset.device}}));
      }));
    }catch(e){list.innerHTML=`<div class="empty">Kalibrierstatus nicht verfügbar: ${esc(e.message)}</div>`}
  }
  document.getElementById('calibrationRefresh')?.addEventListener('click',load);
  window.addEventListener('gc:refresh',load);
  document.querySelector('#mainNav [data-view="calibration"]')?.addEventListener('click',load);
  load();
})();
