const START=7*60, END=18*60, STEP=30;
let currentUser=null, appointments=[], config={resources:[],mechanics:[],statuses:[],parts:[],loaner:[]};
let events=null;
let currentView='workshop', personnelPlan=null, personnelImportPreview=null, personnelEmployees=[], personnelSettingsYear=null;
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
  deviceResizeTimer=setTimeout(()=>{applyDeviceProfile();if(currentUser){if(currentView==='personnel')loadPersonnel();else render()}},90);
}

function todayISO(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function mins(t){const p=t.split(':').map(Number);return p[0]*60+p[1]}
function timeLabel(m){return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')}
function modulePerm(module,level='view'){
  if(!currentUser)return false;
  if(currentUser.role==='admin')return true;
  const p=(currentUser.permissions||{})[module]||{};
  return !!p[level];
}
function canEdit(){return modulePerm('werkstattplaner','edit')}
function canViewWorkshop(){return modulePerm('werkstattplaner','view')}
function canViewPersonnel(){return modulePerm('personalplaner','view')}
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
  if($('personnelDate')) $('personnelDate').value=todayISO();
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
  $('refreshUsersBtn').onclick=()=>loadUsers(true);
  $('newUserModeBtn').onclick=showNewUserMode;
  $('cancelNewUserBtn').onclick=()=>selectedUserId?selectUser(selectedUserId):showUserEmpty();
  $('userSearch').oninput=renderUserDirectory;
  $('editUserForm').onsubmit=saveSelectedUser;
  $('resetEditBtn').onclick=()=>selectedUserId&&selectUser(selectedUserId);
  $('newUserForm').onsubmit=createUser;
  $('overviewNavBtn').onclick=()=>showView('workshop','overviewNavBtn');
  $('workshopNavBtn').onclick=()=>showView('workshop','workshopNavBtn');
  $('personnelNavBtn').onclick=()=>{if(canViewPersonnel())showView('personnel','personnelNavBtn')};
  $('personnelPrevBtn').onclick=()=>shiftPersonnel(-1);
  $('personnelNextBtn').onclick=()=>shiftPersonnel(1);
  $('personnelTodayBtn').onclick=()=>{$('personnelDate').value=todayISO();loadPersonnel()};
  $('personnelDate').onchange=loadPersonnel;
  $('personnelRangeMode').onchange=loadPersonnel;
  $('personnelNewBtn').onclick=()=>openPersonnelEntry();
  $('personnelEntryType').onchange=togglePersonnelCustomCode;
  $('personnelEntryForm').onsubmit=savePersonnelEntry;
  $('personnelEntryDeleteBtn').onclick=deletePersonnelEntry;
  $('personnelImportBtn').onclick=openPersonnelImport;
  $('personnelImportShortcut').onclick=openPersonnelImport;
  $('personnelImportCloseBtn').onclick=closePersonnelImport;
  $('personnelImportCancelBtn').onclick=closePersonnelImport;
  $('personnelImportFile').onchange=()=>{$('personnelImportFileName').textContent=$('personnelImportFile').files[0]?.name||'Keine Datei ausgewählt'};
  $('personnelImportForm').onsubmit=previewPersonnelImport;
  $('personnelCommitBtn').onclick=commitPersonnelImport;
  $('employeeManageBtn').onclick=()=>openEmployeeManager();
  $('employeeDialogCloseBtn').onclick=()=>$('employeeDialog').close();
  $('employeeSettingsYearPrevBtn').onclick=()=>shiftEmployeeSettingsYear(-1);
  $('employeeSettingsYearNextBtn').onclick=()=>shiftEmployeeSettingsYear(1);
  $('employeeSettingsYearTodayBtn').onclick=()=>setEmployeeSettingsYear(new Date().getFullYear());
  $('employeeSettingsYear').onchange=()=>setEmployeeSettingsYear($('employeeSettingsYear').value);
  $('newEmployeeForm').onsubmit=createEmployee;
  window.addEventListener('online',()=>setOnline(true));
  window.addEventListener('offline',()=>setOnline(false));
  window.addEventListener('resize',scheduleDeviceProfile,{passive:true});
  window.addEventListener('orientationchange',scheduleDeviceProfile,{passive:true});
}

async function enterApp(){
  config=await api('/api/config');
  fillSelect($('resource'),config.resources);fillSelect($('mechanic'),config.mechanics);fillSelect($('status'),config.statuses);fillSelect($('parts'),config.parts);fillSelect($('loaner'),config.loaner);
  $('legend').innerHTML=config.statuses.map(s=>'<span data-status="'+esc(s)+'">'+esc(s)+'</span>').join('');
  updateRole();showApp();
  if(canViewWorkshop()) showView('workshop','workshopNavBtn',false);
  else if(canViewPersonnel()) showView('personnel','personnelNavBtn',false);
  if(canViewWorkshop()){
    await loadAppointments();connectEvents();
  }else{
    $('planner').innerHTML='<div class="no-access"><strong>Kein Zugriff auf den Werkstattplaner</strong><span>Dein Benutzerkonto ist angemeldet, besitzt aber keine Berechtigung für dieses Modul.</span></div>';
    $('todayCount').textContent='0 Termine';
  }
  setOnline(navigator.onLine);
}
function fillSelect(el,arr){el.innerHTML='';arr.forEach(x=>el.add(new Option(x,x)))}
function updateRole(){
  $('currentUser').textContent=currentUser.name;
  $('roleBadge').textContent=currentUser.role==='admin'?'Administrator':currentUser.role==='editor'?'Bearbeitung':'Nur Lesen';
  $('newBtn').disabled=!canEdit();
  $('usersBtn').classList.toggle('hidden',!isAdmin());
  document.body.dataset.workshopAccess=canViewWorkshop()?'1':'0';
  document.body.dataset.personnelAccess=canViewPersonnel()?'1':'0';
  $('personnelNavBtn').classList.toggle('hidden',!canViewPersonnel());
  $('personnelNewBtn').disabled=!modulePerm('personalplaner','edit');
  $('employeeManageBtn').classList.toggle('hidden',!modulePerm('personalplaner','manage'));
  $('personnelImportBtn').classList.toggle('hidden',!modulePerm('personalplaner','manage'));
  $('personnelImportShortcut').classList.toggle('hidden',!modulePerm('personalplaner','manage'));
}
function setOnline(ok){$('syncDot').classList.toggle('offline',!ok);$('syncDot').title=ok?'Server verbunden':'Offline'}
function connectEvents(){
  if(events)events.close();
  events=new EventSource('/api/events');
  events.onopen=()=>setOnline(true);events.onerror=()=>setOnline(false);
  events.addEventListener('appointments-changed',()=>{if(currentView==='workshop'&&canViewWorkshop())loadAppointments()});
  events.addEventListener('personnel-changed',()=>{if(currentView==='personnel'&&canViewPersonnel())loadPersonnel()});
}
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

let usersCache=[];
let selectedUserId=null;

async function openUsers(){
  if(!isAdmin())return;
  $('usersDialog').showModal();
  await loadUsers(true);
}
async function loadUsers(preserveSelection=false){
  try{
    const d=await api('/api/users');
    usersCache=Array.isArray(d.users)?d.users:[];
    $('usersCount').textContent=usersCache.length+' '+(usersCache.length===1?'Benutzerkonto':'Benutzerkonten');
    renderUserDirectory();
    if(preserveSelection&&selectedUserId&&usersCache.some(u=>u.id===selectedUserId)){
      selectUser(selectedUserId);
    }else if(usersCache.length){
      const preferred=usersCache.find(u=>u.id!==currentUser.id)||usersCache[0];
      selectUser(preferred.id);
    }else{
      showUserEmpty();
    }
  }catch(e){toast(e.message)}
}
function renderUserDirectory(){
  const list=$('usersList');
  const q=($('userSearch').value||'').trim().toLowerCase();
  list.innerHTML='';
  usersCache
    .filter(u=>!q||u.name.toLowerCase().includes(q)||roleLabel(u.role).toLowerCase().includes(q))
    .forEach(u=>{
      const btn=document.createElement('button');
      btn.type='button';
      btn.className='account-list-item'+(u.id===selectedUserId?' active':'')+(u.active?'':' inactive');
      btn.dataset.userId=u.id;
      btn.innerHTML=
        '<span class="account-avatar">'+esc((u.name||'?').slice(0,1).toUpperCase())+'</span>'+
        '<span class="account-list-copy"><strong>'+esc(u.name)+'</strong><small>'+esc(roleLabel(u.role))+(u.id===currentUser.id?' · Du':'')+'</small></span>'+
        '<span class="account-status-dot '+(u.active?'on':'off')+'" title="'+(u.active?'Aktiv':'Deaktiviert')+'"></span>';
      btn.onclick=()=>selectUser(u.id);
      list.appendChild(btn);
    });
}
function showUserEmpty(){
  selectedUserId=null;
  $('userEditor').classList.add('hidden');
  $('newUserPanel').classList.add('hidden');
  $('userEmptyState').classList.remove('hidden');
  renderUserDirectory();
}
function showNewUserMode(){
  selectedUserId=null;
  $('userEmptyState').classList.add('hidden');
  $('userEditor').classList.add('hidden');
  $('newUserPanel').classList.remove('hidden');
  $('newUserError').textContent='';
  $('newUserForm').reset();
  $('newUserRole').value='viewer';
  $('newWView').checked=true;$('newPView').checked=true;
  $('newWEdit').checked=$('newWManage').checked=$('newPEdit').checked=$('newPManage').checked=false;
  renderUserDirectory();
  setTimeout(()=>$('newUserName').focus(),0);
}
function setCheckbox(id,value){$(id).checked=!!value}
function selectUser(id){
  const u=usersCache.find(x=>x.id===Number(id)||x.id===id);
  if(!u)return;
  selectedUserId=u.id;
  $('userEmptyState').classList.add('hidden');
  $('newUserPanel').classList.add('hidden');
  $('userEditor').classList.remove('hidden');
  $('editUserId').value=u.id;
  $('editUserTitle').textContent=u.name;
  $('editUserState').textContent=u.active?'aktiv':'deaktiviert';
  $('editUserState').className='user-state '+(u.active?'active':'inactive');
  $('editUserName').value=u.name;
  $('editUserRole').value=u.role;
  $('editUserActive').checked=!!u.active;
  const wp=(u.permissions||{}).werkstattplaner||{};
  const pp=(u.permissions||{}).personalplaner||{};
  setCheckbox('editWView',wp.view);setCheckbox('editWEdit',wp.edit);setCheckbox('editWManage',wp.manage);
  setCheckbox('editPView',pp.view);setCheckbox('editPEdit',pp.edit);setCheckbox('editPManage',pp.manage);
  $('editUserPassword').value='';$('editUserPassword2').value='';
  $('editUserError').textContent='';
  applyEditRoleLock();
  renderUserDirectory();
}
function normalizePerm(viewId,editId,manageId){
  const manage=$(manageId).checked;
  const edit=$(editId).checked||manage;
  const view=$(viewId).checked||edit||manage;
  return {view,edit,manage};
}
function syncPermGroup(viewId,editId,manageId){
  const v=$(viewId),e=$(editId),m=$(manageId);
  const sync=()=>{
    if(m.checked){e.checked=true;v.checked=true}
    if(e.checked)v.checked=true;
    if(!v.checked){e.checked=false;m.checked=false}
    if(!e.checked)m.checked=false;
  };
  v.onchange=sync;e.onchange=sync;m.onchange=sync;
}
function applyEditRoleLock(){
  const admin=$('editUserRole').value==='admin';
  ['editWView','editWEdit','editWManage','editPView','editPEdit','editPManage'].forEach(id=>{
    $(id).disabled=admin;
    if(admin)$(id).checked=true;
  });
}
async function saveSelectedUser(e){
  e.preventDefault();
  const id=Number($('editUserId').value);
  const role=$('editUserRole').value;
  const p1=$('editUserPassword').value,p2=$('editUserPassword2').value;
  const err=$('editUserError');err.textContent='';
  if(p1!==p2){err.textContent='Passwörter stimmen nicht überein';return}
  const permissions=role==='admin'
    ? {werkstattplaner:{view:true,edit:true,manage:true},personalplaner:{view:true,edit:true,manage:true}}
    : {
        werkstattplaner:normalizePerm('editWView','editWEdit','editWManage'),
        personalplaner:normalizePerm('editPView','editPEdit','editPManage')
      };
  const payload={
    name:$('editUserName').value.trim(),
    role,
    active:$('editUserActive').checked,
    password:p1,
    password_confirm:p2,
    permissions
  };
  try{
    await api('/api/users/'+id,{method:'PUT',body:JSON.stringify(payload)});
    toast('Benutzerkonto gespeichert');
    if(id===currentUser.id){const me=await api('/api/me');currentUser=me.user;updateRole()}
    await loadUsers(true);
  }catch(ex){err.textContent=ex.message}
}
function roleLabel(role){
  return role==='admin'?'Systemadministrator':role==='editor'?'Bearbeiter':'Mitarbeiter';
}
function newUserPermissions(){
  const role=$('newUserRole').value;
  if(role==='admin')return {werkstattplaner:{view:true,edit:true,manage:true},personalplaner:{view:true,edit:true,manage:true}};
  return {
    werkstattplaner:normalizePerm('newWView','newWEdit','newWManage'),
    personalplaner:normalizePerm('newPView','newPEdit','newPManage')
  };
}
async function createUser(e){
  e.preventDefault();
  $('newUserError').textContent='';
  const p1=$('newUserPassword').value,p2=$('newUserPassword2').value;
  if(p1!==p2){$('newUserError').textContent='Passwörter stimmen nicht überein';return}
  try{
    const d=await api('/api/users',{method:'POST',body:JSON.stringify({
      name:$('newUserName').value.trim(),
      role:$('newUserRole').value,
      password:p1,password_confirm:p2,
      permissions:newUserPermissions()
    })});
    toast('Benutzerkonto angelegt');
    await loadUsers(false);
    const created=usersCache.find(u=>u.id===d.id);
    if(created)selectUser(created.id);
  }catch(err){$('newUserError').textContent=err.message}
}

syncPermGroup('editWView','editWEdit','editWManage');
syncPermGroup('editPView','editPEdit','editPManage');
syncPermGroup('newWView','newWEdit','newWManage');
syncPermGroup('newPView','newPEdit','newPManage');
$('editUserRole').onchange=applyEditRoleLock;
$('newUserRole').onchange=()=>{
  const role=$('newUserRole').value;
  const ids=['newWView','newWEdit','newWManage','newPView','newPEdit','newPManage'];
  ids.forEach(id=>$(id).disabled=role==='admin');
  if(role==='admin')ids.forEach(id=>$(id).checked=true);
};


function dateFromIso(value){const [y,m,d]=String(value||todayISO()).split('-').map(Number);return new Date(y,m-1,d,12)}
function isoFromDate(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function addDays(d,n){const x=new Date(d);x.setDate(x.getDate()+n);return x}
function canPersonnelEdit(){return modulePerm('personalplaner','edit')}
function canPersonnelManage(){return modulePerm('personalplaner','manage')}
function personnelMode(){const v=$('personnelRangeMode').value;return v!=='auto'?v:(document.documentElement.dataset.device==='phone'?'week':'month')}
function personnelRange(){
  const selected=dateFromIso($('personnelDate').value||todayISO());
  if(personnelMode()==='week'){
    const monday=new Date(selected);monday.setDate(selected.getDate()-((selected.getDay()+6)%7));
    return {start:isoFromDate(monday),end:isoFromDate(addDays(monday,6)),year:selected.getFullYear(),mode:'week'};
  }
  const first=new Date(selected.getFullYear(),selected.getMonth(),1,12),last=new Date(selected.getFullYear(),selected.getMonth()+1,0,12);
  return {start:isoFromDate(first),end:isoFromDate(last),year:selected.getFullYear(),mode:'month'};
}
function showView(view,navId,load=true){
  currentView=view;
  $('workshopView').classList.toggle('hidden',view!=='workshop');
  $('personnelView').classList.toggle('hidden',view!=='personnel');
  ['overviewNavBtn','workshopNavBtn','personnelNavBtn'].forEach(id=>$(id).classList.toggle('active',id===navId));
  if(load&&view==='personnel')loadPersonnel();
}
function shiftPersonnel(direction){
  const d=dateFromIso($('personnelDate').value||todayISO());
  if(personnelMode()==='month'){d.setDate(1);d.setMonth(d.getMonth()+direction)}else d.setDate(d.getDate()+direction*7);
  $('personnelDate').value=isoFromDate(d);loadPersonnel();
}
function formatDays(v){const n=Number(v||0);return n.toLocaleString('de-DE',{minimumFractionDigits:Number.isInteger(n)?0:1,maximumFractionDigits:1})+' T'}
async function loadPersonnel(){
  if(!currentUser||!canViewPersonnel())return;
  const range=personnelRange();
  $('personnelGrid').innerHTML='<div class="personnel-loading">Personalplan wird geladen …</div>';
  try{personnelPlan=await api('/api/personnel/plan?start='+encodeURIComponent(range.start)+'&end='+encodeURIComponent(range.end)+'&year='+range.year);renderPersonnel(range)}
  catch(e){$('personnelGrid').innerHTML='<div class="personnel-empty"><strong>Personalplan konnte nicht geladen werden.</strong><span>'+esc(e.message)+'</span></div>'}
}
function renderPersonnel(range){
  const plan=personnelPlan;if(!plan)return;
  const days=[];for(let d=dateFromIso(range.start),end=dateFromIso(range.end);d<=end;d=addDays(d,1))days.push(isoFromDate(d));
  const holidayMap=new Map((plan.holidays||[]).map(x=>[x.date,x]));
  const entryMap=new Map((plan.entries||[]).map(x=>[x.employee_id+'|'+x.date,x]));
  const start=dateFromIso(range.start),end=dateFromIso(range.end);
  $('personnelRangeLabel').textContent=range.mode==='week'
    ?'Woche '+start.toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'})+' – '+end.toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric'})
    :start.toLocaleDateString('de-DE',{month:'long',year:'numeric'});
  $('personnelEmployeeCount').textContent=plan.employees.length;
  $('personnelVacationCount').textContent=formatDays(plan.employees.reduce((s,x)=>s+Number(x.vacation_used||0),0));
  $('personnelVacationYear').textContent='im Jahr '+plan.year;
  $('personnelSickCount').textContent=formatDays(plan.employees.reduce((s,x)=>s+Number(x.sick_days||0),0));
  $('personnelLegend').innerHTML='<span class="category-vacation">U Urlaub</span><span class="category-sick">K Krank</span><span class="category-work">A Arbeit</span><span class="category-individual">I Individuell</span><span class="category-custom">… Sonstiges</span>';
  $('personnelHolidayList').innerHTML=plan.holidays.length?plan.holidays.map(x=>'<div><time>'+dateFromIso(x.date).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'})+'</time><span>'+esc(x.name)+'</span></div>').join(''):'<p class="muted-copy">Keine Feiertage im Zeitraum.</p>';
  $('personnelImportStatus').textContent=plan.last_import?'Letzter Import: '+plan.last_import.filename:'Noch kein Excel-Import';
  const wrap=$('personnelGrid');wrap.innerHTML='';
  if(!plan.employees.length){wrap.innerHTML='<div class="personnel-empty"><strong>Noch keine Mitarbeiter vorhanden.</strong><span>Über Personal-Einstellungen anlegen oder die Excel-Datei importieren.</span></div>';return}
  const table=document.createElement('div');table.className='personnel-table';table.style.gridTemplateColumns='minmax(var(--person-name-col),var(--person-name-col)) repeat('+days.length+',minmax(var(--person-day-col),var(--person-day-col)))';
  const corner=document.createElement('div');corner.className='personnel-name-cell personnel-corner';corner.innerHTML='<strong>Mitarbeiter</strong><small>Urlaub '+plan.year+'</small>';table.appendChild(corner);
  days.forEach(day=>{
    const d=dateFromIso(day),holiday=holidayMap.get(day),weekend=[0,6].includes(d.getDay());
    const h=document.createElement('div');h.className='personnel-day-head'+(weekend?' weekend':'')+(holiday?' holiday':'');
    h.innerHTML='<span>'+d.toLocaleDateString('de-DE',{weekday:'short'}).replace('.','')+'</span><strong>'+d.getDate()+'</strong>'+(holiday?'<small>'+esc(holiday.name)+'</small>':'');table.appendChild(h);
  });
  plan.employees.forEach(emp=>{
    const name=document.createElement('button');name.type='button';name.className='personnel-name-cell personnel-name-button';
    name.innerHTML='<strong>'+esc(emp.name)+'</strong><small>'+formatDays(emp.vacation_used)+' / '+formatDays(emp.vacation_total)+' · Rest '+formatDays(emp.vacation_remaining)+'</small>';
    if(canPersonnelManage())name.onclick=()=>openEmployeeManager(emp.id);else name.disabled=true;
    table.appendChild(name);
    days.forEach(day=>{
      const d=dateFromIso(day),entry=entryMap.get(emp.id+'|'+day),holiday=holidayMap.get(day),weekend=[0,6].includes(d.getDay());
      const cell=document.createElement('button');cell.type='button';cell.className='personnel-entry-cell'+(weekend?' weekend':'')+(holiday?' holiday':'')+(entry?' has-entry category-'+entry.category:'');
      if(entry){cell.innerHTML='<span>'+esc(entry.code)+'</span>'+(Number(entry.portion)===0.5?'<small>½</small>':'');cell.title=entry.label+(entry.note?' · '+entry.note:'')}
      else if(holiday){cell.innerHTML='<i>•</i>';cell.title=holiday.name}
      if(canPersonnelEdit())cell.onclick=()=>openPersonnelEntry(emp.id,day,entry||null);else cell.disabled=true;
      table.appendChild(cell);
    });
  });
  wrap.appendChild(table);
}
function togglePersonnelCustomCode(){$('personnelCustomCodeWrap').classList.toggle('hidden',$('personnelEntryType').value!=='CUSTOM')}
function openPersonnelEntry(employeeId=null,day=null,entry=null){
  if(!canPersonnelEdit())return;
  const employees=personnelPlan?.employees||[];
  $('personnelEmployee').innerHTML='';employees.forEach(x=>$('personnelEmployee').add(new Option(x.name,x.id)));
  $('personnelEntryId').value=entry?.id||'';
  $('personnelEmployee').value=String(employeeId||employees[0]?.id||'');
  $('personnelEntryDate').value=day||$('personnelDate').value||todayISO();
  $('personnelEntryEndDate').value='';
  $('personnelEntryEndDate').disabled=!!entry;
  const code=entry?.category==='custom'?'CUSTOM':(entry?.code||'U');
  $('personnelEntryType').value=[...$('personnelEntryType').options].some(o=>o.value===code)?code:'CUSTOM';
  $('personnelEntryPortion').value=String(entry?.portion||1);
  $('personnelCustomCode').value=entry?.category==='custom'?entry.code:'';
  $('personnelEntryNote').value=entry?.note||'';
  $('personnelEntryDeleteBtn').classList.toggle('hidden',!entry);
  $('personnelEntryMeta').textContent=entry?(entry.source==='excel'?'Aus Excel importiert · Änderungen werden manuell geschützt':'Manueller Eintrag'):'Von–Bis ist möglich; ohne Bis wird nur ein Tag eingetragen.';
  togglePersonnelCustomCode();$('personnelEntryDialog').showModal();
}
async function savePersonnelEntry(e){
  e.preventDefault();if(!canPersonnelEdit())return;
  const id=$('personnelEntryId').value;
  const payload={
    employee_id:Number($('personnelEmployee').value),date:$('personnelEntryDate').value,
    end_date:id?'':$('personnelEntryEndDate').value,code:$('personnelEntryType').value,
    custom_code:$('personnelCustomCode').value,portion:Number($('personnelEntryPortion').value),
    note:$('personnelEntryNote').value
  };
  try{await api('/api/personnel/entries'+(id?'/'+id:''),{method:id?'PUT':'POST',body:JSON.stringify(payload)});$('personnelEntryDialog').close();await loadPersonnel();toast('Personaleintrag gespeichert')}
  catch(err){alert(err.message)}
}
async function deletePersonnelEntry(){
  const id=$('personnelEntryId').value;if(!id||!canPersonnelEdit()||!confirm('Personaleintrag wirklich löschen?'))return;
  try{await api('/api/personnel/entries/'+id,{method:'DELETE'});$('personnelEntryDialog').close();await loadPersonnel();toast('Personaleintrag gelöscht')}catch(e){alert(e.message)}
}
function openPersonnelImport(){
  if(!canPersonnelManage())return;
  personnelImportPreview=null;$('personnelImportForm').reset();$('personnelImportFileName').textContent='Keine Datei ausgewählt';$('personnelImportPreview').innerHTML='';$('personnelImportPreview').classList.add('hidden');$('personnelCommitBtn').disabled=true;$('personnelImportError').textContent='';$('personnelImportDialog').showModal()
}
function closePersonnelImport(){$('personnelImportDialog').close()}
async function previewPersonnelImport(e){
  e.preventDefault();const file=$('personnelImportFile').files[0];if(!file)return;
  const fd=new FormData();fd.append('file',file);
  $('personnelImportError').textContent='';$('personnelPreviewBtn').disabled=true;
  try{const r=await api('/api/personnel/import/preview',{method:'POST',body:fd});personnelImportPreview=r.preview;renderImportPreview(r.preview);$('personnelCommitBtn').disabled=false}
  catch(err){$('personnelImportError').textContent=err.message}
  finally{$('personnelPreviewBtn').disabled=false}
}
function renderImportPreview(p){
  const el=$('personnelImportPreview');el.classList.remove('hidden');
  el.innerHTML='<h3>Import-Vorschau '+esc(String(p.year))+'</h3><div class="import-stats"><span><strong>'+p.employee_count+'</strong>Mitarbeiter</span><span><strong>'+p.entry_count+'</strong>Einträge</span><span><strong>'+p.manual_conflicts+'</strong>manuelle Konflikte</span></div>'+
    (p.warnings?.length?'<ul>'+p.warnings.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'<p>Keine Warnungen.</p>');
}
async function commitPersonnelImport(){
  if(!personnelImportPreview||!canPersonnelManage())return;
  $('personnelCommitBtn').disabled=true;
  try{const r=await api('/api/personnel/import/commit',{method:'POST',body:JSON.stringify({import_id:personnelImportPreview.id})});closePersonnelImport();toast(r.inserted+' Einträge importiert');await loadPersonnel()}
  catch(e){$('personnelImportError').textContent=e.message;$('personnelCommitBtn').disabled=false}
}
async function openEmployeeManager(employeeId=null){
  if(!canPersonnelManage())return;
  personnelSettingsYear=personnelPlan?.year||dateFromIso($('personnelDate').value||todayISO()).getFullYear();
  $('employeeSettingsYear').value=personnelSettingsYear;$('employeeDialog').showModal();$('employeeError').textContent='';
  await loadEmployeeManager(employeeId);
}
function setEmployeeSettingsYear(value){
  const y=Math.round(Number(value));if(!Number.isFinite(y)||y<2000||y>2100){$('employeeError').textContent='Planungsjahr muss zwischen 2000 und 2100 liegen';return}
  personnelSettingsYear=y;$('employeeSettingsYear').value=y;loadEmployeeManager()
}
function shiftEmployeeSettingsYear(delta){setEmployeeSettingsYear((personnelSettingsYear||new Date().getFullYear())+delta)}
async function loadEmployeeManager(focusId=null){
  const year=personnelSettingsYear||new Date().getFullYear();
  try{const r=await api('/api/personnel/employees?year='+year);personnelEmployees=r.employees;renderEmployeeManager(year,focusId)}catch(e){$('employeeError').textContent=e.message}
}
function renderEmployeeManager(year,focusId=null){
  $('employeeSettingsSummary').textContent=personnelEmployees.filter(x=>x.active).length+' aktiv · '+personnelEmployees.length+' gesamt · '+year;
  const list=$('employeeList');list.innerHTML='';
  if(!personnelEmployees.length){list.innerHTML='<div class="personnel-empty">Noch keine Mitarbeiter vorhanden.</div>';return}
  personnelEmployees.forEach(emp=>{
    const row=document.createElement('div');row.className='employee-row'+(emp.active?'':' inactive');
    row.innerHTML='<div class="employee-row-title"><strong>'+esc(emp.name)+'</strong><span>'+formatDays(emp.vacation_remaining)+' verfügbar</span></div>'+
      '<div class="employee-edit-grid"><label>Name<input class="e-name" value="'+esc(emp.name)+'"></label><label>Urlaub/Jahr<input class="e-annual" type="number" step=".5" value="'+Number(emp.annual_vacation||0)+'"></label><label>Rest Vorjahr<input class="e-carry" type="number" step=".5" value="'+Number(emp.carryover_vacation||0)+'"></label><label>Sortierung<input class="e-sort" type="number" value="'+Number(emp.sort_order||0)+'"></label><label class="toggle-label"><input class="e-active" type="checkbox" '+(emp.active?'checked':'')+'> aktiv</label></div>'+
      '<div class="row-actions"><span class="row-error"></span><button class="primary e-save" type="button">Speichern</button></div>';
    row.querySelector('.e-save').onclick=async()=>{
      const payload={name:row.querySelector('.e-name').value.trim(),annual_vacation:Number(row.querySelector('.e-annual').value||0),carryover_vacation:Number(row.querySelector('.e-carry').value||0),sort_order:Number(row.querySelector('.e-sort').value||0),active:row.querySelector('.e-active').checked,year};
      try{await api('/api/personnel/employees/'+emp.id,{method:'PUT',body:JSON.stringify(payload)});toast('Personal-Einstellungen gespeichert');await loadEmployeeManager(emp.id);await loadPersonnel()}catch(e){row.querySelector('.row-error').textContent=e.message}
    };
    list.appendChild(row);
    if(Number(focusId)===Number(emp.id))setTimeout(()=>row.scrollIntoView({block:'center'}),0);
  });
}
async function createEmployee(e){
  e.preventDefault();const year=personnelSettingsYear||new Date().getFullYear();
  const payload={name:$('newEmployeeName').value.trim(),annual_vacation:Number($('newEmployeeAnnual').value||0),carryover_vacation:Number($('newEmployeeCarry').value||0),sort_order:Number($('newEmployeeSort').value||personnelEmployees.length+1),active:true,year};
  try{const r=await api('/api/personnel/employees',{method:'POST',body:JSON.stringify(payload)});$('newEmployeeForm').reset();$('newEmployeeAnnual').value='30';$('newEmployeeCarry').value='0';toast('Mitarbeiter angelegt');await loadEmployeeManager(r.id);await loadPersonnel()}catch(e){$('employeeError').textContent=e.message}
}

init();
