const API='/jl/demo/api';
const DEMO_USER='demo', DEMO_PASS='WerkstattDemo!2026';
const $=id=>document.getElementById(id);
const fmtMoney=v=>new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(Number(v||0));
const fmtDate=v=>v?new Intl.DateTimeFormat('de-DE',{dateStyle:'medium'}).format(new Date(v)):'–';
const fmtDateTime=v=>v?new Intl.DateTimeFormat('de-DE',{dateStyle:'short',timeStyle:'short'}).format(new Date(v)):'–';
let token=sessionStorage.getItem('wm_erp_token')||'';
let state={site:null,sites:[],customers:[],vehicles:[],employees:[],resources:[],appointments:[],orders:[],inventory:[],suppliers:[],tires:[],invoices:[],dashboard:null,selectedOrder:null};

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
$('loginForm').onsubmit=async e=>{
 e.preventDefault();$('loginError').textContent='';
 try{
  const d=await api('/auth/login',{method:'POST',body:JSON.stringify({username:$('user').value,password:$('pass').value})});
  token=d.access_token;sessionStorage.setItem('wm_erp_token',token);showApp();await loadAll();
 }catch(err){$('loginError').textContent=err.message}
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
  const [sites,customers,vehicles,employees,resources,appointments,orders,inventory,suppliers,tires,invoices,dashboard]=await Promise.all([
   api('/sites'),api('/customers'),api('/vehicles'),api('/employees'),api('/resources'),api('/appointments'),
   api('/work-orders'),api('/inventory'),api('/suppliers'),api('/tires'),api('/invoices'),api('/dashboard')
  ]);
  Object.assign(state,{sites,customers,vehicles,employees,resources,appointments,orders,inventory,suppliers,tires,invoices,dashboard});
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
 $('kpiAppointments').textContent=d.appointments??0;$('kpiOrders').textContent=d.openOrders??0;$('kpiStock').textContent=d.lowStock??0;$('kpiReceivables').textContent=fmtMoney(d.receivables||0);
 $('reportAppointments').textContent=d.appointments??0;$('reportOrders').textContent=d.openOrders??0;$('reportStock').textContent=d.lowStock??0;$('reportReceivables').textContent=fmtMoney(d.receivables||0);

 $('dashboardOrders').innerHTML=state.orders.slice(0,7).map(o=>{
  const v=vehicle(o.vehicleId),c=customer(o.customerId);
  return '<div class="row-item"><div class="row-main"><div><b>'+esc(o.number)+' · '+esc(v?.licensePlate||'')+'</b><span>'+esc(v?((v.make||'')+' '+(v.model||'')):'')+' · '+esc(c?.displayName||'')+'</span></div></div><span class="badge '+badge(workStatus[o.status])+'">'+esc(workStatus[o.status]||o.status)+'</span></div>'
 }).join('')||empty('Noch keine Aufträge.');

 $('dashboardAppointments').innerHTML=state.appointments.slice(0,7).map(a=>{
  const v=vehicle(a.vehicleId),c=customer(a.customerId);
  return '<div class="row-item"><div class="row-main"><div><b>'+new Date(a.startsAt).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})+' · '+esc(a.subject)+'</b><span>'+esc(v?.licensePlate||'')+' · '+esc(c?.displayName||'')+'</span></div></div><span class="badge '+badge(appointmentStatus[a.status])+'">'+esc(appointmentStatus[a.status]||a.status)+'</span></div>'
 }).join('')||empty('Noch keine Termine.');

 $('appointmentRows').innerHTML=state.appointments.map(a=>{
  const c=customer(a.customerId),v=vehicle(a.vehicleId),r=resource(a.resourceId);
  const action=a.workOrderId?'':'<button class="secondary small" data-convert="'+a.id+'">Auftrag</button>';
  return '<tr><td>'+fmtDateTime(a.startsAt)+'</td><td>'+esc(a.subject)+'</td><td>'+esc(c?.displayName||'')+'</td><td>'+esc(v?.licensePlate||'')+'</td><td>'+esc(r?.name||'–')+'</td><td><span class="badge '+badge(appointmentStatus[a.status])+'">'+esc(appointmentStatus[a.status]||a.status)+'</span></td><td>'+action+'</td></tr>'
 }).join('');
 document.querySelectorAll('[data-convert]').forEach(b=>b.onclick=()=>convertAppointment(b.dataset.convert));

 renderOrderBoard();
 $('customerRows').innerHTML=state.customers.map(c=>'<tr><td>'+esc(c.customerNumber)+'</td><td>'+esc(c.displayName)+'</td><td>'+esc(c.phone||c.mobile||'')+'</td><td>'+esc(c.email||'')+'</td><td>'+esc(c.city||'')+'</td></tr>').join('');
 $('vehicleRows').innerHTML=state.vehicles.map(v=>'<tr><td><b>'+esc(v.licensePlate)+'</b></td><td>'+esc((v.make||'')+' '+(v.model||''))+'</td><td>'+esc(v.vin||'')+'</td><td>'+esc(v.mileage??'–')+'</td><td>'+esc(v.nextHu||'–')+'</td></tr>').join('');
 $('tireCards').innerHTML=state.tires.map(t=>'<article><div class="panel-head"><h3>'+esc(t.storageNumber)+'</h3><span class="badge '+badge(t.condition===0?'gut':t.condition===1?'beobachten':'ersetzen')+'">'+esc(t.condition===0?'gut':t.condition===1?'beobachten':'ersetzen')+'</span></div><p><b>'+esc(t.size)+'</b> · '+esc(t.brandModel)+'</p><p>'+esc(t.storageLocation)+' · DOT '+esc(t.dot||'–')+'</p><small>Profil '+[t.frontLeftMm,t.frontRightMm,t.rearLeftMm,t.rearRightMm].join(' / ')+' mm</small></article>').join('')||emptyCard('Noch keine Radsätze eingelagert.');
 $('inventoryRows').innerHTML=state.inventory.map(i=>'<tr><td><b>'+esc(i.itemNumber)+'</b></td><td>'+esc(i.description)+'</td><td><span class="badge '+badge(Number(i.stock)<=Number(i.minimumStock)?'kritisch':'vorhanden')+'">'+esc(i.stock)+'</span></td><td>'+esc(i.minimumStock)+'</td><td>'+fmtMoney(i.purchaseNet)+'</td><td>'+fmtMoney(i.saleNet)+'</td><td>'+esc(i.storageLocation||'')+'</td></tr>').join('');
 $('supplierRows').innerHTML=state.suppliers.map(s=>'<div class="row-item"><div class="row-main"><div><b>'+esc(s.name)+'</b><span>'+esc(s.supplierNumber)+' · '+esc(s.phone||s.email||'')+'</span></div></div></div>').join('')||empty('Noch keine Lieferanten.');
 renderPurchaseForm();
 $('employeeRows').innerHTML=state.employees.map(e=>'<tr><td><b>'+esc(e.name)+'</b></td><td>'+esc(e.roleName)+'</td><td>'+esc(e.weeklyHours)+' h</td><td>'+esc(e.annualVacationDays)+' Tage</td><td>'+fmtMoney(e.productiveHourlyRate)+'/h</td></tr>').join('');
 $('invoiceRows').innerHTML=state.invoices.map(i=>'<tr><td><b>'+esc(i.number)+'</b></td><td>'+esc(i.issueDate)+'</td><td>'+esc(i.dueDate)+'</td><td>'+fmtMoney(i.grossTotal)+'</td><td>'+fmtMoney(i.paidTotal)+'</td><td><span class="badge '+badge(invoiceStatus[i.status])+'">'+esc(invoiceStatus[i.status]||i.status)+'</span></td><td>'+(i.status!==3?'<button class="secondary" data-pay="'+i.id+'">Zahlung</button>':'')+'</td></tr>').join('');
 document.querySelectorAll('[data-pay]').forEach(b=>b.onclick=()=>paymentModal(b.dataset.pay));
 $('intakeOrder').innerHTML=state.orders.filter(o=>o.status<10&&o.status!==12).map(o=>'<option value="'+o.id+'">'+esc(o.number)+' · '+esc(vehicle(o.vehicleId)?.licensePlate||'')+'</option>').join('');
 if(!$('checkItems').children.length)$('checkItems').innerHTML=['Beleuchtung','Bremsen','Bereifung','Flüssigkeiten','Warnleuchten','Wischer/Wascher','Unterboden','Fehlerspeicher'].map(x=>'<label class="check-item"><span>'+x+'</span><input type="checkbox"></label>').join('');
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
   '<div class="page-actions" style="margin-top:16px"><button class="primary" id="addLineBtn">+ Position</button><button class="secondary" id="approvalBtn">Freigabe</button>'+(next!==null?'<button class="secondary" id="nextStatusBtn">→ '+esc(workStatus[next])+'</button>':'')+(o.status===9?'<button class="primary" id="invoiceBtn">Rechnung erzeugen</button>':'')+'</div>';
  $('orderDetail').classList.remove('hidden');
  $('addLineBtn').onclick=()=>lineModal(id);$('approvalBtn').onclick=()=>approvalModal(id);
  if($('nextStatusBtn'))$('nextStatusBtn').onclick=()=>transition(id,next);
  if($('invoiceBtn'))$('invoiceBtn').onclick=()=>createInvoice(id);
 }catch(e){toast(e.message,true)}
}
function nextStatus(s){const m={0:1,1:2,2:3,3:4,4:5,5:6,6:7,7:8,8:9,9:10,10:11};return m[s]??null}
async function transition(id,status){try{await api('/work-orders/'+id+'/transition',{method:'POST',body:JSON.stringify({status})});toast('Auftragsstatus aktualisiert.');await loadAll();await openOrder(id)}catch(e){toast(e.message,true)}}
async function convertAppointment(id){try{await api('/work-orders/from-appointment/'+id,{method:'POST'});toast('Werkstattauftrag erzeugt.');await loadAll();page('orders')}catch(e){toast(e.message,true)}}

function options(arr,label){return arr.map(x=>'<option value="'+x.id+'">'+esc(label(x))+'</option>').join('')}
function modalForm(title,body,onSubmit){
 showModal(title,'<form id="dynamicForm">'+body+'<div class="modal-actions"><button type="button" class="secondary" id="cancelModal">Abbrechen</button><button class="primary" type="submit">Speichern</button></div></form>');
 $('cancelModal').onclick=closeModal;$('dynamicForm').onsubmit=async e=>{e.preventDefault();try{await onSubmit(new FormData(e.target));closeModal();await loadAll();toast('Gespeichert.')}catch(err){toast(err.message,true)}}
}
function customerModal(){modalForm('Neuen Kunden anlegen',
 '<div class="form-grid"><label class="span2">Anzeigename<input name="displayName" required></label><label>Vorname<input name="firstName"></label><label>Nachname<input name="lastName"></label><label>Telefon<input name="phone"></label><label>E-Mail<input name="email" type="email"></label><label>PLZ<input name="postalCode"></label><label>Ort<input name="city"></label></div>',
 async f=>api('/customers',{method:'POST',body:JSON.stringify({displayName:f.get('displayName'),firstName:f.get('firstName'),lastName:f.get('lastName'),phone:f.get('phone'),email:f.get('email'),postalCode:f.get('postalCode'),city:f.get('city')})})
}
function vehicleModal(){modalForm('Fahrzeug anlegen',
 '<div class="form-grid"><label class="span2">Kunde<select name="customerId">'+options(state.customers,c=>c.displayName)+'</select></label><label>Kennzeichen<input name="licensePlate" required></label><label>VIN<input name="vin"></label><label>Hersteller<input name="make"></label><label>Modell<input name="model"></label><label>Kilometer<input name="mileage" type="number"></label><label>HU<input name="nextHu" type="date"></label></div>',
 async f=>api('/vehicles',{method:'POST',body:JSON.stringify({customerId:f.get('customerId'),licensePlate:f.get('licensePlate'),vin:f.get('vin'),make:f.get('make'),model:f.get('model'),mileage:Number(f.get('mileage')||0),nextHu:f.get('nextHu')||null})})
}
function appointmentModal(){modalForm('Termin anlegen',
 '<div class="form-grid"><label>Kunde<select id="apptCustomer" name="customerId">'+options(state.customers,c=>c.displayName)+'</select></label><label>Fahrzeug<select name="vehicleId">'+options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model)+'</select></label><label>Start<input name="startsAt" type="datetime-local" required></label><label>Ende<input name="endsAt" type="datetime-local" required></label><label>Ressource<select name="resourceId"><option value="">–</option>'+options(state.resources,r=>r.name)+'</select></label><label>Mitarbeiter<select name="employeeId"><option value="">–</option>'+options(state.employees,e=>e.name)+'</select></label><label class="span2">Betreff<input name="subject" required placeholder="z. B. Inspektion + Ölservice"></label><label class="span2">Kundenwunsch<textarea name="customerRequest"></textarea></label></div>',
 async f=>api('/appointments',{method:'POST',body:JSON.stringify({siteId:state.site?.id,customerId:f.get('customerId'),vehicleId:f.get('vehicleId'),resourceId:f.get('resourceId')||null,employeeId:f.get('employeeId')||null,startsAt:new Date(f.get('startsAt')).toISOString(),endsAt:new Date(f.get('endsAt')).toISOString(),subject:f.get('subject'),customerRequest:f.get('customerRequest')})})
}
function lineModal(id){modalForm('Auftragsposition hinzufügen',
 '<div class="form-grid"><label>Art<select name="type"><option value="0">Arbeit</option><option value="1">Teil</option><option value="2">Material</option><option value="3">Gebühr</option><option value="5">Text</option></select></label><label>Artikelnummer<input name="itemNumber"></label><label class="span2">Beschreibung<input name="description" required></label><label>Menge<input name="quantity" type="number" step=".01" value="1"></label><label>Netto Einzel<input name="unitNet" type="number" step=".01" value="0"></label><label>USt %<input name="vatRate" type="number" step=".01" value="19"></label><label>Rabatt %<input name="discountPercent" type="number" step=".01" value="0"></label></div>',
 async f=>{await api('/work-orders/'+id+'/lines',{method:'POST',body:JSON.stringify({type:Number(f.get('type')),itemNumber:f.get('itemNumber'),description:f.get('description'),quantity:Number(f.get('quantity')),unitNet:Number(f.get('unitNet')),vatRate:Number(f.get('vatRate')),discountPercent:Number(f.get('discountPercent'))})});await openOrder(id)}
)}
function approvalModal(id){modalForm('Kundenfreigabe anlegen','<label>Freigabebetrag brutto<input name="offeredGross" type="number" step=".01" required></label><label>Kanal<select name="channel"><option>Link</option><option>Telefon</option><option>E-Mail</option></select></label>',
 async f=>{const a=await api('/work-orders/'+id+'/approvals',{method:'POST',body:JSON.stringify({offeredGross:Number(f.get('offeredGross')),channel:f.get('channel')})});await api('/approvals/'+a.id+'/respond',{method:'POST',body:JSON.stringify({status:1,note:'Staging: Freigabe bestätigt'})});toast('Kundenfreigabe simuliert.');await openOrder(id)}
)}
async function createInvoice(id){try{await api('/invoices/from-work-order/'+id,{method:'POST'});toast('Rechnung erzeugt.');await loadAll();page('billing')}catch(e){toast(e.message,true)}}
function paymentModal(id){modalForm('Zahlung erfassen','<label>Betrag<input name="amount" type="number" step=".01" required></label><label>Zahlungsart<select name="method"><option value="0">Bar</option><option value="1">Karte</option><option value="2">Überweisung</option><option value="3">Lastschrift</option></select></label><label>Referenz<input name="reference"></label>',
 async f=>api('/invoices/'+id+'/payments',{method:'POST',body:JSON.stringify({amount:Number(f.get('amount')),method:Number(f.get('method')),reference:f.get('reference')})})
)}
function tireModal(){modalForm('Radsatz einlagern',
 '<div class="form-grid"><label>Kunde<select name="customerId">'+options(state.customers,c=>c.displayName)+'</select></label><label>Fahrzeug<select name="vehicleId">'+options(state.vehicles,v=>v.licensePlate+' · '+v.make+' '+v.model)+'</select></label><label>Lagernummer<input name="storageNumber" required></label><label>Lagerplatz<input name="storageLocation" required></label><label>Saison<select name="season"><option value="0">Sommer</option><option value="1">Winter</option><option value="2">Ganzjahr</option></select></label><label>Größe<input name="size" required placeholder="205/55 R16"></label><label>Marke / Modell<input name="brandModel" required></label><label>DOT<input name="dot"></label><label>VL mm<input name="fl" type="number" step=".1" value="6"></label><label>VR mm<input name="fr" type="number" step=".1" value="6"></label><label>HL mm<input name="rl" type="number" step=".1" value="6"></label><label>HR mm<input name="rr" type="number" step=".1" value="6"></label></div>',
 async f=>api('/tires',{method:'POST',body:JSON.stringify({customerId:f.get('customerId'),vehicleId:f.get('vehicleId'),storageNumber:f.get('storageNumber'),season:Number(f.get('season')),brandModel:f.get('brandModel'),size:f.get('size'),dot:f.get('dot'),frontLeftMm:Number(f.get('fl')),frontRightMm:Number(f.get('fr')),rearLeftMm:Number(f.get('rl')),rearRightMm:Number(f.get('rr')),condition:0,storageLocation:f.get('storageLocation'),hasTpms:false})})
)}
function absenceModal(){modalForm('Abwesenheit eintragen','<div class="form-grid"><label>Mitarbeiter<select name="employeeId">'+options(state.employees,e=>e.name)+'</select></label><label>Art<select name="type"><option value="0">Urlaub</option><option value="1">Krank</option><option value="2">Schulung</option><option value="3">Berufsschule</option></select></label><label>Von<input name="from" type="date" required></label><label>Bis<input name="to" type="date" required></label><label class="span2">Grund<input name="reason"></label></div>',
 async f=>api('/absences',{method:'POST',body:JSON.stringify({employeeId:f.get('employeeId'),type:Number(f.get('type')),from:f.get('from'),to:f.get('to'),reason:f.get('reason'),approved:true,affectsCapacity:true})})
)}
function renderPurchaseForm(){
 const host=$('purchaseFormHost');
 if(!state.suppliers.length||!state.inventory.length||!state.site){host.innerHTML='<p class="muted">Lieferant, Artikel oder Standort fehlt.</p>';return}
 host.innerHTML='<label>Lieferant<select id="poSupplier">'+options(state.suppliers,s=>s.name)+'</select></label><label>Artikel<select id="poItem">'+options(state.inventory,i=>i.itemNumber+' · '+i.description)+'</select></label><div class="form-grid"><label>Menge<input id="poQty" type="number" step=".01" value="1"></label><label>EK netto<input id="poPrice" type="number" step=".01" value="'+(state.inventory[0]?.purchaseNet||0)+'"></label></div>';
 $('poItem').onchange=()=>{$('poPrice').value=state.inventory.find(i=>i.id===$('poItem').value)?.purchaseNet||0};
}
$('createPurchaseBtn').onclick=async()=>{
 try{await api('/purchase-orders',{method:'POST',body:JSON.stringify({supplierId:$('poSupplier').value,siteId:state.site.id,expectedAt:null,lines:[{inventoryItemId:$('poItem').value,quantity:Number($('poQty').value),unitPurchaseNet:Number($('poPrice').value)}]})});toast('Bestellung angelegt.')}catch(e){toast(e.message,true)}
};

$('saveIntake').onclick=async()=>{const id=$('intakeOrder').value;if(!id)return toast('Kein Auftrag gewählt.',true);try{await transition(id,3);toast('Fahrzeugannahme gespeichert.');page('orders')}catch(e){toast(e.message,true)}};
$('absenceBtn').onclick=absenceModal;
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>({ 'new-customer':customerModal,'new-vehicle':vehicleModal,'new-appointment':appointmentModal,'new-tire':tireModal }[b.dataset.action]?.()));
$('quickBtn').onclick=()=>appointmentModal();
$('customerSearchBtn').onclick=async()=>{try{state.customers=await api('/customers?q='+encodeURIComponent($('customerSearch').value));renderAll()}catch(e){toast(e.message,true)}};
$('vehicleSearchBtn').onclick=async()=>{try{state.vehicles=await api('/vehicles?q='+encodeURIComponent($('vehicleSearch').value));renderAll()}catch(e){toast(e.message,true)}};

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
 if(token){showApp();await loadAll()}else showLogin();
})();
