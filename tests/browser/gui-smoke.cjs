/* Run from the repository root with Node and Playwright available.
   Uses Chromium from GC_CHROMIUM or /usr/bin/chromium. All API data is synthetic. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const stamp=new Date().toISOString();
const sample=(temperature=24)=>({temperature_c:temperature,humidity_percent:null,vpd_kpa:null,soil_moisture_percent:42.5,timestamp:stamp,source:'assigned-devices'});
const rooms=[{id:'room1',name:'Zelt A',kind:'grow_tent',device_count:1,plant_count:0,latest_sensor:sample()},{id:'room2',name:'Zelt B',kind:'grow_room',device_count:1,latest_sensor:sample(19)}];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.GC_CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let savedRoom=null,failSave=false,captures=1,delayFirst=false,failRuntime=false,lightCommands=[],automationRuns=[];
 let runtimeHealth={ok:true,state:'ok',provisioned:true,warnings:[],blockers:[],cloud:{enabled:false},device_runtime:{provider_count:10}};
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url()),pathname=url.pathname;
  if(url.hostname!=='gc.test')return route.fulfill({status:503,body:'External services are not part of this fixture'});
  if(pathname.startsWith('/api/')){
   if(pathname.endsWith('/sensors.csv'))return route.fulfill({contentType:'text/csv',body:'timestamp,power_w\n2026-10-14T00:00:00Z,0\n'});
   let data={};
   if(pathname==='/api/runtime/health'){if(failRuntime)return route.fulfill({status:503,body:'offline'});return route.fulfill({json:runtimeHealth})}
   if(pathname==='/api/v1/rooms'){
    if(route.request().method()==='POST'){if(failSave)return route.fulfill({status:503,json:{detail:'Test: Dienst nicht verfügbar'}});savedRoom=route.request().postDataJSON();data={...savedRoom,id:'room3'};rooms.push(data)}else data={rooms};
   }else if(pathname==='/api/v1/rooms/capture')data={ok:true,rooms_captured:captures};
   else if(pathname.endsWith('/sensors')){if(delayFirst&&pathname.includes('room1'))await new Promise(r=>setTimeout(r,300));const base=pathname.includes('room2')?19:24;data={samples:[{...sample(base-1),humidity_percent:52,power_w:80},{...sample(base+1),humidity_percent:58,power_w:110},{...sample(base),humidity_percent:55,power_w:95}]}}
   else if(pathname.match(/rooms\/[^/]+\/devices$/))data={devices:[{id:'growcentral_esp32:soil1',name:'Substratsonde',provider_id:'growcentral_esp32',assigned:true,online:true,state:{soil_moisture:42.5,meta:{raw:2710,filtered_raw:2709.5,quality:'EXCELLENT',moisture_state:'AIR_DRY',air_raw:3000,water_raw:1200,rssi_dbm:-60,uptime_ms:3600000,firmware:'<img src=x onerror=alert(1)>',sensor_ok:true,min:0}}}]};
   else if(pathname.endsWith('/journal'))data={entries:[]};
   else if(pathname.endsWith('/plants'))data={plants:[]};
   else if(pathname==='/api/v1/automations/runtime')data={scheduler:'running',last_runs:{}};
   else if(pathname==='/api/v1/automations/gc-1/run'&&route.request().method()==='POST'){automationRuns.push('gc-1');data={ok:true,automation_id:'gc-1',confirmed:true,on:true};}
   else if(pathname==='/api/v1/automations'&&route.request().method()==='GET')data={automations:[{id:'gc-1',name:'Test Zeitregel',trigger:'time',trigger_value:'08:00',device_id:'fritz-lampe',ain:'08761 0001',on:true,enabled:true}],execution_status:'time_and_manual'};
   else if(pathname==='/api/devices/discover')data={devices:[{provider_id:'mqtt',native_id:'lamp1',name:'Test Licht',device_class:'light',capabilities:['power','brightness'],model:'Synthetic'}],errors:[]};
   else if(pathname==='/api/devices/mqtt/lamp1/state')data={state:{online:true,power:false,brightness:50}};
   else if(pathname==='/api/devices/mqtt/lamp1/command'&&route.request().method()==='POST'){lightCommands.push(route.request().postDataJSON());data={ok:true,state:{online:true,...route.request().postDataJSON()}};}
   else if(pathname==='/api/health')data={ok:true};
   else if(pathname.includes('smarthome/overview'))data={summary:{power_w:null,energy_wh:null},devices:[]};
   else if(pathname.includes('/runtime')||pathname.includes('/platform'))data={providers:[]};
   else if(pathname==='/api/status')data={notifications:[{temperature:null,humidity:null,vpd:null}]};
   return route.fulfill({json:data});
  }
  if(pathname==='/legacy')return route.fulfill({contentType:'text/html',body:'<!doctype html><title>Legacy fixture</title>'});
  let file=pathname.startsWith('/static/')?pathname.slice(8):({'/rooms':'console.html','/ui':'platform.html','/':'platform.html','/mobile':'mobile.html','/editor':'ui-editor.html'}[pathname]);
  if(!file)return route.fulfill({status:404,body:'Not found'});
  const type=file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.png')?'image/png':file.endsWith('.jpg')?'image/jpeg':'text/html';
  try{return route.fulfill({contentType:type,body:await fs.readFile(path.join(root,'web',file))})}catch{return route.fulfill({status:404,body:'Not found'})}
 });
 await page.goto('http://gc.test/rooms?room=room1&tab=sensors');
 await page.locator('#sensorSummary').getByText('Kalibrierung erforderlich',{exact:true}).waitFor();
 assert(!/42[.,]5\s*%/.test(await page.locator('#sensorSummary').innerText()),'provisional soil percentage stays hidden');
 await page.locator('#sensorDiagnostics > summary').click();
 await page.getByText('EXCELLENT',{exact:true}).waitFor();
 assert.equal(await page.locator('#sensorDiagnosticsRows img').count(),0,'metadata must be escaped');
 assert.match(await page.locator('#sensorDiagnosticsRows').innerText(),/2710/);
 const downloaded=page.waitForEvent('download');await page.locator('#exportSensorsBtn').click();assert.match((await downloaded).suggestedFilename(),/sensoren\.csv$/);
 await page.locator('#newRoomBtn').click();
 await page.locator('[name=name]').fill('  Neues Zelt  ');
 await page.locator('[name=temperature]').fill('0');
 failSave=true;await page.locator('#saveRoomBtn').click();await page.locator('#roomFormError').waitFor({state:'visible'});
 assert.equal(await page.locator('[name=name]').inputValue(),'Neues Zelt','failed save preserves form');
 failSave=false;await page.locator('#saveRoomBtn').click();await page.locator('#roomDialog').waitFor({state:'hidden'});
 assert.equal(savedRoom.target_temperature_c,0);assert.equal(savedRoom.target_humidity_percent,null);
 // Capture feedback and room-change race: an old room response must not win.
 await page.locator('[data-room-id=room1]').first().click();
 await page.locator('#captureRoomBtn').click();await page.getByText('Messwerterfassung abgeschlossen.',{exact:false}).waitFor();
 captures=0;await page.locator('#captureRoomBtn').click();await page.getByText('Keine neuen Messwerte verfügbar.',{exact:false}).waitFor();
 delayFirst=true;await page.locator('[data-room-id=room1]').first().click();await page.locator('[data-room-id=room2]').first().click();
 await page.waitForTimeout(400);assert.match(await page.locator('#sensorSummary').innerText(),/19.0 °C/);
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:900});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`console overflow at ${width}`);
  await page.locator('#editRoomBtn').click();
  const box=await page.locator('#roomDialog').boundingBox();assert(box.x>=0&&box.x+box.width<=width,`dialog overflow at ${width}`);
  await page.locator('#cancelRoomBtn').click();
  if(process.env.GC_SCREENSHOT_DIR){await fs.mkdir(process.env.GC_SCREENSHOT_DIR,{recursive:true});await page.screenshot({path:path.join(process.env.GC_SCREENSHOT_DIR,`console-${width}.png`),fullPage:true})}
 }
 await page.goto('http://gc.test/ui');
 assert.equal(await page.locator('.master-shell').count(),1,'productive UI keeps Final Master');await page.locator('#growSelector option[value=room2]').waitFor({state:'attached'});
 await page.locator('#quickLight button').first().waitFor({state:'visible'});
 await page.waitForFunction(()=>!document.querySelector('#quickLight button')?.disabled);
 await page.locator('#quickLight button').first().click();
 await page.waitForTimeout(100);
 assert(lightCommands.some(c=>c.capability==='power'&&c.value===true),'quick light writes confirmed power command');
 await page.locator('#mainNav [data-view=lighting]').click();
 await page.locator('.gc-light-brightness').waitFor({state:'visible'});
 await page.locator('.gc-light-brightness').evaluate(el=>{el.value='70';el.dispatchEvent(new Event('change',{bubbles:true}))});
 await page.waitForTimeout(100);
 assert(lightCommands.some(c=>c.capability==='brightness'&&c.value===70),'lighting page writes confirmed brightness command');
 await page.locator('#mainNav [data-view=automation]').click();
 await page.locator('.gc-auto-run').first().waitFor({state:'visible'});
 await page.locator('.gc-auto-run').first().click();
 await page.waitForTimeout(100);
 assert.deepEqual(automationRuns,['gc-1'],'manual automation action reaches confirmed run endpoint');
 await page.locator('#overviewClimateHistory svg').waitFor({state:'attached'});
 assert.equal(await page.locator('#overviewClimateHistory polyline').count(),2,'overview climate history renders temperature and humidity');
 await page.locator('#overviewEnergyHistory svg').waitFor({state:'attached'});
 assert.equal(await page.locator('#overviewEnergyHistory polyline').count(),1,'overview energy history renders real power samples');
 await page.locator('#growSelector').selectOption('room2',{force:true});assert.equal(await page.locator('#temp').innerText(),'19.0');
 assert.equal(await page.locator('#rh').innerText(),'—');assert.equal(await page.locator('#power').innerText(),'—');
 await page.locator('#refreshBtn').evaluate(node=>node.click());await page.waitForTimeout(100);assert.equal(await page.locator('#temp').innerText(),'19.0');
 for(const width of [390,768,1440]){
  await page.setViewportSize({width,height:1000});
  if(width===390)await page.locator('#mobileMenuToggle').click();
  await page.locator('#mainNav [data-view=grow]').click();
  assert.equal(await page.locator('#grow').getAttribute('class').then(v=>v.includes('active')),true);
  assert(await page.locator('#growCards a').first().getAttribute('href').then(v=>v.startsWith('/rooms?room=')));
  assert(!/42[.,]5\s*%/.test(await page.locator('#growCards').innerText()),'master calibration policy preserved');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`master overflow at ${width}`);
  if(width===390)assert.equal(await page.locator('#mobileMenuToggle').getAttribute('aria-expanded'),'false');
 }
 // Every Final-Master menu page must initialize without uncaught errors.
 for(const id of ['devices','calibration','climate','irrigation','lighting','automation','recipes','growlog','camera','recordings','timelapse','settings','applehome','users','backups','updates','extensions']){
  await page.locator(`#mainNav [data-view=${id}]`).click();
  await page.waitForTimeout(40);
  assert.equal(await page.locator(`#${id}`).getAttribute('class').then(v=>v.includes('active')),true,`${id} view activates`);
  if(['climate','irrigation','lighting','automation','recipes','growlog','recordings','timelapse','settings','users','backups','updates','extensions'].includes(id))assert.equal(await page.locator(`#${id} > .gc-live-body`).count(),1,`${id} live body mounted`);
 }
 await page.locator('#mainNav [data-view=overview]').click();
 // Runtime status comes from the full health contract and clears on recovery.
 await page.getByText('0 Hinweise',{exact:true}).waitFor();
 await page.evaluate(()=>window.dispatchEvent(new CustomEvent('gc:provider-health',{detail:{errors:2}})));await page.getByText('2 Hinweise',{exact:true}).waitFor();
 await page.evaluate(()=>window.dispatchEvent(new CustomEvent('gc:provider-health',{detail:{errors:0}})));await page.getByText('0 Hinweise',{exact:true}).waitFor();
 runtimeHealth={...runtimeHealth,state:'warning',warnings:['cloud_not_connected'],cloud:{enabled:true,state:'stale'}};
 await page.evaluate(()=>window.dispatchEvent(new Event('gc:refresh')));await page.getByText('1 Hinweis',{exact:true}).waitFor();
 assert.match(await page.locator('#heroHealthLabel').innerText(),/Hinweise/);
 failRuntime=true;await page.evaluate(()=>window.dispatchEvent(new Event('gc:refresh')));await page.getByText('System prüfen',{exact:true}).first().waitFor();
 assert.match(await page.locator('#headlineSub').innerText(),/Status nicht erreichbar/);
 failRuntime=false;runtimeHealth={...runtimeHealth,state:'ok',warnings:[],cloud:{enabled:false}};
 await page.evaluate(()=>window.dispatchEvent(new Event('gc:refresh')));await page.getByText('0 Hinweise',{exact:true}).waitFor();
 rooms[1].latest_sensor.timestamp='2020-01-01T00:00:00Z';await page.evaluate(()=>window.dispatchEvent(new Event('gc:refresh')));
 await page.locator('#roomFreshCount').getByText('1 / 3',{exact:true}).waitFor({state:'attached'});
 await page.goto('http://gc.test/mobile');await page.locator('#mTemp').getByText('24.0',{exact:true}).waitFor();
 assert.equal(await page.locator('#mRh').innerText(),'—');assert.equal(await page.locator('#mPower').innerText(),'—');
 await page.goto('http://gc.test/editor');await page.locator('#canvas .widget').first().click();
 for(const [id,value,key] of [['widgetTitle','Mein Titel','title'],['widgetKicker','Raumstatus','kicker'],['widgetText','Eine Beschreibung','text'],['widgetBinding','sensor.raw','binding']]){
  await page.locator('#'+id).fill(value);
  const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('gc.fullUiLayoutDraft.v2')));
  assert.equal(stored.pages[0].widgets[0][key],value);
 }
 await page.reload();assert.match(await page.locator('#canvas').innerText(),/Mein Titel/);
 const invalidAlert=page.waitForEvent('dialog').then(async d=>{assert.match(d.message(),/Ungültige/);await d.accept()});
 await page.locator('#importInput').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({shell:{},pages:[]}))});await invalidAlert;
 assert.match(await page.locator('#canvas').innerText(),/Mein Titel/,'invalid import keeps the previous draft');
 await page.evaluate(()=>localStorage.setItem('gc.fullUiLayoutDraft.v2',JSON.stringify({shell:{},pages:[]})));
 await page.reload();assert(await page.locator('#canvas .widget').count()>0,'invalid stored layout recovers to defaults');
 assert.deepEqual(errors,[],'no uncaught browser errors');
 console.log('PASS: Final Master, responsive rooms, diagnostics, CSV download, runtime failures/recovery, room races, desktop/mobile metrics and editor persistence');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
