const START=7*60, END=18*60, STEP=30;
let currentUser=null, appointments=[], config={resources:[],mechanics:[],statuses:[],parts:[],loaner:[]};
let events=null;
const $=id=>document.getElementById(id);
function todayISO(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
function mins(t){const [h,m]=t.split(':').map(Number);return h*60+m}
function timeLabel(m){return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')}
function canEdit(){return currentUser&&['admin','editor'].includes(currentUser.role)}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}
function uuid(){return crypto.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random().toString(16).slice(2)}`}
function toast(msg){$('toast').textContent=msg;$('toast').classList.remove('hidden');setTimeout(()=>$('toast').classList.add('hidden'),2600)}
async function api(url,opts={}){
 const r=await fetch(url,{...opts,headers:{'Content-Type':'application/json',...(opts.headers||{})}});
 let data={}; try{data=await r.json()}catch{}
 if(r.status===401){showLogin();throw new Error('Sitzung abgelaufen')}
 if(!r.ok){const e=new Error(data.error||`HTTP ${r.status}`);e.status=r.status;e.data=data;throw e}
 return data;
}
function showLogin(){$('loginScreen').classList.remove('hidden');$('appShell').classList.add('hidden')}
function showApp(){$('loginScreen').classList.add('hidden');$('appShell').classList.remove('hidden')}
async function init(){
 $('datePicker').value=todayISO(); bind();
 try{const me=await api('/api/me');currentUser=me.user;await enterApp()}catch{showLogin()}
 if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
}
function bind(){
 $('loginForm').onsubmit=async e=>{e.preventDefault();$('loginError').textContent='';try{const d=await api('/api/login',{method:'POST',body:JSON.stringify({name:$('loginName').value,password:$('loginPassword').value})});currentUser=d.user;$('loginPassword').value='';await enterApp()}catch(err){$('loginError').textContent=err.message}};
 $('logoutBtn').onclick=async()=>{try{await api('/api/logout',{method:'POST'})}catch{};currentUser=null;if(events)events.close();showLogin()};
 $('todayBtn').onclick=()=>{$('datePicker').value=todayISO();loadAppointments()};
 $('prevBtn').onclick=()=>shiftDate(-1);$('nextBtn').onclick=()=>shiftDate(1);$('datePicker').onchange=loadAppointments;
 $('newBtn').onclick=()=>openNew();
 $('appointmentForm').addEventListener('submit',async e=>{e.preventDefault();if(!canEdit())return;await saveFromForm()});
 $('deleteBtn').onclick=async()=>{if(!canEdit())return;const id=$('apptId').value;if(id&&confirm('Termin wirklich löschen?')){try{await api('/api/appointments/'+encodeURIComponent(id),{method:'DELETE'});$('appointmentDialog').close();await loadAppointments();toast('Termin gelöscht')}catch(e){alert(e.message)}}};
 window.addEventListener('online',()=>setOnline(true));window.addEventListener('offline',()=>setOnline(false));
}
async function enterApp(){
 config=await api('/api/config');fillSelect($('resource'),config.resources);fillSelect($('mechanic'),config.mechanics);fillSelect($('status'),config.statuses);fillSelect($('parts'),config.parts);fillSelect($('loaner'),config.loaner);
 $('legend').innerHTML=config.statuses.map(s=>`<span>${esc(s)}</span>`).join('');
 updateRole();showApp();await loadAppointments();connectEvents();setOnline(navigator.onLine);
}
function fillSelect(el,arr){el.innerHTML='';arr.forEach(x=>el.add(new Option(x,x)))}
function updateRole(){
 $('currentUser').textContent=currentUser.name;
 const txt=currentUser.role==='admin'?'Administrator – Termine + Freigaben':currentUser.role==='editor'?'Bearbeitung – Termine anlegen/ändern/verschieben':'Nur Lesen';
 $('roleBadge').textContent=`${currentUser.name}: ${txt}`;$('newBtn').disabled=!canEdit();
}
function setOnline(ok){$('syncDot').classList.toggle('offline',!ok);$('syncDot').title=ok?'Server verbunden':'Offline'}
function connectEvents(){if(events)events.close();events=new EventSource('/api/events');events.onopen=()=>setOnline(true);events.onerror=()=>setOnline(false);events.addEventListener('appointments-changed',e=>{try{const d=JSON.parse(e.data);const current=$('datePicker').value;if(d.date===current||d.oldDate===current)loadAppointments()}catch{}})}
function shiftDate(days){let d=new Date($('datePicker').value+'T12:00:00');d.setDate(d.getDate()+days);$('datePicker').value=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;loadAppointments()}
async function loadAppointments(){try{const d=await api('/api/appointments?date='+encodeURIComponent($('datePicker').value));appointments=d.appointments;render()}catch(e){console.error(e)}}
function render(){
 const p=$('planner');p.innerHTML='<div class="corner">Zeit</div>'+config.resources.map(r=>`<div class="resource-head">${esc(r)}</div>`).join('');
 for(let t=START;t<END;t+=STEP){const time=document.createElement('div');time.className='time-cell';time.textContent=timeLabel(t);p.appendChild(time);config.resources.forEach(r=>{const s=document.createElement('div');s.className='slot';s.dataset.resource=r;s.dataset.time=timeLabel(t);if(canEdit()){s.addEventListener('dblclick',()=>openNew(r,timeLabel(t)));s.addEventListener('dragover',e=>e.preventDefault());s.addEventListener('drop',e=>dropAppt(e,r,timeLabel(t)))}p.appendChild(s)})}
 drawAppointments();drawNowLine();
}
function drawAppointments(){
 const p=$('planner');appointments.forEach(a=>{const col=config.resources.indexOf(a.resource)+2;if(col<2)return;const sm=mins(a.start),em=mins(a.end);if(em<=START||sm>=END)return;const row=2+Math.floor((sm-START)/STEP);const topOffset=((sm-START)%STEP)/STEP*34;const dur=(em-sm)/STEP*34;const card=document.createElement('div');card.className='appointment'+(canEdit()?'':' readonly');card.dataset.status=a.status;card.draggable=canEdit();card.style.gridColumn=String(col);card.style.gridRow=String(row);card.style.height=Math.max(28,dur-5)+'px';card.style.marginTop=topOffset+'px';card.innerHTML=`<strong>${esc(a.plate)} · ${esc(a.vehicle||'')}</strong><div>${esc(a.job||'')}</div><div class="meta">${a.start}–${a.end}${a.mechanic&&a.mechanic!=='—'?' · '+esc(a.mechanic):''}</div>`;card.onclick=()=>openEdit(a.id);card.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',a.id));p.appendChild(card)})
}
function drawNowLine(){const date=$('datePicker').value;if(date!==todayISO())return;const now=new Date(),m=now.getHours()*60+now.getMinutes();if(m<START||m>END)return;const p=$('planner'),line=document.createElement('div');line.className='now-line';line.style.left='72px';line.style.right='0';line.style.top=(54+(m-START)/STEP*34)+'px';p.appendChild(line)}
async function dropAppt(e,resource,start){if(!canEdit())return;const id=e.dataTransfer.getData('text/plain'),a=appointments.find(x=>x.id===id);if(!a)return;const duration=mins(a.end)-mins(a.start),s=mins(start),en=Math.min(END,s+duration);const data={...a,resource,start:timeLabel(s),end:timeLabel(en)};try{await persist(data,false);toast('Termin verschoben')}catch(err){if(err.status===409&&confirm(`Arbeitsplatz ist bereits mit ${err.data.conflict.plate} belegt. Trotzdem verschieben?`)){await persist(data,true)}else if(err.status!==409)alert(err.message)}}
function openNew(resource='Bühne 1',start='08:00'){if(!canEdit())return;const end=timeLabel(Math.min(END,mins(start)+60));$('dialogTitle').textContent='Neuer Werkstatttermin';$('apptId').value='';$('apptDate').value=$('datePicker').value;$('resource').value=resource;$('startTime').value=start;$('endTime').value=end;$('plate').value='';$('vehicle').value='';$('customer').value='';$('phone').value='';$('mechanic').value=config.mechanics[0];$('status').value=config.statuses[0];$('job').value='';$('parts').value=config.parts[0];$('loaner').value=config.loaner[0];$('note').value='';$('auditNote').textContent='';$('deleteBtn').style.visibility='hidden';setFormEnabled(true);$('appointmentDialog').showModal()}
function openEdit(id){const a=appointments.find(x=>x.id===id);if(!a)return;$('dialogTitle').textContent=canEdit()?'Werkstatttermin bearbeiten':'Werkstatttermin';$('apptId').value=a.id;$('apptDate').value=a.date;$('resource').value=a.resource;$('startTime').value=a.start;$('endTime').value=a.end;$('plate').value=a.plate;$('vehicle').value=a.vehicle||'';$('customer').value=a.customer||'';$('phone').value=a.phone||'';$('mechanic').value=a.mechanic||config.mechanics[0];$('status').value=a.status;$('job').value=a.job||'';$('parts').value=a.parts||config.parts[0];$('loaner').value=a.loaner||config.loaner[0];$('note').value=a.note||'';$('auditNote').textContent=a.updated_by_name?`Zuletzt geändert von ${a.updated_by_name} · ${a.updated_at||''}`:'';$('deleteBtn').style.visibility=canEdit()?'visible':'hidden';setFormEnabled(canEdit());$('appointmentDialog').showModal()}
function setFormEnabled(enabled){[...$('appointmentForm').elements].forEach(el=>{if(el.id==='saveBtn'){el.style.display=enabled?'inline-block':'none';return}if(el.id==='deleteBtn'||el.value==='cancel')return;el.disabled=!enabled})}
function formData(){return{id:$('apptId').value||uuid(),date:$('apptDate').value,resource:$('resource').value,start:$('startTime').value,end:$('endTime').value,plate:$('plate').value.trim(),vehicle:$('vehicle').value.trim(),customer:$('customer').value.trim(),phone:$('phone').value.trim(),mechanic:$('mechanic').value,status:$('status').value,job:$('job').value.trim(),parts:$('parts').value,loaner:$('loaner').value,note:$('note').value.trim()}}
async function saveFromForm(){const d=formData();if(mins(d.end)<=mins(d.start)){alert('Endzeit muss nach der Startzeit liegen.');return}try{await persist(d,false);$('appointmentDialog').close();$('datePicker').value=d.date;await loadAppointments();toast('Termin gespeichert')}catch(err){if(err.status===409&&confirm(`Der Arbeitsplatz ist bereits mit ${err.data.conflict.plate} belegt. Trotzdem speichern?`)){await persist(d,true);$('appointmentDialog').close();$('datePicker').value=d.date;await loadAppointments();toast('Termin gespeichert')}else if(err.status!==409)alert(err.message)}}
async function persist(d,force){const exists=appointments.some(a=>a.id===d.id);await api('/api/appointments'+(exists?'/'+encodeURIComponent(d.id):''),{method:exists?'PUT':'POST',body:JSON.stringify({...d,force})});await loadAppointments()}
init();
