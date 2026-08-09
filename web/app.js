/* 135er GrowControl Future HUD v0.6
DE: Browser-Logik für BLE-Aktionen, Diagnose und geschützte Schreibbefehle.
EN: Browser logic for BLE actions, diagnostics and protected write commands.
*/
const $=id=>document.getElementById(id);
const diag=x=>$("diagnostics").textContent=typeof x==="string"?x:JSON.stringify(x,null,2);
function clock(){$("clock").textContent=new Date().toLocaleTimeString("de-DE")}setInterval(clock,1000);clock();
document.querySelectorAll(".nav-item").forEach(btn=>btn.addEventListener("click",()=>{document.querySelectorAll(".nav-item").forEach(b=>b.classList.remove("active"));document.querySelectorAll(".view").forEach(v=>v.classList.remove("active"));btn.classList.add("active");$(btn.dataset.view).classList.add("active")}));
const slider=$("speedSlider");function updateRing(){const v=Number(slider.value);$("speedValue").textContent=v;const deg=v*3.6;$("ring").style.background=`conic-gradient(var(--green) ${deg}deg, rgba(53,240,167,.08) ${deg}deg)`}slider.addEventListener("input",updateRing);updateRing();
async function api(url,options={}){const r=await fetch(url,options);let data={};try{data=await r.json()}catch{}if(!r.ok)throw new Error(data.detail||`${r.status} ${r.statusText}`);return data}
function writeToken(){let token=sessionStorage.getItem("gcLocalWriteToken")||"";if(!token){token=prompt("Lokales GrowControl Write-Token eingeben. Es wird nur für diese Browser-Sitzung gespeichert.")||"";if(token)sessionStorage.setItem("gcLocalWriteToken",token)}return token}
async function writeApi(url,options={}){const token=writeToken();if(!token)throw new Error("Kein Write-Token angegeben");const headers=new Headers(options.headers||{});headers.set("X-API-Token",token);return api(url,{...options,headers})}
async function refreshStatus(){try{const x=await api("/api/df100m/status");$("fanState").textContent=x.online?"ONLINE":"OFFLINE";$("fanAddr").textContent=x.address||"not connected";$("protocolState").textContent=x.protocol_validated?"VALIDATED":"SAFE";$("writeState").textContent=x.write_enabled?"ENABLED":"LOCKED";$("fanDot").style.background=x.online?"var(--green)":"var(--red)";$("deviceListState").textContent=x.online?"ONLINE":"OFFLINE";$("deviceListState").style.color=x.online?"var(--green)":"var(--red)"}catch(e){diag("STATUS ERROR\n"+e.message)}}
$("discoverBtn").addEventListener("click",async()=>{diag("Scanning BLE…");try{const x=await api("/api/df100m/discover");diag(x);if(x.devices?.length){const d=x.devices[0];diag(`Found ${d.name||"device"}\nConnecting ${d.address}…`);diag(await api("/api/df100m/connect?address="+encodeURIComponent(d.address),{method:"POST"}));refreshStatus()}}catch(e){diag("DISCOVERY ERROR\n"+e.message)}});
$("servicesBtn").addEventListener("click",async()=>{diag("Reading GATT services…");try{diag(await api("/api/df100m/services"))}catch(e){diag("GATT ERROR\n"+e.message)}});
$("sendSpeedBtn").addEventListener("click",async()=>{const v=Number(slider.value);if(!confirm(`Experimentellen DF100M-Testbefehl mit ${v}% senden?`))return;diag(`Sending test speed ${v}%…`);try{diag(await writeApi(`/api/df100m/speed?percent=${v}`,{method:"POST"}))}catch(e){diag("WRITE ERROR\n"+e.message)}});
$("refreshBtn").addEventListener("click",refreshStatus);setInterval(refreshStatus,4000);refreshStatus();
