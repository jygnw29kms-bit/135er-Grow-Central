const DEMO_USER='demo', DEMO_PASS='WerkstattDemo!2026';
const seed={
appointments:[
 {id:1,start:'08:00',resource:'Bühne 1',plate:'B-WM 1028',vehicle:'VW Golf VIII',customer:'M. Weber',mechanic:'Marco Stein',status:'In Arbeit',job:'Inspektion + Ölservice'},
 {id:2,start:'09:30',resource:'Diagnoseplatz',plate:'B-WM 1184',vehicle:'Audi A4',customer:'S. Lehmann',mechanic:'Alex Berger',status:'Diagnose',job:'Motorkontrollleuchte'},
 {id:3,start:'11:00',resource:'Bühne 3',plate:'B-WM 1249',vehicle:'Skoda Octavia',customer:'K. Sommer',mechanic:'Lea Hoffmann',status:'Termin bestätigt',job:'Reifenwechsel'},
 {id:4,start:'13:00',resource:'Achsmessplatz',plate:'B-WM 1315',vehicle:'Ford Transit',customer:'BauService Nord',mechanic:'Lea Hoffmann',status:'Teile vollständig',job:'Achsvermessung'},
 {id:5,start:'14:30',resource:'Bühne 2',plate:'B-WM 1391',vehicle:'BMW 320d',customer:'J. Richter',mechanic:'Marco Stein',status:'Freigabe offen',job:'Bremse Hinterachse'}],
customers:[
 {name:'M. Weber',car:'VW Golf VIII',plate:'B-WM 1028',vin:'WVWZZZ…1028',history:'4 Werkstattbesuche'},
 {name:'S. Lehmann',car:'Audi A4',plate:'B-WM 1184',vin:'WAUZZZ…1184',history:'2 Werkstattbesuche'},
 {name:'K. Sommer',car:'Skoda Octavia',plate:'B-WM 1249',vin:'TMBZZZ…1249',history:'6 Werkstattbesuche'},
 {name:'BauService Nord',car:'Ford Transit',plate:'B-WM 1315',vin:'WF0XXX…1315',history:'Flottenkunde'}],
personnel:[
 ['Alex Berger','Werkstattleitung','verfügbar','Diagnose · HV · Klima','14 Tage'],
 ['Marco Stein','Mechaniker','verfügbar','Mechanik · Reifen','11 Tage'],
 ['Lea Hoffmann','Mechanikerin','bis 13:00','Diagnose · Achse','16 Tage'],
 ['Ben Krüger','Azubi','Berufsschule','unter Aufsicht','18 Tage']],
tires:[
 ['WH-1028','VW Golf VIII · B-WM 1028','205/55 R16 · Continental','Halle A / Regal 3 / Platz 12'],
 ['WH-1184','Audi A4 · B-WM 1184','245/40 R18 · Michelin','Halle B / Regal 1 / Platz 04'],
 ['WH-1249','Skoda Octavia · B-WM 1249','225/45 R17 · Goodyear','Halle A / Regal 6 / Platz 09']],
parts:[
 ['Ölfilter OF-221','8','4','A-03-04','vorhanden'],
 ['Zündspule ZS-884','1','2','B-01-07','Mindestbestand'],
 ['Bremsscheibe BR-320','0','2','C-02-11','bestellt'],
 ['5W-30 Motoröl','46 l','20 l','Tank 1','vorhanden']],
billing:[
 ['ANG-2026-0412','S. Lehmann','Audi A4','189,00 €','Freigabe offen'],
 ['RE-2026-1188','M. Weber','VW Golf VIII','486,40 €','offen'],
 ['RE-2026-1187','K. Sommer','Skoda Octavia','129,00 €','bezahlt']]
};
let state;
const clone=x=>JSON.parse(JSON.stringify(x));
function resetData(){state=clone(seed);sessionStorage.setItem('wm_demo_state',JSON.stringify(state));render();toast('Demo auf Ausgangszustand zurückgesetzt.')}
function loadData(){try{state=JSON.parse(sessionStorage.getItem('wm_demo_state'))||clone(seed)}catch{state=clone(seed)}}
function persist(){sessionStorage.setItem('wm_demo_state',JSON.stringify(state))}
function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>t.classList.remove('show'),2600)}
function login(e){e.preventDefault();if(user.value.trim()===DEMO_USER&&pass.value===DEMO_PASS){sessionStorage.setItem('wm_demo','1');showApp()}else loginError.textContent='Demo-Zugangsdaten sind nicht korrekt.'}
function showApp(){loginView.classList.add('hidden');appView.classList.remove('hidden');loadData();render()}
function logout(){sessionStorage.removeItem('wm_demo');sessionStorage.removeItem('wm_demo_state');location.reload()}
function statusClass(s){if(/fertig|bezahlt|vorhanden|freigegeben|verfügbar/i.test(s))return'green';if(/offen|bestellt|bis|Termin/i.test(s))return'amber';if(/schule|Mindest|wartet/i.test(s))return'red';return'blue'}
function render(){
 kpiAppointments.textContent=state.appointments.length;
 todayLabel.textContent=new Intl.DateTimeFormat('de-DE',{dateStyle:'full'}).format(new Date());
 dashboardJobs.innerHTML=state.appointments.slice(0,5).map(a=>`<div class="job-row"><b>${a.start}</b><span>${a.resource}</span><div><b>${a.vehicle}</b><br><small>${a.plate} · ${a.customer}</small></div><span class="pill ${statusClass(a.status)}">${a.status}</span></div>`).join('');
 plannerRows.innerHTML=state.appointments.map(a=>`<tr><td>${a.start}</td><td>${a.resource}</td><td>${a.plate}</td><td>${a.vehicle}</td><td>${a.customer}</td><td>${a.mechanic}</td><td><span class="pill ${statusClass(a.status)}">${a.status}</span></td><td>${a.job}</td></tr>`).join('');
 customerCards.innerHTML=state.customers.map(c=>`<article><h3>${c.name}</h3><p><b>${c.car}</b><br>${c.plate}</p><small>FIN ${c.vin}<br>${c.history}</small></article>`).join('');
 personnelRows.innerHTML=state.personnel.map(p=>`<tr><td>${p[0]}</td><td>${p[1]}</td><td><span class="pill ${statusClass(p[2])}">${p[2]}</span></td><td>${p[3]}</td><td>${p[4]}</td></tr>`).join('');
 tireCards.innerHTML=state.tires.map(t=>`<article><h3>${t[0]}</h3><p>${t[1]}</p><p>${t[2]}</p><small>Lager: ${t[3]}</small></article>`).join('');
 partRows.innerHTML=state.parts.map(p=>`<tr><td>${p[0]}</td><td>${p[1]}</td><td>${p[2]}</td><td>${p[3]}</td><td><span class="pill ${statusClass(p[4])}">${p[4]}</span></td></tr>`).join('');
 billingRows.innerHTML=state.billing.map(b=>`<tr><td>${b[0]}</td><td>${b[1]}</td><td>${b[2]}</td><td>${b[3]}</td><td><span class="pill ${statusClass(b[4])}">${b[4]}</span></td></tr>`).join('');
 renderOrders();
 if(!checkItems.children.length)checkItems.innerHTML=['Beleuchtung','Bremsanlage','Bereifung','Flüssigkeitsstände','Warnleuchten','Wischer/Wascher','Unterboden Sichtprüfung','OBD Fehlerspeicher'].map(x=>`<label class="check-row"><span>${x}</span><input type="checkbox"></label>`).join('');
}
const stages=['Termin','Diagnose','Freigabe','In Arbeit','Fertig'];
function renderOrders(){orderBoard.innerHTML=stages.map(s=>`<div class="kanban-col"><h4>${s}</h4>${state.appointments.filter(a=>{const m={'Termin bestätigt':'Termin','Diagnose':'Diagnose','Freigabe offen':'Freigabe','In Arbeit':'In Arbeit','Teile vollständig':'In Arbeit','Fertig':'Fertig'};return m[a.status]===s}).map(a=>`<div class="ticket ${window.selectedOrder===a.id?'selected':''}" data-order="${a.id}"><b>${a.plate}</b><br>${a.vehicle}<br><small>${a.job}</small></div>`).join('')}</div>`).join('');document.querySelectorAll('.ticket').forEach(x=>x.onclick=()=>{window.selectedOrder=+x.dataset.order;renderOrders()})}
document.getElementById('loginForm').addEventListener('submit',login);
logoutBtn.onclick=logout;resetBtn.onclick=resetData;
newDemoAppointment.onclick=()=>{state.appointments.push({id:Date.now(),start:'16:00',resource:'Bühne 4',plate:'B-DEMO 26',vehicle:'Mercedes C-Klasse',customer:'Demo Kunde',mechanic:'Alex Berger',status:'Termin bestätigt',job:'Probefahrt / Diagnose'});persist();render();toast('Demo-Termin angelegt.')};
advanceOrder.onclick=()=>{const a=state.appointments.find(x=>x.id===window.selectedOrder)||state.appointments[0];const flow=['Termin bestätigt','Diagnose','Freigabe offen','In Arbeit','Fertig'];let i=flow.indexOf(a.status);a.status=flow[Math.min(i+1,flow.length-1)];persist();render();toast('Auftrag wurde auf „'+a.status+'“ gesetzt.')};
saveIntake.onclick=()=>toast('Annahme inkl. Checkliste wurde in der Demo gespeichert.');
approveBtn.onclick=()=>{approvalState.textContent='Status: freigegeben · Demo-Zeitstempel '+new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});approvalState.className='pill green';toast('Digitale Freigabe simuliert.')};
addAbsence.onclick=()=>{state.personnel[2][2]='Urlaub 24.–25.09.';persist();render();toast('Von–Bis-Abwesenheit eingetragen.')};
tireCheckin.onclick=()=>{state.tires.push(['WH-DEMO','Mercedes C-Klasse · B-DEMO 26','225/45 R18 · Demo-Reifen','Halle A / Regal 8 / Platz 02']);persist();render();toast('Demo-Radsatz eingelagert.')};
orderPart.onclick=()=>{state.parts[2][4]='bestellt';persist();render();toast('Bestellung ausgelöst; Lieferstatus aktualisiert.')};
createInvoice.onclick=()=>{if(!state.billing.some(x=>x[0]==='RE-DEMO-0001'))state.billing.unshift(['RE-DEMO-0001','S. Lehmann','Audi A4','189,00 €','Entwurf']);persist();render();toast('Rechnungsentwurf aus Auftrag erzeugt.')};
document.querySelectorAll('[data-toast]').forEach(b=>b.onclick=()=>toast(b.dataset.toast));
document.querySelectorAll('.nav').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));btn.classList.add('active');document.querySelectorAll('.page').forEach(x=>x.classList.add('hidden'));document.getElementById(btn.dataset.page).classList.remove('hidden')}));
globalSearch.addEventListener('input',()=>{const q=globalSearch.value.trim().toLowerCase();if(q.length<2){searchResults.classList.add('hidden');return}const hits=[];state.customers.forEach(c=>{if(Object.values(c).join(' ').toLowerCase().includes(q))hits.push(`${c.name} · ${c.car} · ${c.plate}`)});state.appointments.forEach(a=>{if(Object.values(a).join(' ').toLowerCase().includes(q))hits.push(`Auftrag · ${a.plate} · ${a.job}`)});searchResults.innerHTML=(hits.slice(0,8).map(x=>`<div>${x}</div>`).join('')||'<div>Keine Treffer</div>');searchResults.classList.remove('hidden')});
if(sessionStorage.getItem('wm_demo')==='1')showApp();