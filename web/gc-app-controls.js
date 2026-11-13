/* Grow Central device-app UI, original Final Master preserved. No simulated readings. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const F='MZ_MZF002_68756_A0A3B35EFDC8',L='MZ_MARS_68756_FCB467AEC260';
  const S={fan:null,lamp:null,ids:{},busy:false,fanTouched:false,lampTouched:false,
           period:7,plot:null,view:'',lastScan:0,refresh:null};
  const safeNumber=n=>Number.isFinite(Number(n))?Number(n):null;
  const num=(n,d=0)=>n==null?'—':Number(n).toLocaleString('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d});
  const writeText=(id,value)=>{if($(id))$(id).textContent=value;};
  async function api(path,body){
    const response=await fetch(path,body===undefined?{cache:'no-store'}:
      {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});
    if(!response.ok)throw Error('HTTP '+response.status);
    return response.json();
  }
  function note(message,isError=false){
    writeText('gcDeviceStatus',message);
    $('gcDeviceStatus')?.classList.toggle('gc-app-error',isError);
  }
  function changeBusy(value){
    S.busy=value;
    for(const id of ['gcFanApply','gcLampApply','gcLampOn','gcLampOff','gcAppRefresh']){
      if($(id))$(id).disabled=value;
    }
  }
  async function discover(force=false){
    if(!force && Date.now()-S.lastScan<100000 && S.ids.fan && S.ids.lamp)return;
    const data=await api('/api/mars-hydro/ble/scan',{seconds:6});
    S.ids.fan=data.devices?.find(x=>x.name===F)?.candidate_id||null;
    S.ids.lamp=data.devices?.find(x=>x.name===L)?.candidate_id||null;
    S.lastScan=Date.now();
  }
  async function observe(kind){
    const id=S.ids[kind];if(!id)return null;
    const result=await api('/api/mars-hydro/ble/observe-'+(kind==='fan'?'fan':'lamp')+'-telemetry',{candidate_id:id});
    return result.status==='decoded'?result.latest:null;
  }
  function fanView(row){
    if(!row)return;
    S.fan=row;
    writeText('gcFanOnline','BLE live');
    $('gcFanOnline')?.classList.add('online');
    writeText('gcFanNow',(row.power_on?'Ein':'Aus')+' · '+num(row.setpoint_percent)+' %');
    writeText('gcFanRpm',num(row.rpm)+' RPM');
    writeText('gcFanTemp',num(row.temperature_c,1)+' °C');
    writeText('gcFanHumidity',num(row.humidity_rh,1)+' %');
    writeText('gcFanCfm',num(row.airflow_cfm,1));
    writeText('gcFanPa',num(row.pressure_pa,1));
    if(!S.fanTouched && $('gcFanSlider')){
      $('gcFanSlider').value=row.setpoint_percent;
      writeText('gcFanTarget',row.setpoint_percent+' %');
    }
  }
  function lampView(row){
    if(!row)return;
    S.lamp=row;
    writeText('gcLampOnline','BLE live');
    $('gcLampOnline')?.classList.add('online');
    writeText('gcLampNow',row.power_on?'Ein':'Aus');
    writeText('gcLampLevel',num(row.brightness_percent)+' %');
    if(!S.lampTouched && $('gcLampSlider')){
      $('gcLampSlider').value=row.brightness_percent;
      writeText('gcLampTarget',row.brightness_percent+' %');
    }
  }
  async function refresh(){
    if(S.busy || document.hidden || S.view!=='devices')return;
    changeBusy(true);
    note('Verbinde Geräte und lese echte Bluetooth-Werte…');
    try{
      await discover(true);
      const fan=await observe('fan').catch(()=>null);
      if(fan)fanView(fan);
      else {writeText('gcFanOnline','Nicht erreichbar');$('gcFanOnline')?.classList.remove('online');}
      const lamp=await observe('lamp').catch(()=>null);
      if(lamp)lampView(lamp);
      else {writeText('gcLampOnline','Nicht erreichbar');$('gcLampOnline')?.classList.remove('online');}
      note((fan?'DF150-M live':'DF150-M ohne neue Daten')+' · '+
           (lamp?'FC3000 live':'FC3000 ohne neue Daten')+' · '+
           new Date().toLocaleTimeString('de-DE'));
    }catch(e){note('Bluetooth-Verbindung: '+e.message,true);}
    finally{changeBusy(false);}
  }
  async function command(kind,action,value){
    if(S.busy)return;
    const label=kind==='fan'?'DF150-M':'FC3000';
    const name=action==='power'?(value===0?'ausschalten':'einschalten'):value+' % einstellen';
    if(!window.confirm(label+' wirklich '+name+'? Die Hardware reagiert sofort.'))return;
    changeBusy(true);note('Sende an '+label+' und warte auf echte Rückmeldung…');
    try{
      await discover(true);
      if(!S.ids[kind])throw Error(label+' nicht via BLE sichtbar');
      const path=kind==='fan'?'/api/mars-hydro/ble/control-fan':'/api/mars-hydro/ble/control-lamp-trial';
      const params=kind==='fan'?{candidate_id:S.ids.fan,percent:value,confirm_physical_change:true}:
        {candidate_id:S.ids.lamp,action,value,confirm_physical_change:true};
      const result=await api(path,params);
      if(result.latest){if(kind==='fan')fanView(result.latest);else lampView(result.latest);}
      if(result.device_report_confirmed){
        note(label+': '+name+' bestätigt · '+new Date().toLocaleTimeString('de-DE'));
        if(kind==='fan')S.fanTouched=false;else S.lampTouched=false;
      }else note(label+': Befehl nicht sicher bestätigt. Nicht automatisch wiederholt.',true);
    }catch(e){note(label+': '+e.message+' · kein automatischer Zweitversuch',true);}
    finally{changeBusy(false);}
  }
  function controls(){
    $('gcFanSlider')?.addEventListener('input',e=>{
      S.fanTouched=true;writeText('gcFanTarget',e.target.value+' %');
    });
    $('gcFanApply')?.addEventListener('click',()=>command('fan','speed',Number($('gcFanSlider').value)));
    $('gcLampSlider')?.addEventListener('input',e=>{
      S.lampTouched=true;writeText('gcLampTarget',e.target.value+' %');
    });
    $('gcLampApply')?.addEventListener('click',()=>command('lamp','brightness',Number($('gcLampSlider').value)));
    $('gcLampOn')?.addEventListener('click',()=>command('lamp','power',1));
    $('gcLampOff')?.addEventListener('click',()=>command('lamp','power',0));
    $('gcAppRefresh')?.addEventListener('click',refresh);
    $('gcHistoryPeriod')?.addEventListener('change',e=>{S.period=Number(e.target.value);history();});
    $('gcHistoryMetric')?.addEventListener('change',history);
    $('gcHistoryRoom')?.addEventListener('change',history);
    $('gcCompareButton')?.addEventListener('click',compare);
    $('gcGrowAdd')?.addEventListener('click',createGrow);
  }
  const plotColor='#39efab';
  const HISTORY_METRICS={
    temperature_c:['Temperatur','°C'],
    humidity_percent:['Luftfeuchte','% rF'],
    fan_rpm:['Lüfterdrehzahl','RPM'],
    fan_setpoint_percent:['Lüfter-Sollwert','%'],
    lamp_brightness_percent:['Licht-Sollwert','%'],
    soil_moisture_percent:['Bodenfeuchte','%'],
    soil_temperature_c:['Bodentemperatur','°C'],
    ppfd_umol_m2_s:['PPFD','µmol/m²/s'],
    ec_ms_cm:['EC','mS/cm'],
    ph:['pH','']
  };
  function plot(points,metric){
    S.plot={points,metric};
    const canvas=$('gcHistoryChart');if(!canvas)return;
    const dpr=Math.min(2,window.devicePixelRatio||1),w=Math.max(240,canvas.clientWidth||300),h=190;
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
    ctx.font='11px system-ui';ctx.fillStyle='#83aba2';
    const values=points.filter(x=>x.value!=null&&Number.isFinite(Number(x.value))&&!Number.isNaN(Date.parse(x.recorded_at)))
      .map(x=>({t:Date.parse(x.recorded_at),v:Number(x.value)}));
    const label=HISTORY_METRICS[metric]||[metric,''];
    if(values.length<2){
      ctx.fillText('Noch keine ausreichende Messreihe für '+label[0]+'.',13,100);
      writeText('gcHistoryCaption',values.length+' Messpunkte · '+label[0]+' · weitere Werte werden archiviert');
      return;
    }
    let low=Math.min(...values.map(x=>x.v)),high=Math.max(...values.map(x=>x.v));
    const padding=Math.max(.15,(high-low)*.12);
    low-=padding;high+=padding;
    const left=55,right=w-14,top=18,bottom=156;
    for(let i=0;i<4;i++){
      const y=top+(bottom-top)*i/3;ctx.strokeStyle='#294644';ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();
      ctx.fillStyle='#9cb9b0';
      ctx.fillText(num(high-i*(high-low)/3,1),4,y+4);
    }
    const first=values[0].t,last=values[values.length-1].t;
    ctx.beginPath();ctx.strokeStyle=plotColor;ctx.lineWidth=2.3;
    values.forEach((p,i)=>{
      const x=left+(right-left)*(last===first?i/(values.length-1):(p.t-first)/(last-first));
      const y=bottom-(p.v-low)/(high-low)*(bottom-top);
      if(!i)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    });ctx.stroke();
    ctx.fillStyle='#8ea9a5';
    ctx.fillText(new Date(first).toLocaleDateString('de-DE'),left,bottom+20);
    ctx.fillText(new Date(last).toLocaleDateString('de-DE'),Math.max(left,right-85),bottom+20);
    const measured=['fan_rpm','temperature_c','humidity_percent','soil_moisture_percent',
      'soil_temperature_c','ppfd_umol_m2_s','ec_ms_cm','ph'].includes(metric);
    writeText('gcHistoryCaption',values.length+' archivierte Werte · '+label[0]+' ('+label[1]+') · '+
      (measured?'Messwerte':'gemeldeter Sollwert'));
  }
  async function history(){
    const metric=$('gcHistoryMetric')?.value||'temperature_c';
    const room=$('gcHistoryRoom')?.value||'';
    try{
      const start=new Date(Date.now()-S.period*86400000).toISOString();
      const params=new URLSearchParams({metric,start,limit:'5000'});
      if(room)params.set('room_id',room);
      const [summary,series]=await Promise.all([
        api('/api/mars-history/summary'),
        api('/api/v1/history/points?'+params.toString())
      ]);
      const totals=summary.totals||[];
      writeText('gcHistoryCount',totals.reduce((n,v)=>n+v.samples,0).toLocaleString('de-DE')+' Geräte-Stichproben archiviert');
      plot(series.points||[],metric);
    }catch(e){writeText('gcHistoryCaption','Archiv derzeit nicht erreichbar: '+e.message);}
  }
  async function loadGrows(){
    const [data,roomData]=await Promise.all([
      api('/api/mars-history/grows'),
      api('/api/v1/rooms').catch(()=>({rooms:[]}))
    ]);
    const grows=data.grows||[];
    const roomChart=$('gcHistoryRoom');
    if(roomChart){
      const previous=roomChart.value;roomChart.replaceChildren();
      const all=document.createElement('option');all.value='';all.textContent='Alle Räume';
      roomChart.appendChild(all);
      for(const room of roomData.rooms||[]){
        const option=document.createElement('option');option.value=room.id;option.textContent=room.name;
        roomChart.appendChild(option);
      }
      if((roomData.rooms||[]).some(r=>r.id===previous))roomChart.value=previous;
    }
    const roomPicker=$('gcGrowRoom');
    if(roomPicker){
      const previous=roomPicker.value;roomPicker.replaceChildren();
      const empty=document.createElement('option');empty.value='';empty.textContent='Ohne Raumzuordnung';
      roomPicker.appendChild(empty);
      for(const room of roomData.rooms||[]){
        const option=document.createElement('option');
        option.value=room.id;option.textContent=room.name;
        roomPicker.appendChild(option);
      }
      roomPicker.value=previous;
    }
    for(const id of ['gcGrowA','gcGrowB']){
      const select=$(id);if(!select)continue;
      const previous=select.value;select.replaceChildren();
      for(const grow of grows){
        const option=document.createElement('option');option.value=grow.id;
        option.textContent=grow.name+' · '+new Date(grow.started_at).toLocaleDateString('de-DE');
        select.appendChild(option);
      }
      if(grows.some(x=>String(x.id)===previous))select.value=previous;
      else if(id==='gcGrowB'&&grows.length>1)select.selectedIndex=1;
    }
    writeText('gcGrowCount',grows.length+' Grow-Durchläufe gespeichert');
  }
  async function createGrow(){
    const name=$('gcGrowName')?.value.trim(),crop=$('gcGrowCrop')?.value.trim();
    const date=$('gcGrowDate')?.value;
    if(!name||!date){writeText('gcGrowFeedback','Name und Startdatum fehlen.');return;}
    if(!window.confirm('Grow-Durchlauf "'+name+'" dauerhaft anlegen?'))return;
    try{
      await api('/api/mars-history/grows',{name,crop,room_id:$('gcGrowRoom')?.value||'',
        started_at:new Date(date+'T12:00:00').toISOString()});
      $('gcGrowName').value='';
      writeText('gcGrowFeedback','Grow "'+name+'" angelegt. Sensorwerte werden nach Datum verglichen.');
      await loadGrows();
    }catch(e){writeText('gcGrowFeedback','Konnte Grow nicht speichern: '+e.message);}
  }
  async function compare(){
    const a=Number($('gcGrowA')?.value),b=Number($('gcGrowB')?.value);
    if(!a||!b||a===b){writeText('gcGrowFeedback','Zwei unterschiedliche Durchläufe auswählen.');return;}
    try{
      const out=await api('/api/mars-history/compare?a='+a+'&b='+b);
      const target=$('gcCompareResult');target.replaceChildren();
      for(const x of out.comparisons){
        const div=document.createElement('div');div.className='gc-app-comparerow';
        const name=document.createElement('b');name.textContent=x.grow.name;
        div.appendChild(name);
        const fan=x.metrics?.find(m=>m.device==='fan'),lamp=x.metrics?.find(m=>m.device==='lamp');
        const info=document.createElement('span');
        info.textContent=fan?('Ø '+num(fan.avg_temp_c,1)+' °C · '+num(fan.avg_humidity_rh,1)+' % rF · '+num(fan.avg_rpm)+' RPM · '+num(fan.count)+' Samples'):'Noch keine Klimamessungen';
        div.appendChild(info);
        const light=document.createElement('span');
        light.textContent=lamp?('Ø Licht-Sollwert '+num(lamp.avg_light_percent,1)+' %'):'Lichtwerte nicht verfügbar';
        div.appendChild(light);
        const rooms=x.room_metrics||[];
        for(const [metric,label,unit] of [
          ['soil_moisture_percent','Ø Bodenfeuchte','%'],
          ['soil_temperature_c','Ø Bodentemperatur','°C'],
          ['ppfd_umol_m2_s','Ø PPFD','µmol/m²/s'],
          ['ec_ms_cm','Ø EC','mS/cm'],
          ['ph','Ø pH','']
        ]){
          const row=rooms.find(r=>r.metric===metric);
          if(row?.avg==null)continue;
          const span=document.createElement('span');
          span.textContent=label+': '+num(row.avg,1)+' '+unit;
          div.appendChild(span);
        }
        target.appendChild(div);
      }
      writeText('gcGrowFeedback','Vergleich anhand archivierter Messwerte, keine Schätzungen.');
    }catch(e){writeText('gcGrowFeedback','Vergleich fehlgeschlagen: '+e.message);}
  }
  async function overviewQuick(){
    try {
      const data=await api('/api/mars-history/summary');
      const fan=data.latest?.find(x=>x.device==='fan');
      const lamp=data.latest?.find(x=>x.device==='lamp');
      if(fan){
        writeText('gcQuickTemp',num(fan.temperature_c,1)+' °C');
        writeText('gcQuickHum',num(fan.humidity_rh,1)+' %');
        writeText('gcQuickFan',fan.power_on?num(fan.setpoint_percent)+' %':'Aus');
      }
      if(lamp)writeText('gcQuickLamp',lamp.power_on?num(lamp.brightness_percent)+' %':'Aus');
      const stamps=[fan?.recorded_at,lamp?.recorded_at].filter(Boolean).map(Date.parse).filter(Number.isFinite);
      if(stamps.length){
        const age=Math.round((Date.now()-Math.max(...stamps))/60000);
        writeText('gcQuickAge',age<0?'Letzte Archivmessung · Zeitprüfung nötig':
          age<2?'Zuletzt aufgezeichnet: gerade eben':
          'Letzte Archivmessung vor '+age+' Minuten'+(age>10?' · nicht aktuell':''));
      }else writeText('gcQuickAge','Noch keine automatischen Messungen im Archiv');
    }catch(e){writeText('gcQuickAge','Messarchiv derzeit nicht erreichbar');}
  }
  function view(id){
    S.view=id;
    if(id==='devices'){
      refresh();
      if(S.refresh===null)S.refresh=setInterval(refresh,60000);
    }else if(S.refresh!==null){
      clearInterval(S.refresh);S.refresh=null;
    }
    if(id==='growlog'){history();loadGrows().catch(e=>writeText('gcGrowFeedback',e.message));}
    if(id==='overview')overviewQuick();
  }
  document.addEventListener('gc:view',e=>view(e.detail.id));
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden&&S.view==='devices')refresh();
  });
  window.addEventListener('resize',()=>{if(S.view==='growlog'&&S.plot)plot(S.plot.points,S.plot.metric);});
  controls();
  document.querySelectorAll('[data-gc-nav]').forEach(button=>button.addEventListener('click',()=>{
    document.querySelector('#mainNav [data-view="'+button.dataset.gcNav+'"]')?.click();
  }));
  if($('overview')?.classList.contains('active')){S.view='overview';overviewQuick();}
  if($('gcGrowDate'))$('gcGrowDate').value=new Date().toLocaleDateString('en-CA');
})();
