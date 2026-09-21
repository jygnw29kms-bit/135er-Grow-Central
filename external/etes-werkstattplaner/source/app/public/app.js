const START=7*60, END=18*60, STEP=30;
let currentUser=null, appointments=[], config={resources:[],mechanics:[],statuses:[],parts:[],loaner:[]};
let events=null;
const $=id=>document.getElementById(id);

function applyDeviceProfile(){
  const w=window.innerWidth||document.documentElement.clientWidth;
  const h=window.innerHeight||document.documentElement.clientHeight;
  const coarse=window.matchMedia&&window.matchMedia('(pointer: coarse)').matches;
  const touch=coarse||navigator.maxTouchPoints>0;
  const shortSide=Math.min(w,h);
  let device='desktop';
  if((touch&&shortSide<=600)||w<=700) device='phone';
  else if((touch&&w<=1366)||w<=1100) device='tablet';
  const orientation=w>h?'landscape':'portrait';
  document.documentElement.dataset.device=device;
  document.documentElement.dataset.orientation=orientation;
  document.body.classList.remove('device-phone','device-tablet','device-desktop','orientation-portrait','orientation-landscape','touch-ui');
  document.body.classList.add('device-'+device,'orientation-'+orientation);
  if(touch) document.body.classList.add('touch-ui');
  document.documentElement.style.setProperty('--app-vh',(h*0.01)+'px');
}
let deviceResizeTimer=null;
function scheduleDeviceProfile(){
  clearTimeout(deviceResizeTimer);
  deviceResizeTimer=setTimeout(()=>{applyDeviceProfile();if(currentUser)render()},90);
}

function todayISO(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function mins(t){const p=t.split(':').map(Number);return p[0]*60+p[1]}
function timeLabel(m){return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')}
function canEdit(){return currentUser&&['admin','editor'].includes(currentUser.role)}
function isAdmin(){return currentUser&&currentUser.role==='admin'}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function uuid(){return crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(16).slice(2)}
function toast(msg){$('toast').textContent=msg;$('toast').classList.remove('hidden');setTimeout(()=>$('toast').classList.add('hidden'),2600)}
function hideAllScreens(){['setupScreen','loginScreen','appShell'].forEach(id=>$(id).classList.add('hidden'))}
function showSetup(){hideAllScreens();$('setupScreen').classList.remove('hidden')}
function showLogin(){hideAllScreens();$('loginScreen').classList.remove('hidden')}
function showApp(){hideAllScreens();$('appShell').classList.remove('hidden')}

async function api(url,opts={}){
  const r=await fetch(url,{...opts,headers:{'Content-Type':'application/json',...(opts.headers||{})}});
  let data={};try{data=await r.json()}catch{}
  if(r.status===428&&data.needs_setup){showSetup();const e=new Error(data.error||'Ersteinrichtung erforderlich');e.status=r.status;e.data=data;throw e}
  if(r.status===401){showLogin();const e=new Error('Sitzung abgelaufen');e.status=401;e.data=data;throw e}
  if(!r.ok){const e=new Error(data.error||('HTTP '+r.status));e.status=r.status;e.data=data;throw e}
  return data;
}

async function init(){
  applyDeviceProfile();
  $('datePicker').value=todayISO();
  bind();
  try{
    const s=await api('/api/setup-status');
    if(s.needs_setup){showSetup();return}
    try{const me=await api('/api/me');currentUser=me.user;await enterApp()}catch{showLogin()}
  }catch(e){console.error(e);showLogin()}
  if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
}

function bind(){
  $('setupForm').onsubmit=async e=>{
    e.preventDefault();$('setupError').textContent='';
    const p1=$('setupPassword').value,p2=$('setupPassword2').value;
    if(p1!==p2){$('setupError').textContent='Passwörter stimmen nicht überein';return}
    try{
      const d=await api('/api/setup',{method:'POST',body:JSON.stringify({name:$('setupName').value.trim(),password:p1,password_confirm:p2})});
      currentUser=d.user;$('setupPassword').value='';$('setupPassword2').value='';await enterApp();toast('Ersteinrichtung abgeschlossen');
    }catch(err){$('setupError').textContent=err.message}
  };
  $('loginForm').onsubmit=async e=>{
    e.preventDefault();$('loginError').textContent='';
    try{
      const d=await api('/api/login',{method:'POST',body:JSON.stringify({name:$('loginName').value,password:$('loginPassword').value})});
      currentUser=d.user;$('loginPassword').value='';await enterApp();
    }catch(err){$('loginError').textContent=err.message}
  };
  $('logoutBtn').onclick=async()=>{try{await api('/api/logout',{method:'POST'})}catch{};currentUser=null;if(events)events.close();showLogin()};
  $('todayBtn').onclick=()=>{$('datePicker').value=todayISO();loadAppointments()};
  $('prevBtn').onclick=()=>shiftDate(-1);
  $('nextBtn').onclick=()=>shiftDate(1);
  $('datePicker').onchange=loadAppointments;
  $('newBtn').onclick=()=>openNew();
  $('appointmentForm').addEventListener('submit',async e=>{e.preventDefault();if(canEdit())await saveFromForm()});
  $('deleteBtn').onclick=async()=>{
    if(!canEdit())return;
    const id=$('apptId').value;
    if(id&&confirm('Termin wirklich löschen?')){
      try{await api('/api/appointments/'+encodeURIComponent(id),{method:'DELETE'});$('appointmentDialog').close();await loadAppointments();toast('Termin gelöscht')}catch(e){alert(e.message)}
    }
  };
  $('usersBtn').onclick=openUsers;
  $('usersCloseBtn').onclick=()=>$('usersDialog').close();
  $('refreshUsersBtn').onclick=loadUsers;
  $('newUserForm').onsubmit=createUser;
  window.addEventListener('online',()=>setOnline(true));
  window.addEventListener('offline',()=>setOnline(false));
  window.addEventListener('resize',scheduleDeviceProfile,{passive:true});
  window.addEventListener('orientationchange',scheduleDeviceProfile,{passive:true});
}

async function enterApp(){
  config=await api('/api/config');
  fillSelect($('resource'),config.resources);fillSelect($('mechanic'),config.mechanics);fillSelect($('status'),config.statuses);fillSelect($('parts'),config.parts);fillSelect($('loaner'),config.loaner);
  $('legend').innerHTML=config.statuses.map(s=>'<span data-status="'+esc(s)+'">'+esc(s)+'</span>').join('');
  updateRole();showApp();await loadAppointments();connectEvents();setOnline(navigator.onLine);
}
function fillSelect(el,arr){el.innerHTML='';arr.forEach(x=>el.add(new Option(x,x)))}
function updateRole(){
  $('currentUser').textContent=currentUser.name;
  $('roleBadge').textContent=currentUser.role==='admin'?'Administrator':currentUser.role==='editor'?'Bearbeitung':'Nur Lesen';
  $('newBtn').disabled=!canEdit();
  $('usersBtn').classList.toggle('hidden',!isAdmin());
}
function setOnline(ok){$('syncDot').classList.toggle('offline',!ok);$('syncDot').title=ok?'Server verbunden':'Offline'}
function connectEvents(){if(events)events.close();events=new EventSource('/api/events');events.onopen=()=>setOnline(true);events.onerror=()=>setOnline(false);events.addEventListener('appointments-changed',()=>loadAppointments())}
function shiftDate(days){let d=new Date($('datePicker').value+'T12:00:00');d.setDate(d.getDate()+days);$('datePicker').value=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');loadAppointments()}
function updateDateLabel(){
  const d=new Date($('datePicker').value+'T12:00:00');
  $('railDateLabel').textContent=d.toLocaleDateString('de-DE',{day:'2-digit',month:'long',year:'numeric'});
}
async function loadAppointments(){
  try{
    updateDateLabel();
    const d=await api('/api/appointments?date='+encodeURIComponent($('datePicker').value));
    appointments=d.appointments;
    $('todayCount').textContent=appointments.length+' '+(appointments.length===1?'Termin':'Termine');
    render();
  }catch(e){console.error(e)}
}

function resourceIcon(name){return name==='Achsmessplatz'?'◎':'▥'}
function render(){
  const p=$('planner');
  const hours=[];
  for(let m=START;m<END;m+=60)hours.push(timeLabel(m));
  p.innerHTML='<div class="timeline-head"><div class="timeline-corner">Arbeitsplatz</div><div class="time-scale">'+hours.map(h=>'<span>'+h+'</span>').join('')+'</div></div>';
  config.resources.forEach(resource=>{
    const row=document.createElement('div');row.className='resource-row';
    row.innerHTML='<div class="resource-label"><div class="resource-icon">'+resourceIcon(resource)+'</div><div class="resource-copy"><strong>'+esc(resource)+'</strong><small>'+(resource==='Achsmessplatz'?'Achsvermessung · PKW / Transporter':'Hebebühne · PKW')+'</small></div></div><div class="resource-track" data-resource="'+esc(resource)+'"></div>';
    const track=row.querySelector('.resource-track');
    if(canEdit()){
      track.addEventListener('dblclick',e=>{const t=timeFromPointer(track,e);openNew(resource,t)});
      track.addEventListener('dragover',e=>e.preventDefault());
      track.addEventListener('drop',e=>dropOnTrack(e,track,resource));
    }
    p.appendChild(row);
  });
  drawAppointments();
  drawNowLines();
}
function timeFromPointer(track,e){
  const r=track.getBoundingClientRect();
  let ratio=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));
  let m=START+Math.round((ratio*(END-START))/STEP)*STEP;
  m=Math.max(START,Math.min(END-STEP,m));
  return timeLabel(m);
}
function drawAppointments(){
  appointments.forEach(a=>{
    const track=document.querySelector('.resource-track[data-resource="'+CSS.escape(a.resource)+'"]');
    if(!track)return;
    const sm=Math.max(START,mins(a.start)),em=Math.min(END,mins(a.end));
    if(em<=START||sm>=END)return;
    const left=((sm-START)/(END-START))*100;
    const width=Math.max(3,((em-sm)/(END-START))*100);
    const card=document.createElement('div');
    card.className='appointment'+(canEdit()?'':' readonly');
    card.dataset.status=a.status;card.draggable=canEdit();
    card.style.left=left+'%';card.style.width='calc('+width+'% - 4px)';
    card.innerHTML='<strong>'+esc(a.plate)+(a.vehicle?' · '+esc(a.vehicle):'')+'</strong><div class="jobline">'+esc(a.job||a.customer||'Werkstatttermin')+'</div><div class="meta"><span>'+a.start+'–'+a.end+(a.mechanic&&a.mechanic!=='—'?' · '+esc(a.mechanic):'')+'</span><span class="status-chip">'+esc(a.status)+'</span></div>';
    card.onclick=()=>openEdit(a.id);
    card.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',a.id);e.dataTransfer.effectAllowed='move'});
    track.appendChild(card);
  });
}
function drawNowLines(){
  if($('datePicker').value!==todayISO())return;
  const now=new Date(),m=now.getHours()*60+now.getMinutes();
  if(m<START||m>END)return;
  const left=((m-START)/(END-START))*100;
  document.querySelectorAll('.resource-track').forEach(track=>{const line=document.createElement('div');line.className='now-line';line.style.left=left+'%';track.appendChild(line)});
}
async function dropOnTrack(e,track,resource){
  if(!canEdit())return;
  e.preventDefault();
  const id=e.dataTransfer.getData('text/plain'),a=appointments.find(x=>x.id===id);if(!a)return;
  const start=timeFromPointer(track,e),duration=mins(a.end)-mins(a.start),s=mins(start),en=Math.min(END,s+duration);
  const data={...a,resource,start:timeLabel(s),end:timeLabel(en)};
  try{await persist(data,false);toast('Termin verschoben')}catch(err){if(err.status===409&&confirm('Arbeitsplatz ist bereits mit '+err.data.conflict.plate+' belegt. Trotzdem verschieben?'))await persist(data,true);else if(err.status!==409)alert(err.message)}
}

function openNew(resource='Bühne 1',start='08:00'){
  if(!canEdit())return;
  const end=timeLabel(Math.min(END,mins(start)+60));
  $('dialogTitle').textContent='Neuer Werkstatttermin';$('apptId').value='';$('apptDate').value=$('datePicker').value;$('resource').value=resource;$('startTime').value=start;$('endTime').value=end;$('plate').value='';$('vehicle').value='';$('customer').value='';$('phone').value='';$('mechanic').value=config.mechanics[0];$('status').value=config.statuses[0];$('job').value='';$('parts').value=config.parts[0];$('loaner').value=config.loaner[0];$('note').value='';$('auditNote').textContent='';$('deleteBtn').style.visibility='hidden';setFormEnabled(true);$('appointmentDialog').showModal()
}
function openEdit(id){
  const a=appointments.find(x=>x.id===id);if(!a)return;
  $('dialogTitle').textContent=canEdit()?'Werkstatttermin bearbeiten':'Werkstatttermin';$('apptId').value=a.id;$('apptDate').value=a.date;$('resource').value=a.resource;$('startTime').value=a.start;$('endTime').value=a.end;$('plate').value=a.plate;$('vehicle').value=a.vehicle||'';$('customer').value=a.customer||'';$('phone').value=a.phone||'';$('mechanic').value=a.mechanic||config.mechanics[0];$('status').value=a.status;$('job').value=a.job||'';$('parts').value=a.parts||config.parts[0];$('loaner').value=a.loaner||config.loaner[0];$('note').value=a.note||'';$('auditNote').textContent=a.updated_by_name?'Zuletzt geändert von '+a.updated_by_name+' · '+(a.updated_at||''):'';$('deleteBtn').style.visibility=canEdit()?'visible':'hidden';setFormEnabled(canEdit());$('appointmentDialog').showModal()
}
function setFormEnabled(enabled){[...$('appointmentForm').elements].forEach(el=>{if(el.id==='saveBtn'){el.style.display=enabled?'inline-block':'none';return}if(el.id==='deleteBtn'||el.value==='cancel')return;el.disabled=!enabled})}
function formData(){return{id:$('apptId').value||uuid(),date:$('apptDate').value,resource:$('resource').value,start:$('startTime').value,end:$('endTime').value,plate:$('plate').value.trim(),vehicle:$('vehicle').value.trim(),customer:$('customer').value.trim(),phone:$('phone').value.trim(),mechanic:$('mechanic').value,status:$('status').value,job:$('job').value.trim(),parts:$('parts').value,loaner:$('loaner').value,note:$('note').value.trim()}}
async function saveFromForm(){
  const d=formData();if(mins(d.end)<=mins(d.start)){alert('Endzeit muss nach der Startzeit liegen.');return}
  try{await persist(d,false);$('appointmentDialog').close();$('datePicker').value=d.date;await loadAppointments();toast('Termin gespeichert')}
  catch(err){if(err.status===409&&confirm('Der Arbeitsplatz ist bereits mit '+err.data.conflict.plate+' belegt. Trotzdem speichern?')){await persist(d,true);$('appointmentDialog').close();$('datePicker').value=d.date;await loadAppointments();toast('Termin gespeichert')}else if(err.status!==409)alert(err.message)}
}
async function persist(d,force){const exists=appointments.some(a=>a.id===d.id);await api('/api/appointments'+(exists?'/'+encodeURIComponent(d.id):''),{method:exists?'PUT':'POST',body:JSON.stringify({...d,force})});await loadAppointments()}

async function openUsers(){if(!isAdmin())return;$('usersDialog').showModal();await loadUsers()}
async function loadUsers(){try{const d=await api('/api/users');const list=$('usersList');list.innerHTML='';d.users.forEach(u=>list.appendChild(userRow(u)))}catch(e){toast(e.message)}}
function userRow(u){
  const row=document.createElement('div');row.className='user-row'+(u.active?'':' inactive');
  row.innerHTML='<div class="user-row-head"><div><strong>'+esc(u.name)+'</strong><span class="user-state">'+(u.active?'aktiv':'deaktiviert')+'</span></div><span class="role-chip">'+roleLabel(u.role)+'</span></div><div class="user-edit-grid"><label>Name<input class="u-name" value="'+esc(u.name)+'"></label><label>Rolle<select class="u-role"><option value="viewer">Nur Lesen</option><option value="editor">Bearbeitung</option><option value="admin">Administrator</option></select></label><label>Neues Passwort<input class="u-password" type="password" minlength="10" placeholder="leer = unverändert" autocomplete="new-password"></label><label class="toggle-label"><input class="u-active" type="checkbox"> Konto aktiv</label></div><div class="row-actions"><span class="row-error"></span><button type="button" class="save-user primary">Speichern</button></div>';
  row.querySelector('.u-role').value=u.role;row.querySelector('.u-active').checked=!!u.active;
  row.querySelector('.save-user').onclick=async()=>{
    const payload={name:row.querySelector('.u-name').value.trim(),role:row.querySelector('.u-role').value,active:row.querySelector('.u-active').checked,password:row.querySelector('.u-password').value};
    const err=row.querySelector('.row-error');err.textContent='';
    try{await api('/api/users/'+u.id,{method:'PUT',body:JSON.stringify(payload)});toast('Benutzer gespeichert');await loadUsers();if(u.id===currentUser.id){const me=await api('/api/me');currentUser=me.user;updateRole()}}catch(e){err.textContent=e.message}
  };
  return row;
}
function roleLabel(role){return role==='admin'?'Administrator':role==='editor'?'Bearbeitung':'Nur Lesen'}
async function createUser(e){
  e.preventDefault();$('newUserError').textContent='';
  try{await api('/api/users',{method:'POST',body:JSON.stringify({name:$('newUserName').value.trim(),role:$('newUserRole').value,password:$('newUserPassword').value})});$('newUserForm').reset();$('newUserRole').value='viewer';toast('Benutzer angelegt');await loadUsers()}catch(err){$('newUserError').textContent=err.message}
}
init();
