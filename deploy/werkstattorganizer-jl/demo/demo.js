const API='/jl/demo/api';
const DEMO_USER='demo', DEMO_PASS='WerkstattDemo!2026';
const $=id=>document.getElementById(id);
const fmtMoney=v=>new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(Number(v||0));
const fmtDate=v=>v?new Intl.DateTimeFormat('de-DE',{dateStyle:'medium'}).format(new Date(v)):'–';
const fmtDateTime=v=>v?new Intl.DateTimeFormat('de-DE',{dateStyle:'short',timeStyle:'short'}).format(new Date(v)):'–';
let token=sessionStorage.getItem('wm_erp_token')||'';
let plannerState={date:new Date(),view:'week',axis:'calendar'};
let personnelPlannerState={date:new Date(),view:'week'};
let state={site:null,sites:[],customers:[],vehicles:[],employees:[],resources:[],appointments:[],orders:[],inventory:[],suppliers:[],purchaseOrders:[],absences:[],tires:[],invoices:[],reminders:[],loaners:[],loanerBookings:[],checklists:[],dashboard:null,report:null,security:null,adminUsers:[],adminRoles:[],permissions:[],selectedOrder:null};

const workStatus={
0:'Entwurf',1:'Geplant',2:'Angekommen',3:'Annahme',4:'Diagnose',5:'Freigabe offen',6:'Freigegeben',
7:'In Arbeit',8:'Qualitätskontrolle',9:'Fertig',10:'Berechnet',11:'Abgeschlossen',12:'Storniert'
};
const appointmentStatus={0:'Angefragt',1:'Bestätigt',2:'Angekommen',3:'Übernommen',4:'Storniert',5:'Nicht erschienen'};
const invoiceStatus={0:'Entwurf',1:'Ausgestellt',2:'Teilbezahlt',3:'Bezahlt',4:'Überfällig',5:'Storniert',6:'Gutgeschrieben'};
const approvalStatus={0:'Offen',1:'Freigegeben',2:'Abgelehnt',3:'Rückruf',4:'Abgelaufen'};
const badge=s=>{
 const x=String(s).toLowerCase();
 if(/fertig|bezahlt|freigegeben|abgeschlossen|vorhanden|aktiv/.test(x))return'success';
 if(/offen|bestellt|geplant|bestätigt|teil/.test(x))return'warn';
 if(/storn|abgelehnt|überfällig|krit/.test(x))return'danger';
 return'info'
};
function toast(msg,err=false){const t=$('toast');t.textContent=msg;t.className='toast'+(err?' error':'');t.classList.remove('hidden');clearTimeout(window.__t);window.__t=setTimeout(()=>t.classList.add('hidden'),3200)}
function showModal(title,html){$('modalTitle').textContent=title;$('modalBody').innerHTML=html;$('modal').classList.remove('hidden')}
function closeModal(){$('modal').classList.add('hidden');$('modalBody').innerHTML=''}
$('modalClose').onclick=closeModal;$('modal').addEventListener('click',e=>{if(e.target===$('modal'))closeModal()});

async function api(path,opts={}){
 const headers={'Content-Type':'application/json',...(opts.headers||{})};
 if(token)headers.Authorization='Bearer '+token;
 const res=await fetch(API+path,{...opts,headers});
 if(res.status===401){sessionStorage.removeItem('wm_erp_token');token='';showLogin();throw new Error('Sitzung abgelaufen')}
 const txt=await res.text();let data=null;try{data=txt?JSON.parse(txt):null}catch{data=txt}
 if(!res.ok){const msg=data?.error||data?.title||('HTTP '+res.status);throw new Error(msg)}
 return data;
}
async function health(){
 try{const h=await api('/health');$('apiState').textContent='ERP API online';$('apiState').className='status-dot ok';$('loginBuild').textContent='ERP 4.0 · API online';return h}
 catch(e){$('apiState').textContent='ERP API nicht erreichbar';$('apiState').className='status-dot bad';$('loginBuild').textContent='ERP 4.0 · API offline';return null}
}
function showLogin(){$('appView').classList.add('hidden');$('loginView').classList.remove('hidden')}
function showApp(){$('loginView').classList.add('hidden');$('appView').classList.remove('hidden')}
async function performLogin(username,password,automatic=false){
 $('loginError').textContent='';
 if($('loginStatus')) $('loginStatus').textContent=automatic?'Staging wird automatisch geöffnet…':'Anmeldung läuft…';
 try{
  const d=await api('/auth/login',{method:'POST',body:JSON.stringify({username,password})});
  token=d.access_token;
  sessionStorage.setItem('wm_erp_token',token);
  showApp();
  await loadAll();
 }catch(err){
  showLogin();
  if($('loginStatus')) $('loginStatus').textContent='Automatische Anmeldung nicht möglich. Bitte Demo-Zugang verwenden.';
  $('loginError').textContent=err.message;
 }
}
$('loginForm').onsubmit=async e=>{
 e.preventDefault();
 await performLogin($('user').value.trim(),$('pass').value);
};
$('demoLoginBtn').onclick=async()=>{
 $('user').value=DEMO_USER;
 $('pass').value=DEMO_PASS;
 await performLogin(DEMO_USER,DEMO_PASS);
};
$('logoutBtn').onclick=()=>{sessionStorage.removeItem('wm_erp_token');token='';location.reload()};
$('refreshBtn').onclick=()=>loadAll(true);
$('menuBtn').onclick=()=>document.querySelector('.sidebar').classList.toggle('open');

function page(name){
 document.querySelectorAll('.page').forEach(x=>x.classList.add('hidden'));
 const el=$(name);if(el)el.classList.remove('hidden');
 document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x.dataset.page===name));
 const btn=document.querySelector('.nav[data-page="'+name+'"]');$('pageTitle').textContent=btn?.textContent||'Workshop Manager';
 document.querySelector('.sidebar').classList.remove('open');
}
document.querySelectorAll('.nav').forEach(b=>b.onclick=()=>page(b.dataset.page));
document.querySelectorAll('[data-page-jump]').forEach(b=>b.onclick=()=>page(b.dataset.pageJump));

async function loadAll(withToast=false){
 try{
  await health();
  const [sites,customers,vehicles,employees,resources,appointments,orders,inventory,suppliers,purchaseOrders,absences,tires,invoices,reminders,loaners,loanerBookings,checklists,dashboard,report,security,adminUsers,adminRoles,permissions]=await Promise.all([
   api('/sites'),api('/customers'),api('/vehicles'),api('/employees'),api('/resources'),api('/appointments'),
   api('/work-orders'),api('/inventory'),api('/suppliers'),api('/purchase-orders'),api('/absences'),
   api('/tires'),api('/invoices'),api('/reminders'),api('/loaners'),api('/loaner-bookings'),api('/checklists/templates'),
   api('/dashboard'),api('/reports/overview?year=2025'),api('/admin/security-summary'),
   api('/admin/users'),api('/admin/roles'),api('/admin/permissions')
  ]);
  Object.assign(state,{sites,customers,vehicles,employees,resources,appointments,orders,inventory,suppliers,purchaseOrders,absences,tires,invoices,reminders,loaners,loanerBookings,checklists,dashboard,report,security,adminUsers,adminRoles,permissions});
  state.site=sites[0]||null;
  $('siteContext').textContent=state.site?state.site.name+' · '+state.site.city:'Kein Standort';
  $('buildInfo').textContent='ERP 4.0 · STAGING · '+new Date().toLocaleDateString('de-DE');
  renderAll();if(withToast)toast('Staging-Daten aktualisiert.');
 }catch(e){toast(e.message,true)}
}
const customer=id=>state.customers.find(x=>x.id===id);
const vehicle=id=>state.vehicles.find(x=>x.id===id);
const employee=id=>state.employees.find(x=>x.id===id);
const resource=id=>state.resources.find(x=>x.id===id);

function renderAll(){
 const d=state.dashboard||{};
 $('todayLabel').textContent=new Intl.DateTimeFormat('de-DE',{dateStyle:'full'}).format(new Date());
 $('kpiAppointments').textContent=d.appointments??0;
 $('kpiOrders').textContent=d.openOrders??0;
 $('kpiStock').textContent=d.lowStock??0;
 $('kpiReceivables').textContent=fmtMoney(d.receivables||0);

 const rep=state.report||{};
 $('kpiLastYearRevenue').textContent=fmtMoney(rep.netRevenue||0);
 $('reportRevenue').textContent=fmtMoney(rep.netRevenue||0);
 $('reportAverage').textContent=fmtMoney(rep.averageInvoiceNet||0);
 $('reportCustomers').textContent=rep.customerCount??0;
 $('reportVehicles').textContent=rep.vehicleCount??0;
 $('reportInvoiceCount').textContent=(rep.invoiceCount??0)+' Rechnungen';

 $('dashboardOrders').innerHTML=state.orders.filter(o=>o.status!==11&&o.status!==12).slice(0,8).map(o=>{
  const v=vehicle(o.vehicleId),cu=customer(o.customerId);
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(o.number)+' · '+esc(v?.licensePlate||'')+'</b><span>'+esc(v?((v.make||'')+' '+(v.model||'')):'')+' · '+esc(cu?.displayName||'')+'</span></div></div><span class="badge '+badge(workStatus[o.status])+'">'+esc(workStatus[o.status]||o.status)+'</span></div>';
 }).join('')||empty('Keine offenen Aufträge.');

 $('dashboardAppointments').innerHTML=state.appointments.filter(a=>a.status!==4).slice(0,8).map(a=>{
  const v=vehicle(a.vehicleId),cu=customer(a.customerId);
  return '<div class="row-item"><div class="row-main"><div><b>'+fmtDateTime(a.startsAt)+' · '+esc(a.subject)+'</b><span>'+esc(v?.licensePlate||'')+' · '+esc(cu?.displayName||'')+'</span></div></div><span class="badge '+badge(appointmentStatus[a.status])+'">'+esc(appointmentStatus[a.status]||a.status)+'</span></div>';
 }).join('')||empty('Keine Termine.');

 $('appointmentRows').innerHTML=state.appointments.map(a=>{
  const cu=customer(a.customerId),v=vehicle(a.vehicleId),r=resource(a.resourceId);
  const convert=a.workOrderId?'':'<button class="secondary small" data-convert="'+a.id+'">Auftrag</button>';
  return '<tr><td>'+fmtDateTime(a.startsAt)+'</td><td>'+esc(a.subject)+'</td><td>'+esc(cu?.displayName||'')+'</td><td>'+esc(v?.licensePlate||'')+'</td><td>'+esc(r?.name||'–')+'</td><td><span class="badge '+badge(appointmentStatus[a.status])+'">'+esc(appointmentStatus[a.status]||a.status)+'</span></td><td><div class="page-actions">'+convert+'<button class="secondary small" data-edit-appt="'+a.id+'">Bearbeiten</button>'+(a.status!==4?'<button class="secondary small" data-cancel-appt="'+a.id+'">Absagen</button>':'')+'</div></td></tr>';
 }).join('');
 document.querySelectorAll('[data-convert]').forEach(b=>b.onclick=()=>convertAppointment(b.dataset.convert));
 document.querySelectorAll('[data-edit-appt]').forEach(b=>b.onclick=()=>appointmentModal(state.appointments.find(a=>a.id===b.dataset.editAppt)));
 document.querySelectorAll('[data-cancel-appt]').forEach(b=>b.onclick=()=>cancelAppointment(b.dataset.cancelAppt));

 renderOrderBoard();

 $('customerRows').innerHTML=state.customers.map(x=>
  '<tr><td>'+esc(x.customerNumber)+'</td><td><b>'+esc(x.displayName)+'</b></td><td>'+esc(x.phone||x.mobile||'')+'</td><td>'+esc(x.email||'')+'</td><td>'+esc(x.city||'')+'</td><td><button class="secondary small" data-edit-customer="'+x.id+'">Bearbeiten</button></td></tr>'
 ).join('');
 document.querySelectorAll('[data-edit-customer]').forEach(b=>b.onclick=()=>customerModal(customer(b.dataset.editCustomer)));

 $('vehicleRows').innerHTML=state.vehicles.map(v=>
  '<tr><td><b>'+esc(v.licensePlate)+'</b></td><td>'+esc((v.make||'')+' '+(v.model||''))+'</td><td>'+esc(v.vin||'')+'</td><td>'+esc(v.mileage??'–')+'</td><td>'+esc(v.nextHu||'–')+'</td><td><button class="secondary small" data-edit-vehicle="'+v.id+'">Bearbeiten</button></td></tr>'
 ).join('');
 document.querySelectorAll('[data-edit-vehicle]').forEach(b=>b.onclick=()=>vehicleModal(vehicle(b.dataset.editVehicle)));

 $('tireCards').innerHTML=state.tires.map(t=>{
  const v=vehicle(t.vehicleId),cu=customer(t.customerId);
  const cond=t.condition===0?'gut':t.condition===1?'beobachten':'ersetzen';
  return '<article><div class="panel-head"><div><h3>'+esc(t.storageNumber)+'</h3><p>'+esc(v?.licensePlate||'')+' · '+esc(cu?.displayName||'')+'</p></div><span class="badge '+badge(cond)+'">'+esc(cond)+'</span></div><p><b>'+esc(t.size)+'</b> · '+esc(t.brandModel)+'</p><p>'+esc(t.storageLocation)+' · DOT '+esc(t.dot||'–')+(t.hasTpms?' · RDKS':'')+'</p><p class="muted">Profil '+[t.frontLeftMm,t.frontRightMm,t.rearLeftMm,t.rearRightMm].join(' / ')+' mm</p><div class="page-actions"><button class="secondary small" data-edit-tire="'+t.id+'">Bearbeiten</button><button class="secondary small" data-checkout-tire="'+t.id+'">Auslagern</button></div></article>';
 }).join('')||emptyCard('Noch keine Radsätze eingelagert.');
 document.querySelectorAll('[data-edit-tire]').forEach(b=>b.onclick=()=>tireModal(state.tires.find(t=>t.id===b.dataset.editTire)));
 document.querySelectorAll('[data-checkout-tire]').forEach(b=>b.onclick=()=>checkoutTire(b.dataset.checkoutTire));

 $('inventoryRows').innerHTML=state.inventory.map(i=>
  '<tr><td><b>'+esc(i.itemNumber)+'</b></td><td>'+esc(i.description)+'</td><td><span class="badge '+badge(Number(i.stock)<=Number(i.minimumStock)?'kritisch':'vorhanden')+'">'+esc(i.stock)+'</span></td><td>'+esc(i.minimumStock)+'</td><td>'+fmtMoney(i.purchaseNet)+'</td><td>'+fmtMoney(i.saleNet)+'</td><td>'+esc(i.storageLocation||'')+'</td><td><div class="page-actions"><button class="secondary small" data-edit-item="'+i.id+'">Bearbeiten</button><button class="secondary small" data-stock-item="'+i.id+'">Bestand</button></div></td></tr>'
 ).join('');
 document.querySelectorAll('[data-edit-item]').forEach(b=>b.onclick=()=>inventoryModal(state.inventory.find(i=>i.id===b.dataset.editItem)));
 document.querySelectorAll('[data-stock-item]').forEach(b=>b.onclick=()=>stockMovementModal(b.dataset.stockItem));

 $('supplierRows').innerHTML=state.suppliers.map(s=>
  '<div class="row-item"><div class="row-main"><div><b>'+esc(s.name)+'</b><span>'+esc(s.supplierNumber)+' · '+esc(s.phone||s.email||'')+'</span></div></div></div>'
 ).join('')||empty('Noch keine Lieferanten.');

 $('purchaseOrderRows').innerHTML=state.purchaseOrders.map(x=>{
  const o=x.order||x,sup=state.suppliers.find(s=>s.id===o.supplierId),lines=x.lines||[];
  const ordered=lines.reduce((a,l)=>a+Number(l.quantity||0),0),received=lines.reduce((a,l)=>a+Number(l.receivedQuantity||0),0);
  const receive=o.status!==3?'<button class="secondary small" data-receive-po="'+o.id+'">Wareneingang</button>':'';
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(o.number)+' · '+esc(sup?.name||'Lieferant')+'</b><span>'+ordered+' bestellt · '+received+' eingegangen</span></div></div><div class="page-actions"><span class="badge '+badge(o.status===3?'erhalten':o.status===2?'teil':'bestellt')+'">'+esc(o.status===3?'Erhalten':o.status===2?'Teilweise':'Bestellt')+'</span>'+receive+'</div></div>';
 }).join('')||empty('Keine Bestellungen vorhanden.');
 document.querySelectorAll('[data-receive-po]').forEach(b=>b.onclick=()=>goodsReceiptModal(b.dataset.receivePo));
 renderPurchaseForm();

 $('employeeRows').innerHTML=state.employees.map(e=>
  '<tr><td><b>'+esc(e.name)+'</b></td><td>'+esc(e.roleName)+'</td><td>'+esc(e.weeklyHours)+' h</td><td>'+esc(e.annualVacationDays)+' Tage</td><td>'+fmtMoney(e.productiveHourlyRate)+'/h</td></tr>'
 ).join('');
 $('absenceRows').innerHTML=state.absences.map(a=>{
  const e=employee(a.employeeId),types=['Urlaub','Krank','Schulung','Berufsschule','Überstundenabbau','Sonderurlaub','Elternzeit','Dienstreise','Sonstiges'];
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(e?.name||'Mitarbeiter')+' · '+esc(types[a.type]||'Abwesenheit')+'</b><span>'+esc(a.from)+' bis '+esc(a.to)+(a.reason?' · '+esc(a.reason):'')+'</span></div></div><span class="badge '+badge(a.approved?'aktiv':'offen')+'">'+(a.approved?'Freigegeben':'Offen')+'</span></div>';
 }).join('')||empty('Keine Abwesenheiten eingetragen.');

 $('invoiceRows').innerHTML=state.invoices.map(i=>{
  const actions='<button class="secondary small" data-invoice-detail="'+i.id+'">Details</button>'+(i.status!==3&&i.status!==5&&i.status!==6?'<button class="secondary small" data-pay="'+i.id+'">Zahlung</button>':'')+(!i.number.startsWith('ST-')&&!i.number.startsWith('GS-')&&i.status!==5&&i.status!==6?'<button class="secondary small" data-reverse="'+i.id+'">Korrektur</button>':'');
  return '<tr><td><b>'+esc(i.number)+'</b></td><td>'+esc(i.issueDate)+'</td><td>'+esc(i.dueDate)+'</td><td>'+fmtMoney(i.grossTotal)+'</td><td>'+fmtMoney(i.paidTotal)+'</td><td><span class="badge '+badge(invoiceStatus[i.status])+'">'+esc(invoiceStatus[i.status]||i.status)+'</span></td><td><div class="page-actions">'+actions+'</div></td></tr>';
 }).join('');
 document.querySelectorAll('[data-pay]').forEach(b=>b.onclick=()=>paymentModal(b.dataset.pay));
 document.querySelectorAll('[data-invoice-detail]').forEach(b=>b.onclick=()=>invoiceDetail(b.dataset.invoiceDetail));
 document.querySelectorAll('[data-reverse]').forEach(b=>b.onclick=()=>reverseInvoiceModal(b.dataset.reverse));

 $('reminderRows').innerHTML=state.reminders.map(r=>{
  const cu=customer(r.customerId),v=vehicle(r.vehicleId);
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(r.subject)+' · '+esc(cu?.displayName||'')+'</b><span>'+fmtDateTime(r.dueAt)+(v?' · '+esc(v.licensePlate):'')+' · '+esc(r.type)+'</span></div></div><div class="page-actions"><span class="badge '+badge(new Date(r.dueAt)<new Date()?'kritisch':'offen')+'">'+(new Date(r.dueAt)<new Date()?'Fällig':'Offen')+'</span><button class="secondary small" data-complete-reminder="'+r.id+'">Erledigt</button></div></div>';
 }).join('')||empty('Keine offenen Wiedervorlagen.');
 document.querySelectorAll('[data-complete-reminder]').forEach(b=>b.onclick=()=>completeReminder(b.dataset.completeReminder));

 $('loanerRows').innerHTML=state.loaners.map(l=>
  '<div class="row-item"><div class="row-main"><div><b>'+esc(l.number)+' · '+esc(l.licensePlate)+'</b><span>'+esc(l.vehicleName)+' · '+esc(l.mileage)+' km · '+esc(l.fuelOrChargeLevel)+'</span></div></div><span class="badge success">aktiv</span></div>'
 ).join('')||empty('Keine Leihwagen.');

 $('loanerBookingRows').innerHTML=state.loanerBookings.map(b=>{
  const l=state.loaners.find(x=>x.id===b.loanerVehicleId),cu=customer(b.customerId);
  const status=['Reserviert','Ausgegeben','Zurück','Storniert'][b.status]||b.status;
  const action=b.status===0?'<button class="secondary small" data-loaner-out="'+b.id+'">Ausgeben</button>':b.status===1?'<button class="secondary small" data-loaner-return="'+b.id+'">Rücknahme</button>':'';
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(l?.number||'Leihwagen')+' · '+esc(cu?.displayName||'')+'</b><span>'+fmtDateTime(b.from)+' bis '+fmtDateTime(b.to)+'</span></div></div><div class="page-actions"><span class="badge '+badge(status)+'">'+esc(status)+'</span>'+action+'</div></div>';
 }).join('')||empty('Keine Reservierungen.');
 document.querySelectorAll('[data-loaner-out]').forEach(b=>b.onclick=()=>loanerHandoverModal(b.dataset.loanerOut,false));
 document.querySelectorAll('[data-loaner-return]').forEach(b=>b.onclick=()=>loanerHandoverModal(b.dataset.loanerReturn,true));

 $('checklistRows').innerHTML=state.checklists.map(x=>{
  const t=x.template||x,fields=x.fields||[];
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(t.name)+'</b><span>'+esc(t.context)+' · '+fields.length+' Prüfpunkte</span></div></div><button class="primary small" data-run-checklist="'+t.id+'">Starten</button></div>';
 }).join('')||empty('Keine Checklisten.');
 document.querySelectorAll('[data-run-checklist]').forEach(b=>b.onclick=()=>checklistModal(b.dataset.runChecklist));

 const monthly=(state.report?.monthly||[]);
 const maxMonth=Math.max(1,...monthly.map(m=>Number(m.net||0)));
 const monthNames=['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'];
 $('monthlyRevenue').innerHTML=monthly.map(m=>{
  const pct=Math.max(3,Math.round(Number(m.net||0)/maxMonth*100));
  return '<div class="bar-col"><span class="bar-value">'+esc(fmtMoney(m.net||0).replace(',00',''))+'</span><div class="bar" style="height:'+pct+'%"></div><span class="bar-label">'+monthNames[(m.month||1)-1]+'</span></div>';
 }).join('');

 $('topCustomers').innerHTML=(state.report?.topCustomers||[]).map((x,i)=>
  '<div class="row-item"><div class="row-main"><div><b>'+(i+1)+'. '+esc(x.name)+'</b><span>'+esc(x.count)+' Rechnungen</span></div></div><b>'+fmtMoney(x.net)+'</b></div>'
 ).join('')||empty('Keine Umsatzdaten.');

 const sec=state.security||{};
 $('securitySummary').innerHTML=[['Benutzer',sec.users??0],['Rollen',sec.roles??0],['Rechte',sec.permissions??0],['Standorte',sec.sites??0],['Audit-Einträge',sec.auditEntries??0]]
  .map(x=>'<div><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></div>').join('');

 $('adminUserRows').innerHTML=state.adminUsers.map(x=>{
  const u=x.user||x,roleNames=(x.roleIds||[]).map(id=>(state.adminRoles.find(r=>(r.role||r).id===id)?.role||state.adminRoles.find(r=>(r.role||r).id===id))?.name).filter(Boolean);
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(u.displayName||u.email||'Benutzer')+'</b><span>'+esc(roleNames.join(', ')||'Keine Rolle')+'</span></div></div><button class="secondary small" data-user-roles="'+u.id+'">Rollen</button></div>';
 }).join('')||empty('Keine Benutzer.');

 $('adminRoleRows').innerHTML=state.adminRoles.map(x=>{
  const r=x.role||x,perms=x.permissions||[];
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(r.name)+'</b><span>'+perms.length+' Rechte · '+esc(r.description||'')+'</span></div></div><button class="secondary small" data-role-perms="'+r.id+'">Rechte</button></div>';
 }).join('')||empty('Keine Rollen.');

 $('resourceRows').innerHTML=state.resources.map(r=>
  '<div class="row-item"><div class="row-main"><div><b>'+esc(r.name)+'</b><span>'+esc(resourceKindName(r.kind))+(r.maxLoadKg?' · '+esc(r.maxLoadKg)+' kg':'')+(r.supportsEv?' · EV':'')+'</span></div></div><span class="badge success">aktiv</span></div>'
 ).join('')||empty('Keine Ressourcen.');
 document.querySelectorAll('[data-user-roles]').forEach(b=>b.onclick=()=>userRolesModal(b.dataset.userRoles));
 document.querySelectorAll('[data-role-perms]').forEach(b=>b.onclick=()=>rolePermissionsModal(b.dataset.rolePerms));

 $('intakeOrder').innerHTML=state.orders.filter(o=>o.status<10&&o.status!==12).map(o=>'<option value="'+o.id+'">'+esc(o.number)+' · '+esc(vehicle(o.vehicleId)?.licensePlate||'')+'</option>').join('');
 if(!$('checkItems').children.length)$('checkItems').innerHTML=['Beleuchtung','Bremsen','Bereifung','Flüssigkeiten','Warnleuchten','Wischer/Wascher','Unterboden','Fehlerspeicher'].map(x=>'<label class="check-item"><span>'+x+'</span><input type="checkbox"></label>').join('');
 renderWorkshopPlanner();
 renderPersonnelPlanner();
}
function empty(s){return '<div class="row-item"><div class="row-main"><div><span>'+esc(s)+'</span></div></div></div>'}
function emptyCard(s){return '<article><p>'+esc(s)+'</p></article>'}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}

function renderOrderBoard(){
 const stages=[['Geplant',[0,1,2,3]],['Diagnose',[4]],['Freigabe',[5,6]],['In Arbeit',[7,8]],['Fertig',[9,10,11]]];
 $('orderBoard').innerHTML=stages.map(([name,codes])=>'<div class="kanban-col"><h4>'+name+'</h4>'+state.orders.filter(o=>codes.includes(o.status)).map(o=>{
  const v=vehicle(o.vehicleId),c=customer(o.customerId);
  return '<div class="ticket '+(state.selectedOrder===o.id?'selected':'')+'" data-order="'+o.id+'"><b>'+esc(o.number)+' · '+esc(v?.licensePlate||'')+'</b><small>'+esc(v?((v.make||'')+' '+(v.model||'')):'')+' · '+esc(c?.displayName||'')+'</small><small>'+esc(workStatus[o.status])+'</small></div>'
 }).join('')+'</div>').join('');
 document.querySelectorAll('[data-order]').forEach(b=>b.onclick=()=>openOrder(b.dataset.order));
}
async function openOrder(id){
 state.selectedOrder=id;renderOrderBoard();
 try{
  const d=await api('/work-orders/'+id);const o=d.order,v=vehicle(o.vehicleId),c=customer(o.customerId);
  const next=nextStatus(o.status);
  $('orderDetail').innerHTML='<div class="panel-head"><div><h3>'+esc(o.number)+' · '+esc(v?.licensePlate||'')+'</h3><p>'+esc(c?.displayName||'')+' · '+esc(v?((v.make||'')+' '+(v.model||'')):'')+'</p></div><span class="badge '+badge(workStatus[o.status])+'">'+esc(workStatus[o.status])+'</span></div>'+
   '<div class="release-grid"><div><b>Kundenwunsch</b><span>'+esc(o.customerRequest||'–')+'</span></div><div><b>Diagnose</b><span>'+esc(o.diagnosis||'–')+'</span></div><div><b>Fertig bis</b><span>'+fmtDateTime(o.promisedAt)+'</span></div></div>'+
   '<h3 style="margin-top:18px">Positionen</h3>'+(d.lines.length?'<div class="rows">'+d.lines.map(l=>'<div class="row-item"><div><b>'+esc(l.description)+'</b><span>'+esc(l.quantity)+' × '+fmtMoney(l.unitNet)+'</span></div><b>'+fmtMoney(l.netTotal)+'</b></div>').join('')+'</div>':'<p class="muted">Noch keine Positionen.</p>')+
   '<h3 style="margin-top:18px">Zeiterfassung</h3><div class="rows">'+(d.times.length?d.times.map(t=>'<div class="row-item"><div><b>'+esc(employee(t.employeeId)?.name||'Mitarbeiter')+'</b><span>'+fmtDateTime(t.startedAt)+' · '+esc(t.activity||'Arbeitszeit')+'</span></div><div>'+(t.endedAt?fmtDateTime(t.endedAt):'<button class="secondary small" data-stop-time="'+t.id+'">Stop</button>')+'</div></div>').join(''):empty('Keine Zeiterfassung.'))+'</div>'+
   '<div class="page-actions" style="margin-top:16px"><button class="primary" id="addLineBtn">+ Position</button><button class="secondary" id="addPartBtn">Teil aus Lager</button><button class="secondary" id="approvalBtn">Freigabe</button><button class="secondary" id="startTimeBtn">Zeit starten</button>'+(next!==null?'<button class="secondary" id="nextStatusBtn">→ '+esc(workStatus[next])+'</button>':'')+(o.status===9?'<button class="primary" id="invoiceBtn">Rechnung erzeugen</button>':'')+'</div>';
  $('orderDetail').classList.remove('hidden');
  $('addLineBtn').onclick=()=>lineModal(id);
  $('addPartBtn').onclick=()=>inventoryPartModal(id);
  $('approvalBtn').onclick=()=>approvalModal(id);
  $('startTimeBtn').onclick=()=>timeStartModal(id);
  document.querySelectorAll('[data-stop-time]').forEach(b=>b.onclick=()=>stopTime(id,b.dataset.stopTime));
  if($('nextStatusBtn'))$('nextStatusBtn').onclick=()=>transition(id,next);
  if($('invoiceBtn'))$('invoiceBtn').onclick=()=>createInvoice(id);
 }catch(e){toast(e.message,true)}
}
function resourceKindName(k){return ['Hebebühne','Grube','Diagnoseplatz','Achsvermessung','Klimastation','Reifenplatz','Parkplatz','Direktannahme','Leihwagen','Spezialwerkzeug','Sonstiges'][k]||'Ressource'}
function nextStatus(s){const m={0:1,1:2,2:3,3:4,4:5,5:6,6:7,7:8,8:9,9:10,10:11};return m[s]??null}
async function transition(id,status){try{await api('/work-orders/'+id+'/transition',{method:'POST',body:JSON.stringify({status})});toast('Auftragsstatus aktualisiert.');await loadAll();await openOrder(id)}catch(e){toast(e.message,true)}}
async function convertAppointment(id){try{await api('/work-orders/from-appointment/'+id,{method:'POST'});toast('Werkstattauftrag erzeugt.');await loadAll();page('orders')}catch(e){toast(e.message,true)}}

function options(arr,label,selected=null){
 return arr.map(x=>'<option value="'+x.id+'" '+(selected===x.id?'selected':'')+'>'+esc(label(x))+'</option>').join('')
}
function modalForm(title,body,onSubmit,submitLabel='Speichern'){
 showModal(title,'<form id="dynamicForm">'+body+'<div class="modal-actions"><button type="button" class="secondary" id="cancelModal">Abbrechen</button><button class="primary" type="submit">'+esc(submitLabel)+'</button></div></form>');
 $('cancelModal').onclick=closeModal;
 $('dynamicForm').onsubmit=async e=>{
  e.preventDefault();
  try{
   await onSubmit(new FormData(e.target));
   closeModal();
   await loadAll();
   toast('Gespeichert.');
  }catch(err){toast(err.message,true)}
 };
}

function customerModal(existing=null){
 const x=existing||{};
 modalForm(existing?'Kunde bearbeiten':'Kunde anlegen',
 '<div class="form-grid">'+
 '<label class="span2">Anzeigename<input name="displayName" required value="'+esc(x.displayName||'')+'"></label>'+
 '<label>Firma<input name="companyName" value="'+esc(x.companyName||'')+'"></label>'+
 '<label>Vorname<input name="firstName" value="'+esc(x.firstName||'')+'"></label>'+
 '<label>Nachname<input name="lastName" value="'+esc(x.lastName||'')+'"></label>'+
 '<label>Telefon<input name="phone" value="'+esc(x.phone||'')+'"></label>'+
 '<label>Mobil<input name="mobile" value="'+esc(x.mobile||'')+'"></label>'+
 '<label>E-Mail<input name="email" type="email" value="'+esc(x.email||'')+'"></label>'+
 '<label>Straße<input name="street" value="'+esc(x.street||'')+'"></label>'+
 '<label>PLZ<input name="postalCode" value="'+esc(x.postalCode||'')+'"></label>'+
 '<label>Ort<input name="city" value="'+esc(x.city||'')+'"></label>'+
 '<label class="span2">Notizen<textarea name="notes">'+esc(x.notes||'')+'</textarea></label></div>',
 async f=>{
  const body={displayName:f.get('displayName'),companyName:f.get('companyName'),firstName:f.get('firstName'),lastName:f.get('lastName'),email:f.get('email'),phone:f.get('phone'),mobile:f.get('mobile'),street:f.get('street'),postalCode:f.get('postalCode'),city:f.get('city'),notes:f.get('notes')};
  return api(existing?'/customers/'+existing.id:'/customers',{method:existing?'PUT':'POST',body:JSON.stringify(body)});
 });
}

function vehicleModal(existing=null){
 const x=existing||{};
 modalForm(existing?'Fahrzeug bearbeiten':'Fahrzeug anlegen',
 '<div class="form-grid">'+
 '<label class="span2">Kunde<select name="customerId">'+options(state.customers,c=>c.displayName,x.customerId||state.customers[0]?.id)+'</select></label>'+
 '<label>Kennzeichen<input name="licensePlate" required value="'+esc(x.licensePlate||'')+'"></label>'+
 '<label>VIN<input name="vin" value="'+esc(x.vin||'')+'"></label>'+
 '<label>Hersteller<input name="make" value="'+esc(x.make||'')+'"></label>'+
 '<label>Modell<input name="model" value="'+esc(x.model||'')+'"></label>'+
 '<label>Typ<input name="type" value="'+esc(x.type||'')+'"></label>'+
 '<label>HSN<input name="hsn" value="'+esc(x.hsn||'')+'"></label>'+
 '<label>TSN<input name="tsn" value="'+esc(x.tsn||'')+'"></label>'+
 '<label>Erstzulassung<input name="firstRegistration" type="date" value="'+esc(x.firstRegistration||'')+'"></label>'+
 '<label>Kilometer<input name="mileage" type="number" value="'+esc(x.mileage??'')+'"></label>'+
 '<label>HU<input name="nextHu" type="date" value="'+esc(x.nextHu||'')+'"></label>'+
 '<label>Nächster Service<input name="nextService" type="date" value="'+esc(x.nextService||'')+'"></label></div>',
 async f=>{
  const body={customerId:f.get('customerId'),licensePlate:f.get('licensePlate'),vin:f.get('vin'),make:f.get('make'),model:f.get('model'),type:f.get('type'),hsn:f.get('hsn'),tsn:f.get('tsn'),firstRegistration:f.get('firstRegistration')||null,mileage:f.get('mileage')?Number(f.get('mileage')):null,nextHu:f.get('nextHu')||null,nextService:f.get('nextService')||null};
  return api(existing?'/vehicles/'+existing.id:'/vehicles',{method:existing?'PUT':'POST',body:JSON.stringify(body)});
 });
}

function appointmentModal(existing=null){
 const x=existing||{};
 const local=v=>v?new Date(v).toISOString().slice(0,16):'';
 modalForm(existing?'Termin bearbeiten':'Termin anlegen',
 '<div class="form-grid">'+
 '<label>Kunde<select name="customerId">'+options(state.customers,c=>c.displayName,x.customerId||state.customers[0]?.id)+'</select></label>'+
 '<label>Fahrzeug<select name="vehicleId">'+options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model,x.vehicleId||state.vehicles[0]?.id)+'</select></label>'+
 '<label>Start<input name="startsAt" type="datetime-local" required value="'+local(x.startsAt)+'"></label>'+
 '<label>Ende<input name="endsAt" type="datetime-local" required value="'+local(x.endsAt)+'"></label>'+
 '<label>Ressource<select name="resourceId"><option value="">–</option>'+options(state.resources,r=>r.name,x.resourceId)+'</select></label>'+
 '<label>Mitarbeiter<select name="employeeId"><option value="">–</option>'+options(state.employees,e=>e.name,x.employeeId)+'</select></label>'+
 '<label class="span2">Betreff<input name="subject" required value="'+esc(x.subject||'')+'" placeholder="z. B. Inspektion + Ölservice"></label>'+
 '<label class="span2">Kundenwunsch<textarea name="customerRequest">'+esc(x.customerRequest||'')+'</textarea></label></div>',
 async f=>{
  const body={siteId:state.site?.id,customerId:f.get('customerId'),vehicleId:f.get('vehicleId'),resourceId:f.get('resourceId')||null,employeeId:f.get('employeeId')||null,startsAt:new Date(f.get('startsAt')).toISOString(),endsAt:new Date(f.get('endsAt')).toISOString(),subject:f.get('subject'),customerRequest:f.get('customerRequest')};
  return api(existing?'/appointments/'+existing.id:'/appointments',{method:existing?'PUT':'POST',body:JSON.stringify(body)});
 });
}
async function cancelAppointment(id){
 if(!confirm('Termin wirklich absagen?'))return;
 try{await api('/appointments/'+id+'/cancel',{method:'POST'});await loadAll();toast('Termin abgesagt.')}catch(e){toast(e.message,true)}
}

function workOrderModal(){
 const customerOpts=options(state.customers,c=>c.customerNumber+' · '+c.displayName);
 const vehicleOpts=options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model);
 modalForm('Direktauftrag anlegen',
 '<div class="form-grid"><label>Kunde<select name="customerId">'+customerOpts+'</select></label><label>Fahrzeug<select name="vehicleId">'+vehicleOpts+'</select></label>'+
 '<label class="span2">Kundenwunsch<textarea name="customerRequest" required placeholder="Auftrag / Kundenbeanstandung"></textarea></label>'+
 '<label class="span2">Erste Diagnose / Hinweis<textarea name="diagnosis"></textarea></label>'+
 '<label>Fertig bis<input name="promisedAt" type="datetime-local"></label></div>',
 async f=>api('/work-orders',{method:'POST',body:JSON.stringify({siteId:state.site?.id,customerId:f.get('customerId'),vehicleId:f.get('vehicleId'),customerRequest:f.get('customerRequest'),diagnosis:f.get('diagnosis'),promisedAt:f.get('promisedAt')?new Date(f.get('promisedAt')).toISOString():null})})
 );
}

function lineModal(id){
 modalForm('Freie Auftragsposition',
 '<div class="form-grid"><label>Art<select name="type"><option value="0">Arbeit</option><option value="1">Teil</option><option value="2">Material</option><option value="3">Gebühr</option><option value="5">Text</option></select></label><label>Artikelnummer<input name="itemNumber"></label><label class="span2">Beschreibung<input name="description" required></label><label>Menge<input name="quantity" type="number" step=".01" value="1"></label><label>Netto Einzel<input name="unitNet" type="number" step=".01" value="0"></label><label>USt %<input name="vatRate" type="number" step=".01" value="19"></label><label>Rabatt %<input name="discountPercent" type="number" step=".01" value="0"></label></div>',
 async f=>{await api('/work-orders/'+id+'/lines',{method:'POST',body:JSON.stringify({type:Number(f.get('type')),itemNumber:f.get('itemNumber'),description:f.get('description'),quantity:Number(f.get('quantity')),unitNet:Number(f.get('unitNet')),vatRate:Number(f.get('vatRate')),discountPercent:Number(f.get('discountPercent'))})});await openOrder(id)}
 );
}

function inventoryPartModal(orderId){
 const rows=state.inventory.map(i=>'<option value="'+i.id+'">'+esc(i.itemNumber)+' · '+esc(i.description)+' · Bestand '+esc(i.stock)+' · '+esc(fmtMoney(i.saleNet))+'</option>').join('');
 modalForm('Zubehörteil aus Lager übernehmen',
 '<label>Artikel / Zubehörteilenummer<select name="inventoryItemId">'+rows+'</select></label><div class="form-grid"><label>Menge<input name="quantity" type="number" min=".01" step=".01" value="1"></label><label>VK netto (leer = Artikelpreis)<input name="unitNet" type="number" step=".01"></label><label>USt %<input name="vatRate" type="number" step=".01" value="19"></label><label>Rabatt %<input name="discountPercent" type="number" step=".01" value="0"></label></div><label class="check-item"><span>Vom Kunden freigegeben</span><input name="approved" type="checkbox" checked></label>',
 async f=>{await api('/work-orders/'+orderId+'/inventory-line',{method:'POST',body:JSON.stringify({inventoryItemId:f.get('inventoryItemId'),quantity:Number(f.get('quantity')),unitNet:f.get('unitNet')?Number(f.get('unitNet')):null,vatRate:Number(f.get('vatRate')),discountPercent:Number(f.get('discountPercent')),approvedByCustomer:f.get('approved')==='on'})});await openOrder(orderId)}
 );
}

function approvalModal(id){
 modalForm('Kundenfreigabe','<label>Freigabebetrag brutto<input name="offeredGross" type="number" step=".01" required></label><label>Kanal<select name="channel"><option>Link</option><option>Telefon</option><option>E-Mail</option></select></label>',
 async f=>{const a=await api('/work-orders/'+id+'/approvals',{method:'POST',body:JSON.stringify({offeredGross:Number(f.get('offeredGross')),channel:f.get('channel')})});await api('/approvals/'+a.id+'/respond',{method:'POST',body:JSON.stringify({status:1,note:'Staging: Kundenfreigabe bestätigt'})});await openOrder(id)}
 );
}
async function createInvoice(id){try{await api('/invoices/from-work-order/'+id,{method:'POST'});toast('Rechnung erzeugt.');await loadAll();page('billing')}catch(e){toast(e.message,true)}}

function paymentModal(id){
 const inv=state.invoices.find(x=>x.id===id);
 const open=Math.max(0,Number(inv?.grossTotal||0)-Number(inv?.paidTotal||0));
 modalForm('Zahlung erfassen','<label>Betrag<input name="amount" type="number" step=".01" value="'+open.toFixed(2)+'" required></label><label>Zahlungsart<select name="method"><option value="0">Bar</option><option value="1">Karte</option><option value="2">Überweisung</option><option value="3">Lastschrift</option></select></label><label>Referenz<input name="reference"></label>',
 async f=>api('/invoices/'+id+'/payments',{method:'POST',body:JSON.stringify({amount:Number(f.get('amount')),method:Number(f.get('method')),reference:f.get('reference')})})
 );
}

async function invoiceDetail(id){
 try{
  const d=await api('/invoices/'+id),i=d.invoice;
  showModal('Beleg '+i.number,
   '<div class="release-grid"><div><b>Netto</b><span>'+fmtMoney(i.netTotal)+'</span></div><div><b>USt</b><span>'+fmtMoney(i.vatTotal)+'</span></div><div><b>Brutto</b><span>'+fmtMoney(i.grossTotal)+'</span></div></div>'+
   '<h3 style="margin-top:18px">Positionen</h3><div class="rows">'+d.lines.map(l=>'<div class="row-item"><div><b>'+esc(l.description)+'</b><span>'+esc(l.quantity)+' × '+fmtMoney(l.unitNet)+' · '+esc(l.vatRate)+' %</span></div><b>'+fmtMoney(Number(l.quantity)*Number(l.unitNet))+'</b></div>').join('')+'</div>'+
   '<h3 style="margin-top:18px">Zahlungen</h3><div class="rows">'+(d.payments.length?d.payments.map(p=>'<div class="row-item"><div><b>'+fmtMoney(p.amount)+'</b><span>'+fmtDateTime(p.paidAt)+' · '+esc(p.reference||'')+'</span></div></div>').join(''):empty('Keine Zahlungen.'))+'</div>');
 }catch(e){toast(e.message,true)}
}

function reverseInvoiceModal(id){
 const inv=state.invoices.find(x=>x.id===id);
 modalForm('Rechnung korrigieren: '+esc(inv?.number||''),
 '<label>Art<select name="kind"><option value="cancel">Storno</option><option value="credit">Gutschrift</option></select></label><label>Grund<textarea name="reason" required placeholder="Grund der Korrektur"></textarea></label><p class="muted">Es wird ein eigener negativer Folgebelg erzeugt. Die Originalrechnung bleibt nachvollziehbar erhalten.</p>',
 async f=>api('/invoices/'+id+'/reverse',{method:'POST',body:JSON.stringify({kind:f.get('kind'),reason:f.get('reason')})})
 );
}

function tireModal(existing=null){
 const x=existing||{};
 modalForm(existing?'Radsatz bearbeiten':'Radsatz einlagern',
 '<div class="form-grid"><label>Kunde<select name="customerId">'+options(state.customers,c=>c.displayName,x.customerId||state.customers[0]?.id)+'</select></label><label>Fahrzeug<select name="vehicleId">'+options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model,x.vehicleId||state.vehicles[0]?.id)+'</select></label>'+
 '<label>Lagernummer<input name="storageNumber" required value="'+esc(x.storageNumber||'')+'"></label><label>Lagerplatz<input name="storageLocation" required value="'+esc(x.storageLocation||'')+'"></label>'+
 '<label>Saison<select name="season"><option value="0" '+(x.season===0?'selected':'')+'>Sommer</option><option value="1" '+(x.season===1?'selected':'')+'>Winter</option><option value="2" '+(x.season===2?'selected':'')+'>Ganzjahr</option></select></label>'+
 '<label>Größe<input name="size" required value="'+esc(x.size||'')+'" placeholder="205/55 R16"></label><label>Marke / Modell<input name="brandModel" required value="'+esc(x.brandModel||'')+'"></label><label>DOT<input name="dot" value="'+esc(x.dot||'')+'"></label>'+
 '<label>VL mm<input name="fl" type="number" step=".1" value="'+esc(x.frontLeftMm??6)+'"></label><label>VR mm<input name="fr" type="number" step=".1" value="'+esc(x.frontRightMm??6)+'"></label><label>HL mm<input name="rl" type="number" step=".1" value="'+esc(x.rearLeftMm??6)+'"></label><label>HR mm<input name="rr" type="number" step=".1" value="'+esc(x.rearRightMm??6)+'"></label>'+
 '<label>Zustand<select name="condition"><option value="0" '+(x.condition===0?'selected':'')+'>Gut</option><option value="1" '+(x.condition===1?'selected':'')+'>Beobachten</option><option value="2" '+(x.condition===2?'selected':'')+'>Ersetzen</option></select></label><label class="check-item"><span>RDKS vorhanden</span><input name="hasTpms" type="checkbox" '+(x.hasTpms?'checked':'')+'></label></div>',
 async f=>{
  const body={customerId:f.get('customerId'),vehicleId:f.get('vehicleId'),storageNumber:f.get('storageNumber'),season:Number(f.get('season')),brandModel:f.get('brandModel'),size:f.get('size'),dot:f.get('dot'),frontLeftMm:Number(f.get('fl')),frontRightMm:Number(f.get('fr')),rearLeftMm:Number(f.get('rl')),rearRightMm:Number(f.get('rr')),condition:Number(f.get('condition')),storageLocation:f.get('storageLocation'),hasTpms:f.get('hasTpms')==='on'};
  return api(existing?'/tires/'+existing.id:'/tires',{method:existing?'PUT':'POST',body:JSON.stringify(body)});
 });
}
async function checkoutTire(id){
 if(!confirm('Radsatz wirklich auslagern?'))return;
 try{await api('/tires/'+id+'/checkout',{method:'POST'});await loadAll();toast('Radsatz ausgelagert.')}catch(e){toast(e.message,true)}
}

function inventoryModal(existing=null){
 const x=existing||{};
 modalForm(existing?'Lagerartikel bearbeiten':'Lagerartikel anlegen',
 '<div class="form-grid"><label>Artikel-/Zubehörnummer<input name="itemNumber" required value="'+esc(x.itemNumber||'')+'"></label><label>EAN<input name="ean" value="'+esc(x.ean||'')+'"></label><label>Hersteller<input name="manufacturer" value="'+esc(x.manufacturer||'')+'"></label><label>Bezeichnung<input name="description" required value="'+esc(x.description||'')+'"></label><label>EK netto<input name="purchaseNet" type="number" step=".01" value="'+esc(x.purchaseNet??0)+'"></label><label>VK netto<input name="saleNet" type="number" step=".01" value="'+esc(x.saleNet??0)+'"></label><label>Startbestand<input name="stock" type="number" step=".01" value="'+esc(x.stock??0)+'" '+(existing?'readonly':'')+'></label><label>Mindestbestand<input name="minimumStock" type="number" step=".01" value="'+esc(x.minimumStock??0)+'"></label><label>Lagerort<input name="storageLocation" value="'+esc(x.storageLocation||'')+'"></label><label>Lieferant<select name="preferredSupplierId"><option value="">–</option>'+options(state.suppliers,s=>s.name,x.preferredSupplierId)+'</select></label></div>',
 async f=>api(existing?'/inventory/'+existing.id:'/inventory',{method:existing?'PUT':'POST',body:JSON.stringify({itemNumber:f.get('itemNumber'),ean:f.get('ean'),manufacturer:f.get('manufacturer'),description:f.get('description'),purchaseNet:Number(f.get('purchaseNet')),saleNet:Number(f.get('saleNet')),stock:Number(f.get('stock')||x.stock||0),minimumStock:Number(f.get('minimumStock')),storageLocation:f.get('storageLocation'),preferredSupplierId:f.get('preferredSupplierId')||null})})
 );
}

function stockMovementModal(itemId){
 const item=state.inventory.find(i=>i.id===itemId);
 modalForm('Bestand buchen: '+esc(item?.itemNumber||''),
 '<label>Buchungsart<select name="type"><option value="0">Wareneingang</option><option value="1">Verbrauch</option><option value="2">Rückgabe</option><option value="3">Korrektur +</option></select></label><label>Menge<input name="quantity" type="number" step=".01" min=".01" required></label><label>Referenz<input name="reference" placeholder="Inventur, Rückgabe, Lieferschein …"></label>',
 async f=>api('/inventory/'+itemId+'/movement',{method:'POST',body:JSON.stringify({siteId:state.site.id,type:Number(f.get('type')),quantity:Number(f.get('quantity')),reference:f.get('reference')})})
 );
}

function supplierModal(){
 modalForm('Lieferant anlegen','<div class="form-grid"><label>Lieferantennummer<input name="supplierNumber"></label><label>Name<input name="name" required></label><label>E-Mail<input name="email" type="email"></label><label>Telefon<input name="phone"></label></div>',
 async f=>api('/suppliers',{method:'POST',body:JSON.stringify({supplierNumber:f.get('supplierNumber'),name:f.get('name'),email:f.get('email'),phone:f.get('phone')})})
 );
}

function reminderModal(){
 modalForm('Wiedervorlage anlegen','<div class="form-grid"><label>Kunde<select name="customerId">'+options(state.customers,c=>c.displayName)+'</select></label><label>Fahrzeug<select name="vehicleId"><option value="">–</option>'+options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model)+'</select></label><label>Typ<input name="type" value="Service"></label><label>Fällig<input name="dueAt" type="datetime-local" required></label><label class="span2">Betreff<input name="subject" required></label><label>Kanal<select name="preferredChannel"><option value="0">E-Mail</option><option value="1">SMS</option><option value="2">Telefon</option><option value="3">WhatsApp</option><option value="4">Brief</option><option value="5">In-App</option></select></label></div>',
 async f=>api('/reminders',{method:'POST',body:JSON.stringify({customerId:f.get('customerId'),vehicleId:f.get('vehicleId')||null,type:f.get('type'),subject:f.get('subject'),dueAt:new Date(f.get('dueAt')).toISOString(),preferredChannel:Number(f.get('preferredChannel'))})})
 );
}
async function completeReminder(id){
 try{await api('/reminders/'+id+'/status',{method:'PUT',body:JSON.stringify({status:2})});await loadAll();toast('Wiedervorlage erledigt.')}catch(e){toast(e.message,true)}
}

function loanerModal(){
 modalForm('Leihwagen anlegen','<div class="form-grid"><label>Nummer<input name="number" required placeholder="LW-04"></label><label>Kennzeichen<input name="licensePlate" required></label><label>Fahrzeug<input name="vehicleName" required></label><label>Kilometer<input name="mileage" type="number" value="0"></label><label>Tank/Ladung<input name="fuel" value="voll"></label></div>',
 async f=>api('/loaners',{method:'POST',body:JSON.stringify({siteId:state.site?.id,number:f.get('number'),licensePlate:f.get('licensePlate'),vehicleName:f.get('vehicleName'),mileage:Number(f.get('mileage')),fuelOrChargeLevel:f.get('fuel')})})
 );
}
function loanerBookingModal(){
 modalForm('Leihwagen reservieren','<div class="form-grid"><label>Leihwagen<select name="loanerVehicleId">'+options(state.loaners,l=>l.number+' · '+l.licensePlate+' · '+l.vehicleName)+'</select></label><label>Kunde<select name="customerId">'+options(state.customers,c=>c.displayName)+'</select></label><label>Auftrag<select name="workOrderId"><option value="">–</option>'+options(state.orders,o=>o.number+' · '+(vehicle(o.vehicleId)?.licensePlate||''))+'</select></label><label>Von<input name="from" type="datetime-local" required></label><label>Bis<input name="to" type="datetime-local" required></label></div>',
 async f=>api('/loaner-bookings',{method:'POST',body:JSON.stringify({loanerVehicleId:f.get('loanerVehicleId'),customerId:f.get('customerId'),workOrderId:f.get('workOrderId')||null,from:new Date(f.get('from')).toISOString(),to:new Date(f.get('to')).toISOString()})})
 );
}
function loanerHandoverModal(id,isReturn){
 modalForm(isReturn?'Leihwagen zurücknehmen':'Leihwagen ausgeben','<div class="form-grid"><label>Kilometer<input name="mileage" type="number"></label><label>Tank/Ladung<input name="fuel"></label><label class="span2">Schäden / Hinweise<textarea name="damage"></textarea></label></div>',
 async f=>api('/loaner-bookings/'+id+(isReturn?'/return':'/handover'),{method:'POST',body:JSON.stringify({mileage:f.get('mileage')?Number(f.get('mileage')):null,fuelOrChargeLevel:f.get('fuel'),damage:f.get('damage')})})
 );
}

function checklistModal(templateId){
 const item=state.checklists.find(x=>(x.template||x).id===templateId); if(!item)return;
 const t=item.template||item,fields=item.fields||[];
 const body='<label>Auftrag<select name="workOrderId"><option value="">–</option>'+options(state.orders,o=>o.number+' · '+(vehicle(o.vehicleId)?.licensePlate||''))+'</select></label>'+
 '<label>Fahrzeug<select name="vehicleId"><option value="">–</option>'+options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model)+'</select></label>'+
 '<label>Mitarbeiter<select name="employeeId"><option value="">–</option>'+options(state.employees,e=>e.name)+'</select></label>'+
 fields.map(f=>'<label class="check-item"><span>'+esc(f.label)+(f.required?' *':'')+'</span><select name="field_'+f.id+'"><option value="ok">OK</option><option value="defect">Mangel</option><option value="na">n/a</option></select></label>').join('');
 modalForm('Checkliste: '+esc(t.name),body,async fd=>{
  const run=await api('/checklists/run',{method:'POST',body:JSON.stringify({checklistTemplateId:t.id,workOrderId:fd.get('workOrderId')||null,vehicleId:fd.get('vehicleId')||null,employeeId:fd.get('employeeId')||null})});
  const answers=fields.map(f=>({fieldId:f.id,valueJson:JSON.stringify(fd.get('field_'+f.id))}));
  await api('/checklists/run/'+run.id+'/complete',{method:'POST',body:JSON.stringify({answers})});
 });
}

function goodsReceiptModal(purchaseOrderId){
 const po=state.purchaseOrders.find(x=>(x.order||x).id===purchaseOrderId);
 if(!po)return toast('Bestellung nicht gefunden.',true);
 const lines=po.lines||[];
 const body='<div class="rows">'+lines.map(l=>{
  const item=state.inventory.find(i=>i.id===l.inventoryItemId), remaining=Math.max(0,Number(l.quantity)-Number(l.receivedQuantity));
  return '<label>'+esc(item?.itemNumber||'Artikel')+' · '+esc(item?.description||'')+'<input name="'+l.id+'" type="number" min="0" max="'+remaining+'" step=".01" value="'+remaining+'"><small class="muted">offen '+remaining+'</small></label>'
 }).join('')+'</div>';
 modalForm('Wareneingang '+esc((po.order||po).number),body,async f=>{
  const lines=po.lines.map(l=>({purchaseOrderLineId:l.id,quantity:Number(f.get(l.id)||0)})).filter(x=>x.quantity>0);
  if(!lines.length)throw new Error('Keine Menge eingetragen.');
  await api('/purchase-orders/'+purchaseOrderId+'/receive',{method:'POST',body:JSON.stringify({lines})});
 });
}

function timeStartModal(workOrderId){
 modalForm('Arbeitszeit starten','<label>Mitarbeiter<select name="employeeId">'+options(state.employees,e=>e.name+' · '+e.roleName)+'</select></label><label>Tätigkeit<input name="activity" value="Werkstattarbeit"></label>',
  async f=>api('/time/start',{method:'POST',body:JSON.stringify({workOrderId,employeeId:f.get('employeeId'),activity:f.get('activity')})})
 );
}
async function stopTime(workOrderId,timeId){
 try{await api('/time/'+timeId+'/stop',{method:'POST'});toast('Arbeitszeit gestoppt.');await loadAll();await openOrder(workOrderId)}catch(e){toast(e.message,true)}
}

function employeeModal(){
 modalForm('Mitarbeiter anlegen','<div class="form-grid"><label>Personalnummer<input name="personnelNumber" required></label><label>Name<input name="name" required></label><label>Rolle / Funktion<input name="roleName"></label><label>Wochenstunden<input name="weeklyHours" type="number" step=".5" value="40"></label><label>Stundensatz VK<input name="rate" type="number" step=".01" value="109"></label><label>Stundenkosten<input name="cost" type="number" step=".01" value="42"></label><label>Urlaubstage<input name="vacation" type="number" value="30"></label></div>',
  async f=>api('/employees',{method:'POST',body:JSON.stringify({siteId:state.site?.id,personnelNumber:f.get('personnelNumber'),name:f.get('name'),roleName:f.get('roleName'),weeklyHours:Number(f.get('weeklyHours')),productiveHourlyCost:Number(f.get('cost')),productiveHourlyRate:Number(f.get('rate')),annualVacationDays:Number(f.get('vacation'))})})
 );
}

function resourceModal(){
 modalForm('Ressource anlegen','<div class="form-grid"><label>Name<input name="name" required></label><label>Art<select name="kind"><option value="0">Hebebühne</option><option value="2">Diagnoseplatz</option><option value="3">Achsvermessung</option><option value="5">Reifenplatz</option><option value="7">Direktannahme</option><option value="9">Spezialwerkzeug</option></select></label><label>Max. Last kg<input name="maxLoadKg" type="number"></label><label>Max. Fahrzeughöhe m<input name="maxHeight" type="number" step=".1"></label><label><input name="ev" type="checkbox" style="width:auto"> EV geeignet</label></div>',
  async f=>api('/resources',{method:'POST',body:JSON.stringify({siteId:state.site?.id,name:f.get('name'),kind:Number(f.get('kind')),maxLoadKg:f.get('maxLoadKg')?Number(f.get('maxLoadKg')):null,maxVehicleHeightM:f.get('maxHeight')?Number(f.get('maxHeight')):null,supportsEv:f.get('ev')==='on'})})
 );
}

function roleModal(){
 modalForm('Rolle anlegen','<label>Name<input name="name" required></label><label>Beschreibung<input name="description"></label>',
  async f=>api('/admin/roles',{method:'POST',body:JSON.stringify({name:f.get('name'),description:f.get('description')})})
 );
}

function rolePermissionsModal(roleId){
 const item=state.adminRoles.find(x=>(x.role||x).id===roleId); if(!item)return;
 const selected=new Set(item.permissions||[]);
 const groups={};
 state.permissions.forEach(p=>(groups[p.module]??=[]).push(p));
 const body=Object.entries(groups).map(([module,ps])=>'<div class="perm-group"><b>'+esc(module)+'</b>'+ps.map(p=>'<label class="check-item"><span>'+esc(p.key)+'</span><input type="checkbox" name="perm" value="'+esc(p.key)+'" '+(selected.has(p.key)?'checked':'')+'></label>').join('')+'</div>').join('');
 modalForm('Rechte: '+esc((item.role||item).name),body,async f=>{
  const permissionKeys=f.getAll('perm');
  await api('/admin/roles/'+roleId+'/permissions',{method:'PUT',body:JSON.stringify({permissionKeys})});
 });
}

function userRolesModal(userId){
 const item=state.adminUsers.find(x=>(x.user||x).id===userId); if(!item)return;
 const selected=new Set(item.roleIds||[]);
 const body=state.adminRoles.map(x=>{const r=x.role||x;return '<label class="check-item"><span>'+esc(r.name)+'</span><input type="checkbox" name="role" value="'+r.id+'" '+(selected.has(r.id)?'checked':'')+'></label>'}).join('');
 modalForm('Rollen: '+esc((item.user||item).displayName),body,async f=>{
  await api('/admin/users/'+userId+'/roles',{method:'PUT',body:JSON.stringify({roleIds:f.getAll('role'),siteId:null})});
 });
}

function renderPurchaseForm(){
 const host=$('purchaseFormHost');
 if(!state.suppliers.length||!state.inventory.length||!state.site){host.innerHTML='<p class="muted">Lieferant, Artikel oder Standort fehlt.</p>';return}
 host.innerHTML='<label>Lieferant<select id="poSupplier">'+options(state.suppliers,s=>s.name)+'</select></label><label>Artikel<select id="poItem">'+options(state.inventory,i=>i.itemNumber+' · '+i.description)+'</select></label><div class="form-grid"><label>Menge<input id="poQty" type="number" step=".01" value="1"></label><label>EK netto<input id="poPrice" type="number" step=".01" value="'+(state.inventory[0]?.purchaseNet||0)+'"></label></div>';
 $('poItem').onchange=()=>{$('poPrice').value=state.inventory.find(i=>i.id===$('poItem').value)?.purchaseNet||0};
}
$('createPurchaseBtn').onclick=async()=>{
 try{await api('/purchase-orders',{method:'POST',body:JSON.stringify({supplierId:$('poSupplier').value,siteId:state.site.id,expectedAt:null,lines:[{inventoryItemId:$('poItem').value,quantity:Number($('poQty').value),unitPurchaseNet:Number($('poPrice').value)}]})});toast('Bestellung angelegt.')}catch(e){toast(e.message,true)}
};

$('saveIntake').onclick=async()=>{
 const id=$('intakeOrder').value;
 if(!id)return toast('Kein Auftrag gewählt.',true);
 try{
  await api('/work-orders/'+id+'/intake',{
   method:'POST',
   body:JSON.stringify({
    mileageIn:$('intakeMileage').value?Number($('intakeMileage').value):null,
    fuelOrChargeLevel:$('intakeFuel').value,
    customerRequest:$('intakeRequest').value
   })
  });
  toast('Fahrzeugannahme gespeichert.');
  await loadAll();
  page('orders');
  await openOrder(id);
 }catch(e){toast(e.message,true)}
};
$('absenceBtn').onclick=absenceModal;
$('newOrderBtn').onclick=workOrderModal;
$('newInventoryBtn').onclick=()=>inventoryModal();
$('newSupplierBtn').onclick=supplierModal;
$('newReminderBtn').onclick=reminderModal;
$('newLoanerBtn').onclick=loanerModal;
$('newLoanerBookingBtn').onclick=loanerBookingModal;
$('newEmployeeBtn').onclick=employeeModal;
$('newRoleBtn').onclick=roleModal;
$('newResourceBtn').onclick=resourceModal;
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>({ 'new-customer':customerModal,'new-vehicle':vehicleModal,'new-appointment':appointmentModal,'new-tire':tireModal }[b.dataset.action]?.()));
$('quickBtn').onclick=()=>appointmentModal();
$('customerSearchBtn').onclick=async()=>{try{state.customers=await api('/customers?q='+encodeURIComponent($('customerSearch').value));renderAll()}catch(e){toast(e.message,true)}};
$('vehicleSearchBtn').onclick=async()=>{try{state.vehicles=await api('/vehicles?q='+encodeURIComponent($('vehicleSearch').value));renderAll()}catch(e){toast(e.message,true)}};


function platformAdapt(){
 const ua=navigator.userAgent||'';
 const touch=navigator.maxTouchPoints>0||matchMedia('(pointer:coarse)').matches;
 document.body.classList.toggle('is-touch',touch);
 document.body.classList.toggle('is-ios',/iPad|iPhone|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1));
 document.body.classList.toggle('is-android',/Android/i.test(ua));
 document.body.classList.toggle('is-desktop',!touch&&innerWidth>=900);
 document.body.classList.toggle('is-tablet',touch&&innerWidth>=700);
 document.body.classList.toggle('is-phone',innerWidth<700);
 document.body.classList.toggle('is-standalone',matchMedia('(display-mode: standalone)').matches||navigator.standalone===true);
 document.documentElement.style.setProperty('--app-height',(window.visualViewport?.height||innerHeight)+'px');
}
platformAdapt();
window.addEventListener('resize',()=>{platformAdapt();renderWorkshopPlanner();renderPersonnelPlanner()},{passive:true});
window.visualViewport?.addEventListener('resize',platformAdapt,{passive:true});

function localDay(d){return new Date(d.getFullYear(),d.getMonth(),d.getDate())}
function addDays(d,n){const x=new Date(d);x.setDate(x.getDate()+n);return x}
function startOfWeek(d){const x=localDay(d),day=(x.getDay()+6)%7;return addDays(x,-day)}
function endOfMonth(d){return new Date(d.getFullYear(),d.getMonth()+1,0)}
function keyDate(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function sameDay(a,b){return keyDate(new Date(a))===keyDate(new Date(b))}
function dateLabel(d,opts={weekday:'short',day:'2-digit',month:'2-digit'}){return new Intl.DateTimeFormat('de-DE',opts).format(d)}
function appointmentForDay(a,d){return sameDay(a.startsAt,d)&&a.status!==4}
function absenceForDay(a,d){const k=keyDate(d);return k>=String(a.from).slice(0,10)&&k<=String(a.to).slice(0,10)}
function plannerRange(){
 const d=localDay(plannerState.date);
 if(plannerState.view==='day')return[d];
 if(plannerState.view==='workweek'){const s=startOfWeek(d);return Array.from({length:5},(_,i)=>addDays(s,i))}
 if(plannerState.view==='week'){const s=startOfWeek(d);return Array.from({length:7},(_,i)=>addDays(s,i))}
 if(plannerState.view==='month'){const first=new Date(d.getFullYear(),d.getMonth(),1),last=endOfMonth(d);return Array.from({length:last.getDate()},(_,i)=>addDays(first,i))}
 const s=startOfWeek(d);return Array.from({length:14},(_,i)=>addDays(s,i));
}
function plannerRangeText(days){
 if(!days.length)return'–';
 if(plannerState.view==='month')return new Intl.DateTimeFormat('de-DE',{month:'long',year:'numeric'}).format(days[0]);
 if(days.length===1)return new Intl.DateTimeFormat('de-DE',{weekday:'long',day:'2-digit',month:'long',year:'numeric'}).format(days[0]);
 return dateLabel(days[0],{day:'2-digit',month:'2-digit'})+' – '+dateLabel(days.at(-1),{day:'2-digit',month:'2-digit',year:'numeric'});
}
function plannerEventHtml(a){
 const v=vehicle(a.vehicleId),cu=customer(a.customerId);
 return '<button class="scheduler-event" data-planner-appt="'+a.id+'"><b>'+new Date(a.startsAt).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})+' · '+esc(a.subject)+'</b><span>'+esc(v?.licensePlate||'')+' · '+esc(cu?.displayName||'')+'</span></button>';
}
function renderWorkshopPlanner(){
 if(!$('workshopPlannerGrid'))return;
 const days=plannerRange();
 $('plannerRangeLabel').textContent=plannerRangeText(days);
 document.querySelectorAll('[data-planner-view]').forEach(b=>b.classList.toggle('active',b.dataset.plannerView===plannerState.view));
 document.querySelectorAll('[data-planner-axis]').forEach(b=>b.classList.toggle('active',b.dataset.plannerAxis===plannerState.axis));

 const inRange=state.appointments.filter(a=>days.some(d=>appointmentForDay(a,d)));
 const totalHours=inRange.reduce((sum,a)=>sum+Math.max(0,(new Date(a.endsAt)-new Date(a.startsAt))/3600000),0);
 const occupiedResources=new Set(inRange.map(a=>a.resourceId).filter(Boolean)).size;
 const occupiedEmployees=new Set(inRange.map(a=>a.employeeId).filter(Boolean)).size;
 $('plannerSummary').innerHTML=[
  ['Termine',inRange.length],['Geplante Stunden',totalHours.toLocaleString('de-DE',{maximumFractionDigits:1})+' h'],['Ressourcen belegt',occupiedResources+' / '+state.resources.length],['Mitarbeiter geplant',occupiedEmployees+' / '+state.employees.length]
 ].map(x=>'<div><span>'+x[0]+'</span><b>'+x[1]+'</b></div>').join('');

 const mobile=innerWidth<700;
 if(mobile||plannerState.view==='agenda'||plannerState.view==='month'){
  const grouped=days.map(d=>({d,events:inRange.filter(a=>appointmentForDay(a,d))})).filter(x=>x.events.length||plannerState.view!=='agenda');
  $('workshopPlannerGrid').style.minWidth='0';
  $('workshopPlannerGrid').innerHTML='<div class="mobile-planner-list" style="display:grid">'+grouped.map(g=>
   '<div class="mobile-planner-card"><h4>'+dateLabel(g.d,{weekday:'long',day:'2-digit',month:'2-digit'})+'</h4>'+
   (g.events.length?g.events.map(plannerEventHtml).join(''):'<p>Keine Termine</p>')+'</div>'
  ).join('')+'</div>';
 }else if(plannerState.axis==='calendar'){
  const slots=Array.from({length:11},(_,i)=>7+i);
  $('workshopPlannerGrid').style.setProperty('--planner-cols',days.length);
  $('workshopPlannerGrid').innerHTML='<div class="scheduler-head"><div>Zeit</div>'+days.map(d=>'<div>'+dateLabel(d,{weekday:'short',day:'2-digit',month:'2-digit'})+'</div>').join('')+'</div>'+
   slots.map(hour=>'<div class="scheduler-row"><div class="scheduler-label"><b>'+String(hour).padStart(2,'0')+':00</b><span>'+String(hour+1).padStart(2,'0')+':00</span></div>'+
    days.map(d=>{const ev=inRange.filter(a=>appointmentForDay(a,d)&&new Date(a.startsAt).getHours()===hour);return'<div class="scheduler-cell '+(sameDay(d,new Date())?'today ':'')+([0,6].includes(d.getDay())?'weekend':'')+'">'+ev.map(plannerEventHtml).join('')+'</div>'}).join('')+'</div>').join('');
 }else{
  const rows=plannerState.axis==='resources'?state.resources:state.employees;
  $('workshopPlannerGrid').style.setProperty('--planner-cols',days.length);
  $('workshopPlannerGrid').innerHTML='<div class="scheduler-head"><div>'+(plannerState.axis==='resources'?'Ressource':'Mitarbeiter')+'</div>'+days.map(d=>'<div>'+dateLabel(d,{weekday:'short',day:'2-digit',month:'2-digit'})+'</div>').join('')+'</div>'+
   rows.map(row=>'<div class="scheduler-row"><div class="scheduler-label"><b>'+esc(row.name)+'</b><span>'+esc(plannerState.axis==='resources'?resourceKindName(row.kind):row.roleName)+'</span></div>'+
    days.map(d=>{const ev=inRange.filter(a=>appointmentForDay(a,d)&&(plannerState.axis==='resources'?a.resourceId===row.id:a.employeeId===row.id));return'<div class="scheduler-cell '+(sameDay(d,new Date())?'today':'')+'">'+ev.map(plannerEventHtml).join('')+'</div>'}).join('')+'</div>').join('');
 }
 document.querySelectorAll('[data-planner-appt]').forEach(b=>b.onclick=()=>appointmentModal(state.appointments.find(a=>a.id===b.dataset.plannerAppt)));
}

function personnelRange(){
 const d=localDay(personnelPlannerState.date);
 if(personnelPlannerState.view==='month'){
  const first=new Date(d.getFullYear(),d.getMonth(),1),last=endOfMonth(d);
  return Array.from({length:last.getDate()},(_,i)=>addDays(first,i));
 }
 const s=startOfWeek(d);return Array.from({length:7},(_,i)=>addDays(s,i));
}
function renderPersonnelPlanner(){
 if(!$('personnelPlannerGrid'))return;
 const days=personnelRange();
 $('personnelRangeLabel').textContent=personnelPlannerState.view==='month'
  ?new Intl.DateTimeFormat('de-DE',{month:'long',year:'numeric'}).format(days[0])
  :dateLabel(days[0],{day:'2-digit',month:'2-digit'})+' – '+dateLabel(days.at(-1),{day:'2-digit',month:'2-digit',year:'numeric'});
 $('personnelWeekBtn').classList.toggle('active',personnelPlannerState.view==='week');
 $('personnelMonthBtn').classList.toggle('active',personnelPlannerState.view==='month');

 const abs=state.absences.filter(a=>days.some(d=>absenceForDay(a,d)));
 const planned=state.appointments.filter(a=>days.some(d=>appointmentForDay(a,d)));
 const weeklyCapacity=state.employees.reduce((s,e)=>s+Number(e.weeklyHours||0),0);
 const plannedHours=planned.reduce((s,a)=>s+Math.max(0,(new Date(a.endsAt)-new Date(a.startsAt))/3600000),0);
 const absentDays=abs.reduce((s,a)=>s+days.filter(d=>absenceForDay(a,d)).length,0);
 $('personnelSummary').innerHTML=[
  ['Mitarbeiter',state.employees.length],['Sollkapazität',weeklyCapacity.toLocaleString('de-DE',{maximumFractionDigits:1})+' h'],['Geplant',plannedHours.toLocaleString('de-DE',{maximumFractionDigits:1})+' h'],['Abwesenheitstage',absentDays]
 ].map(x=>'<div><span>'+x[0]+'</span><b>'+x[1]+'</b></div>').join('');

 if(innerWidth<700){
  $('personnelPlannerGrid').style.minWidth='0';
  $('personnelPlannerGrid').innerHTML='<div class="mobile-planner-list" style="display:grid">'+state.employees.map(e=>{
   const eAbs=abs.filter(a=>a.employeeId===e.id),eAp=planned.filter(a=>a.employeeId===e.id);
   return'<div class="mobile-planner-card"><h4>'+esc(e.name)+'</h4><p>'+esc(e.roleName)+' · '+esc(e.weeklyHours)+' h/Woche</p>'+
    eAbs.map(a=>'<div class="scheduler-event absence"><b>'+esc(['Urlaub','Krank','Schulung','Berufsschule','Überstundenabbau','Sonderurlaub','Elternzeit','Dienstreise','Sonstiges'][a.type]||'Abwesenheit')+'</b><span>'+esc(a.from)+' – '+esc(a.to)+'</span></div>').join('')+
    eAp.slice(0,6).map(plannerEventHtml).join('')+'</div>';
  }).join('')+'</div>';
  return;
 }
 const cols='180px repeat('+days.length+',minmax(96px,1fr))';
 $('personnelPlannerGrid').innerHTML='<div class="personnel-grid-head" style="grid-template-columns:'+cols+'"><div>Mitarbeiter</div>'+days.map(d=>'<div>'+dateLabel(d,{weekday:'short',day:'2-digit',month:'2-digit'})+'</div>').join('')+'</div>'+
  state.employees.map(e=>'<div class="personnel-grid-row" style="grid-template-columns:'+cols+'"><div class="personnel-name"><b>'+esc(e.name)+'</b><span>'+esc(e.roleName)+' · '+esc(e.weeklyHours)+' h</span></div>'+
   days.map(d=>{const a=state.absences.find(x=>x.employeeId===e.id&&absenceForDay(x,d));const ap=state.appointments.filter(x=>x.employeeId===e.id&&appointmentForDay(x,d));return'<div class="personnel-day">'+(a?'<span class="capacity-pill absent">'+esc(['Urlaub','Krank','Schulung','Berufsschule','Überstundenabbau','Sonderurlaub','Elternzeit','Dienstreise','Sonstiges'][a.type]||'Abwesend')+'</span>':'<span class="capacity-pill">'+(ap.length?ap.length+' Termin'+(ap.length>1?'e':''):'verfügbar')+'</span>')+ap.slice(0,2).map(plannerEventHtml).join('')+'</div>'}).join('')+'</div>').join('');
 document.querySelectorAll('[data-planner-appt]').forEach(b=>b.onclick=()=>appointmentModal(state.appointments.find(a=>a.id===b.dataset.plannerAppt)));
}

document.querySelectorAll('[data-planner-view]').forEach(b=>b.onclick=()=>{plannerState.view=b.dataset.plannerView;renderWorkshopPlanner()});
document.querySelectorAll('[data-planner-axis]').forEach(b=>b.onclick=()=>{plannerState.axis=b.dataset.plannerAxis;renderWorkshopPlanner()});
$('plannerPrevBtn').onclick=()=>{plannerState.date=plannerState.view==='month'?new Date(plannerState.date.getFullYear(),plannerState.date.getMonth()-1,1):addDays(plannerState.date,plannerState.view==='day'?-1:-7);renderWorkshopPlanner()};
$('plannerNextBtn').onclick=()=>{plannerState.date=plannerState.view==='month'?new Date(plannerState.date.getFullYear(),plannerState.date.getMonth()+1,1):addDays(plannerState.date,plannerState.view==='day'?1:7);renderWorkshopPlanner()};
$('plannerTodayBtn').onclick=()=>{plannerState.date=new Date();renderWorkshopPlanner()};
$('personnelPrevBtn').onclick=()=>{personnelPlannerState.date=personnelPlannerState.view==='month'?new Date(personnelPlannerState.date.getFullYear(),personnelPlannerState.date.getMonth()-1,1):addDays(personnelPlannerState.date,-7);renderPersonnelPlanner()};
$('personnelNextBtn').onclick=()=>{personnelPlannerState.date=personnelPlannerState.view==='month'?new Date(personnelPlannerState.date.getFullYear(),personnelPlannerState.date.getMonth()+1,1):addDays(personnelPlannerState.date,7);renderPersonnelPlanner()};
$('personnelTodayBtn').onclick=()=>{personnelPlannerState.date=new Date();renderPersonnelPlanner()};
$('personnelWeekBtn').onclick=()=>{personnelPlannerState.view='week';renderPersonnelPlanner()};
$('personnelMonthBtn').onclick=()=>{personnelPlannerState.view='month';renderPersonnelPlanner()};

$('globalSearch').addEventListener('input',()=>{
 const q=$('globalSearch').value.trim().toLowerCase();if(q.length<2){$('searchResults').classList.add('hidden');return}
 const hits=[];
 state.customers.forEach(c=>{if((c.displayName+' '+c.customerNumber+' '+c.phone).toLowerCase().includes(q))hits.push(['Kunde',c.displayName,'customers'])});
 state.vehicles.forEach(v=>{if((v.licensePlate+' '+v.vin+' '+v.make+' '+v.model).toLowerCase().includes(q))hits.push(['Fahrzeug',v.licensePlate+' · '+v.make+' '+v.model,'vehicles'])});
 state.orders.forEach(o=>{if(o.number.toLowerCase().includes(q)||vehicle(o.vehicleId)?.licensePlate.toLowerCase().includes(q))hits.push(['Auftrag',o.number+' · '+(vehicle(o.vehicleId)?.licensePlate||''),'orders',o.id])});
 state.invoices.forEach(i=>{if(i.number.toLowerCase().includes(q))hits.push(['Rechnung',i.number,'billing'])});
 $('searchResults').innerHTML=hits.slice(0,10).map((x,i)=>'<button data-hit="'+i+'"><small>'+esc(x[0])+'</small><br>'+esc(x[1])+'</button>').join('')||'<button>Keine Treffer</button>';
 $('searchResults').classList.remove('hidden');
 document.querySelectorAll('[data-hit]').forEach(b=>b.onclick=()=>{const x=hits[Number(b.dataset.hit)];page(x[2]);$('searchResults').classList.add('hidden');if(x[3])openOrder(x[3])});
});

(async()=>{
 await health();
 if(token){
  showApp();
  try{await loadAll()}catch(e){
   sessionStorage.removeItem('wm_erp_token');
   token='';
   await performLogin(DEMO_USER,DEMO_PASS,true);
  }
 }else{
  showLogin();
  await performLogin(DEMO_USER,DEMO_PASS,true);
 }
})();
