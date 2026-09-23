const DEMO_USER='demo';
const DEMO_PASS='WerkstattDemo!2026';
const seedAppointments=[
 {start:'08:00',resource:'Bühne 1',plate:'B-WM 1028',vehicle:'VW Golf VIII',customer:'M. Weber',mechanic:'Marco Stein',status:'In Arbeit',job:'Inspektion + Ölservice'},
 {start:'09:30',resource:'Diagnoseplatz',plate:'B-WM 1184',vehicle:'Audi A4',customer:'S. Lehmann',mechanic:'Alex Berger',status:'Diagnose',job:'Motorkontrollleuchte'},
 {start:'11:00',resource:'Bühne 3',plate:'B-WM 1249',vehicle:'Skoda Octavia',customer:'K. Sommer',mechanic:'Lea Hoffmann',status:'Termin bestätigt',job:'Reifenwechsel'},
 {start:'13:00',resource:'Achsmessplatz',plate:'B-WM 1315',vehicle:'Ford Transit',customer:'BauService Nord',mechanic:'Lea Hoffmann',status:'Teile vollständig',job:'Achsvermessung'},
 {start:'14:30',resource:'Bühne 2',plate:'B-WM 1391',vehicle:'BMW 320d',customer:'J. Richter',mechanic:'Marco Stein',status:'Freigabe offen',job:'Bremse Hinterachse'}
];
const customers=[
 {name:'M. Weber',car:'VW Golf VIII',plate:'B-WM 1028',vin:'WVWZZZ…1028',history:'4 Werkstattbesuche'},
 {name:'S. Lehmann',car:'Audi A4',plate:'B-WM 1184',vin:'WAUZZZ…1184',history:'2 Werkstattbesuche'},
 {name:'K. Sommer',car:'Skoda Octavia',plate:'B-WM 1249',vin:'TMBZZZ…1249',history:'6 Werkstattbesuche'},
 {name:'BauService Nord',car:'Ford Transit',plate:'B-WM 1315',vin:'WF0XXX…1315',history:'Flottenkunde'}
];
let appointments=[];
function resetData(){appointments=JSON.parse(JSON.stringify(seedAppointments));render();}
function login(e){e.preventDefault();const u=document.getElementById('user').value.trim();const p=document.getElementById('pass').value;if(u===DEMO_USER&&p===DEMO_PASS){sessionStorage.setItem('wm_demo','1');showApp()}else{document.getElementById('loginError').textContent='Demo-Zugangsdaten sind nicht korrekt.'}}
function showApp(){document.getElementById('loginView').classList.add('hidden');document.getElementById('appView').classList.remove('hidden');resetData()}
function logout(){sessionStorage.removeItem('wm_demo');location.reload()}
function render(){
 document.getElementById('kpiAppointments').textContent=appointments.length;
 document.getElementById('todayLabel').textContent=new Intl.DateTimeFormat('de-DE',{dateStyle:'full'}).format(new Date());
 document.getElementById('dashboardJobs').innerHTML=appointments.slice(0,4).map(a=>`<div class="job-row"><b>${a.start}</b><span>${a.resource}</span><div><b>${a.vehicle}</b><br><small>${a.plate} · ${a.customer}</small></div><span class="pill blue">${a.status}</span></div>`).join('');
 document.getElementById('plannerRows').innerHTML=appointments.map(a=>`<tr><td>${a.start}</td><td>${a.resource}</td><td>${a.plate}</td><td>${a.vehicle}</td><td>${a.customer}</td><td>${a.mechanic}</td><td><span class="pill blue">${a.status}</span></td><td>${a.job}</td></tr>`).join('');
 document.getElementById('customerCards').innerHTML=customers.map(c=>`<article><h3>${c.name}</h3><p><b>${c.car}</b><br>${c.plate}</p><small>FIN ${c.vin}<br>${c.history}</small></article>`).join('');
}
document.getElementById('loginForm').addEventListener('submit',login);
document.getElementById('logoutBtn').addEventListener('click',logout);
document.getElementById('resetBtn').addEventListener('click',resetData);
document.getElementById('newDemoAppointment').addEventListener('click',()=>{appointments.push({start:'16:00',resource:'Bühne 4',plate:'B-DEMO 26',vehicle:'Mercedes C-Klasse',customer:'Demo Kunde',mechanic:'Alex Berger',status:'Termin bestätigt',job:'Probefahrt / Diagnose'});render()});
document.querySelectorAll('.nav').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));btn.classList.add('active');document.querySelectorAll('.page').forEach(x=>x.classList.add('hidden'));document.getElementById(btn.dataset.page).classList.remove('hidden')}));
if(sessionStorage.getItem('wm_demo')==='1')showApp();