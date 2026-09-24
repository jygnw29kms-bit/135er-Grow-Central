const cEsc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
let catalogState={status:null,kba:[],aag:[]};

async function catalogUpload(path,file){
  if(!file) throw new Error('Bitte zuerst eine Datei auswählen.');
  const fd=new FormData(); fd.append('file',file,file.name);
  const res=await fetch(API+path,{method:'POST',headers:token?{Authorization:'Bearer '+token}:{},body:fd});
  const txt=await res.text(); let data=null; try{data=txt?JSON.parse(txt):null}catch{data=txt}
  if(res.status===401){sessionStorage.removeItem('wm_erp_token');token='';showLogin();throw new Error('Sitzung abgelaufen')}
  if(!res.ok) throw new Error(data?.error||data?.title||('HTTP '+res.status));
  return data;
}

async function loadCatalogStatus(){
  try{
    catalogState.status=await api('/catalog/status');
    renderCatalogStatus();
  }catch(e){
    if($('catalogStatus')) $('catalogStatus').innerHTML='<article><span>Katalog</span><b>Fehler</b><small>'+cEsc(e.message)+'</small></article>';
  }
}

function renderCatalogStatus(){
  const host=$('catalogStatus'); if(!host)return;
  const src=Object.fromEntries((catalogState.status?.sources||[]).map(x=>[x.source,x]));
  const k=src.KBA||{},a=src.AAG||{}, supplied=catalogState.status?.suppliedFiles||{};
  const sourceLabel=x=>String(x.sourceName||'').includes('Demoauszug')?'Demoauszug':'vollständig importiert';
  host.innerHTML=
   '<article><span>KBA Datensatz</span><b>'+Number(k.recordCount||0).toLocaleString('de-DE')+'</b><small>'+cEsc(k.dataDate||supplied.kba?.sourceDate||'')+' · '+cEsc(sourceLabel(k))+'</small></article>'+
   '<article><span>AAG Artikel</span><b>'+Number(a.recordCount||0).toLocaleString('de-DE')+'</b><small>'+cEsc(sourceLabel(a))+'</small></article>'+
   '<article><span>Geliefertes KBA-Paket</span><b>'+Number(supplied.kba?.sourceRecords||0).toLocaleString('de-DE')+'</b><small>'+cEsc(supplied.kba?.file||'KBA.ZIP')+'</small></article>'+
   '<article><span>Gelieferte AAG-Datei</span><b>'+Number(supplied.aag?.sourceRecords||0).toLocaleString('de-DE')+'</b><small>'+cEsc(supplied.aag?.columns||27)+' Spalten · monatlich</small></article>';
}

async function searchKba(){
  const h=($('kbaHsn')?.value||'').trim(),t=($('kbaTsn')?.value||'').trim(),q=($('kbaQuery')?.value||'').trim();
  if(!h&&!t&&!q){toast('Bitte HSN/TSN oder einen Suchbegriff eingeben.',true);return}
  try{
    catalogState.kba=await api('/catalog/kba?hsn='+encodeURIComponent(h)+'&tsn='+encodeURIComponent(t)+'&q='+encodeURIComponent(q)+'&limit=100');
    renderKba();
  }catch(e){toast(e.message,true)}
}
function renderKba(){
  const rows=$('kbaRows'); if(!rows)return;
  $('kbaResultInfo').textContent=catalogState.kba.length+' Treffer';
  rows.innerHTML=catalogState.kba.map((x,i)=>{
    const motor=[x.kw!=null?x.kw+' kW':'',x.ps!=null?x.ps+' PS':'',x.ccm!=null?x.ccm+' ccm':'',x.fuel||''].filter(Boolean).join(' · ');
    const tech=[x.body,x.drive,x.gearbox,x.cylinders?x.cylinders+' Zyl.':''].filter(Boolean).join(' · ');
    return '<tr><td><b>'+cEsc(x.hsn)+' / '+cEsc(x.tsn)+'</b><small class="muted">'+cEsc(x.kbaNo)+'</small></td>'+
      '<td>'+cEsc(x.manufacturer)+'</td><td><b>'+cEsc(x.model)+'</b><br><span class="muted">'+cEsc(x.type)+'</span></td>'+
      '<td>'+cEsc(motor||'–')+'</td><td>'+cEsc([x.buildFrom,x.buildTo].filter(Boolean).join(' – ')||'–')+'</td><td>'+cEsc(tech||'–')+'</td>'+
      '<td><button class="primary small" data-kba-use="'+i+'">Fahrzeug anlegen</button></td></tr>';
  }).join('')||'<tr><td colspan="7">Keine passenden Fahrzeuge gefunden.</td></tr>';
  document.querySelectorAll('[data-kba-use]').forEach(b=>b.onclick=()=>kbaVehicleModal(catalogState.kba[Number(b.dataset.kbaUse)]));
}
function kbaVehicleModal(x){
  const opts=(state.customers||[]).map(c=>'<option value="'+c.id+'">'+cEsc(c.customerNumber+' · '+c.displayName)+'</option>').join('');
  showModal('Fahrzeug aus KBA anlegen',
    '<div class="form-grid">'+
    '<label class="span2">Kunde<select id="kbaVehicleCustomer">'+opts+'</select></label>'+
    '<label>Kennzeichen<input id="kbaVehiclePlate" placeholder="HVL-AB 123"></label>'+
    '<label>VIN<input id="kbaVehicleVin" maxlength="17"></label>'+
    '<label>HSN<input id="kbaVehicleHsn" value="'+cEsc(x.hsn)+'"></label>'+
    '<label>TSN<input id="kbaVehicleTsn" value="'+cEsc(x.tsn)+'"></label>'+
    '<label>Hersteller<input id="kbaVehicleMake" value="'+cEsc(x.manufacturer)+'"></label>'+
    '<label>Modell<input id="kbaVehicleModel" value="'+cEsc(x.model)+'"></label>'+
    '<label class="span2">Typ<input id="kbaVehicleType" value="'+cEsc(x.type)+'"></label>'+
    '<label>Erstzulassung<input id="kbaVehicleFirst" type="date"></label>'+
    '<label>Kilometer<input id="kbaVehicleMileage" type="number" min="0"></label>'+
    '</div>'+
    '<div class="panel"><b>KBA-Technik</b><p class="muted">'+cEsc([
      x.kw!=null?x.kw+' kW':'',x.ps!=null?x.ps+' PS':'',x.ccm!=null?x.ccm+' ccm':'',x.fuel,x.engineType,x.body,x.drive,x.gearbox
    ].filter(Boolean).join(' · '))+'</p></div>'+
    '<div class="form-actions"><button id="kbaVehicleSave" class="primary">Fahrzeug speichern</button></div>');
  $('kbaVehicleSave').onclick=async()=>{
    try{
      const customerId=$('kbaVehicleCustomer').value;
      if(!customerId)throw new Error('Bitte einen Kunden auswählen.');
      const payload={customerId,licensePlate:$('kbaVehiclePlate').value.trim(),vin:$('kbaVehicleVin').value.trim(),make:$('kbaVehicleMake').value.trim(),
        model:$('kbaVehicleModel').value.trim(),type:$('kbaVehicleType').value.trim(),hsn:$('kbaVehicleHsn').value.trim(),tsn:$('kbaVehicleTsn').value.trim(),
        firstRegistration:$('kbaVehicleFirst').value||null,mileage:$('kbaVehicleMileage').value?Number($('kbaVehicleMileage').value):null,nextHu:null,nextService:null};
      if(!payload.licensePlate)throw new Error('Kennzeichen fehlt.');
      await api('/vehicles',{method:'POST',body:JSON.stringify(payload)});
      closeModal(); await loadAll(); toast('Fahrzeug aus KBA-Daten angelegt.');
    }catch(e){toast(e.message,true)}
  };
}

async function searchAag(){
  const q=($('aagQuery')?.value||'').trim(),brand=($('aagBrand')?.value||'').trim(),status=$('aagStatus')?.value||'';
  if(!q&&!brand&&!status){toast('Bitte Artikelnummer, EAN, Marke oder Suchtext eingeben.',true);return}
  try{
    catalogState.aag=await api('/catalog/aag?q='+encodeURIComponent(q)+'&brand='+encodeURIComponent(brand)+'&status='+encodeURIComponent(status)+'&limit=100');
    renderAag();
  }catch(e){toast(e.message,true)}
}
function renderAag(){
  const rows=$('aagRows');if(!rows)return;
  $('aagResultInfo').textContent=catalogState.aag.length+' Treffer';
  rows.innerHTML=catalogState.aag.map((x,i)=>{
    const successor=[x.successorOriginal,x.successorHennig].filter(Boolean).join(' / ')||'–';
    return '<tr><td><b>'+cEsc(x.artNr)+'</b><br><span class="muted">AAG '+cEsc(x.hennigArtNr||'–')+'</span></td>'+
      '<td><b>'+cEsc(x.brand||'')+'</b><br>'+cEsc(x.description1||'')+(x.description2?'<br><span class="muted">'+cEsc(x.description2)+'</span>':'')+'</td>'+
      '<td>'+cEsc(x.ean||'–')+'</td><td>'+fmtMoney(x.purchasePrice||0)+'</td><td>'+fmtMoney(x.grossPrice||0)+'</td>'+
      '<td><span class="badge '+badge(x.articleStatus||'')+'">'+cEsc(x.articleStatus||'–')+'</span></td><td>'+cEsc(successor)+'</td>'+
      '<td><div class="page-actions"><button class="secondary small" data-aag-stock="'+i+'">Lager</button>'+
      '<button class="primary small" data-aag-order="'+i+'">Auftrag/KV</button></div></td></tr>';
  }).join('')||'<tr><td colspan="8">Keine passenden AAG-Artikel gefunden.</td></tr>';
  document.querySelectorAll('[data-aag-stock]').forEach(b=>b.onclick=()=>aagInventoryModal(catalogState.aag[Number(b.dataset.aagStock)]));
  document.querySelectorAll('[data-aag-order]').forEach(b=>b.onclick=()=>aagOrderModal(catalogState.aag[Number(b.dataset.aagOrder)]));
}
function aagInventoryModal(x){
  const listNet=Number(x.grossPrice||0)/1.19;
  showModal('AAG-Artikel in Lagerstamm übernehmen',
    '<div class="form-grid">'+
    '<label>Artikelnummer<input id="aagInvNo" value="'+cEsc(x.artNr)+'"></label>'+
    '<label>EAN<input id="aagInvEan" value="'+cEsc(x.ean||'')+'"></label>'+
    '<label>Hersteller / Marke<input id="aagInvBrand" value="'+cEsc(x.brand||'')+'"></label>'+
    '<label class="span2">Bezeichnung<input id="aagInvDesc" value="'+cEsc(x.description1||'')+'"></label>'+
    '<label>EK netto<input id="aagInvEk" type="number" step="0.01" value="'+Number(x.purchasePrice||0).toFixed(2)+'"></label>'+
    '<label>VK netto<input id="aagInvVk" type="number" step="0.01" value="'+listNet.toFixed(2)+'"></label>'+
    '<label>Bestand<input id="aagInvStock" type="number" step="1" value="0"></label>'+
    '<label>Mindestbestand<input id="aagInvMin" type="number" step="1" value="0"></label>'+
    '<label class="span2">Lagerort<input id="aagInvLoc" placeholder="optional"></label>'+
    '</div><p class="muted">AAG-Status: '+cEsc(x.articleStatus||'–')+' · Lieferant '+cEsc(x.supplierNo||'–')+(x.coreValue?' · Pfand '+fmtMoney(x.coreValue):'')+'</p>'+
    '<div class="form-actions"><button id="aagInvSave" class="primary">In Lagerstamm übernehmen</button></div>');
  $('aagInvSave').onclick=async()=>{
    try{
      const no=$('aagInvNo').value.trim();
      if(state.inventory.some(i=>String(i.itemNumber).toLowerCase()===no.toLowerCase()))throw new Error('Artikelnummer existiert bereits im Lagerstamm.');
      await api('/inventory',{method:'POST',body:JSON.stringify({itemNumber:no,ean:$('aagInvEan').value.trim(),manufacturer:$('aagInvBrand').value.trim(),
        description:$('aagInvDesc').value.trim(),purchaseNet:Number($('aagInvEk').value||0),saleNet:Number($('aagInvVk').value||0),
        stock:Number($('aagInvStock').value||0),minimumStock:Number($('aagInvMin').value||0),storageLocation:$('aagInvLoc').value.trim(),preferredSupplierId:null})});
      closeModal();await loadAll();toast('AAG-Artikel in Lagerstamm übernommen.');
    }catch(e){toast(e.message,true)}
  };
}
function currentCatalogOrder(){
  return state.selectedOrder||null;
}
function aagOrderModal(x){
  const order=currentCatalogOrder();
  if(!order){toast('Bitte zuerst einen Auftrag oder Kostenvoranschlag öffnen.',true);page('orders');return}
  const listNet=Number(x.grossPrice||0)/1.19;
  showModal('AAG-Artikel · '+cEsc(order.number),
    '<div class="form-grid">'+
    '<label>Artikelnummer<input id="aagOrderNo" value="'+cEsc(x.artNr)+'"></label>'+
    '<label>Menge<input id="aagOrderQty" type="number" min="0.01" step="0.01" value="1"></label>'+
    '<label class="span2">Bezeichnung<input id="aagOrderDesc" value="'+cEsc((x.brand?x.brand+' ':'')+(x.description1||''))+'"></label>'+
    '<label>EK AAG netto<input value="'+Number(x.purchasePrice||0).toFixed(2)+'" disabled></label>'+
    '<label>VK netto<input id="aagOrderVk" type="number" min="0" step="0.01" value="'+listNet.toFixed(2)+'"></label>'+
    '<label>MwSt. %<input id="aagOrderVat" type="number" min="0" step="0.1" value="19"></label>'+
    '<label>Rabatt %<input id="aagOrderDiscount" type="number" min="0" max="100" step="0.1" value="0"></label>'+
    '</div><p class="muted">AAG '+cEsc(x.hennigArtNr||'')+' · '+cEsc(x.articleStatus||'')+(x.successorOriginal?' · Nachfolger '+cEsc(x.successorOriginal):'')+'</p>'+
    '<div class="form-actions"><button id="aagOrderSave" class="primary">Position übernehmen</button></div>');
  $('aagOrderSave').onclick=async()=>{
    try{
      await api('/work-orders/'+order.id+'/lines',{method:'POST',body:JSON.stringify({type:1,itemNumber:$('aagOrderNo').value.trim(),
        description:$('aagOrderDesc').value.trim(),quantity:Number($('aagOrderQty').value||1),unitNet:Number($('aagOrderVk').value||0),
        vatRate:Number($('aagOrderVat').value||19),discountPercent:Number($('aagOrderDiscount').value||0),inventoryItemId:null,employeeId:null})});
      closeModal();await loadAll();if(typeof openOrder==='function')await openOrder(order.id);toast('AAG-Artikel in Auftrag/KV übernommen.');
    }catch(e){toast(e.message,true)}
  };
}

async function importCatalog(kind){
  const isKba=kind==='kba', input=$(isKba?'kbaImportFile':'aagImportFile'), file=input?.files?.[0];
  if(!file){toast('Bitte zuerst die passende Datei auswählen.',true);return}
  const stateEl=$('catalogImportState');
  stateEl.textContent=(isKba?'KBA-Paket':'AAG-Preisdatei')+' wird verarbeitet: '+file.name;
  const btn=$(isKba?'kbaImportBtn':'aagImportBtn');btn.disabled=true;
  try{
    const r=await catalogUpload('/catalog/import/'+kind,file);
    stateEl.textContent=(isKba?'KBA':'AAG')+': '+Number(r.imported||0).toLocaleString('de-DE')+' Datensätze importiert · '+file.name;
    toast('Katalogimport abgeschlossen.');
    await loadCatalogStatus();
    if(isKba){catalogState.kba=[];renderKba()}else{catalogState.aag=[];renderAag()}
  }catch(e){stateEl.textContent='Import fehlgeschlagen: '+e.message;toast(e.message,true)}
  finally{btn.disabled=false}
}

function injectCatalogButtons(){
  [['orderDetail','AAG-Katalog'],['quoteDetail','AAG-Katalog']].forEach(([id,label])=>{
    const host=$(id);if(!host||host.classList.contains('hidden')||host.querySelector('[data-open-aag-catalog]'))return;
    const head=host.querySelector('.panel-head')||host;
    const b=document.createElement('button');b.className='secondary small';b.dataset.openAagCatalog='1';b.textContent=label;
    b.onclick=()=>{page('catalog');setTimeout(()=>$('aagQuery')?.focus(),0)};
    head.appendChild(b);
  });
}
const catalogObserver=new MutationObserver(injectCatalogButtons);
['orderDetail','quoteDetail'].forEach(id=>{const el=$(id);if(el)catalogObserver.observe(el,{childList:true,subtree:true,attributes:true,attributeFilter:['class']})});

$('catalogRefreshBtn')?.addEventListener('click',loadCatalogStatus);
$('kbaSearchBtn')?.addEventListener('click',searchKba);
$('aagSearchBtn')?.addEventListener('click',searchAag);
$('kbaImportBtn')?.addEventListener('click',()=>importCatalog('kba'));
$('aagImportBtn')?.addEventListener('click',()=>importCatalog('aag'));
$('kbaHsn')?.addEventListener('keydown',e=>{if(e.key==='Enter')searchKba()});
$('kbaTsn')?.addEventListener('keydown',e=>{if(e.key==='Enter')searchKba()});
$('kbaQuery')?.addEventListener('keydown',e=>{if(e.key==='Enter')searchKba()});
$('aagQuery')?.addEventListener('keydown',e=>{if(e.key==='Enter')searchAag()});
loadCatalogStatus();
