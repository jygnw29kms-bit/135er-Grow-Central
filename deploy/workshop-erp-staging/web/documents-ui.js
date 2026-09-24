/* Productive document workspace: orders, quotes, invoices and delivery notes */
const docMoney = v => fmtMoney(Number(v || 0));
const docLineNet = l => Number(l.netTotal ?? (Number(l.quantity||0)*Number(l.unitNet||0)*(1-Number(l.discountPercent||0)/100)));
const docTotals = lines => {
  const net=(lines||[]).reduce((s,l)=>s+docLineNet(l),0);
  const vat=(lines||[]).reduce((s,l)=>s+docLineNet(l)*Number(l.vatRate||0)/100,0);
  return {net,vat,gross:net+vat};
};
function docTabs(root){
  root.querySelectorAll('[data-doc-tab]').forEach(b=>b.onclick=()=>{
    const key=b.dataset.docTab;
    root.querySelectorAll('[data-doc-tab]').forEach(x=>x.classList.toggle('active',x===b));
    root.querySelectorAll('[data-doc-pane]').forEach(x=>x.classList.toggle('hidden',x.dataset.docPane!==key));
  });
}
function docCustomerCard(cu){
 return '<div class="doc-card"><span class="doc-label">Kunde</span><b>'+esc(cu?.displayName||'–')+'</b>'+
   '<small>'+esc([cu?.customerNumber,cu?.phone||cu?.mobile,cu?.email].filter(Boolean).join(' · ')||'Keine Kontaktdaten')+'</small>'+
   '<small>'+esc([cu?.street,[cu?.postalCode,cu?.city].filter(Boolean).join(' ')].filter(Boolean).join(', ')||'')+'</small></div>';
}
function docVehicleCard(v){
 return '<div class="doc-card vehicle"><span class="doc-label">Fahrzeug</span><div class="doc-vehicle-title"><b>'+esc(v?.licensePlate||'–')+'</b><span>'+esc([v?.make,v?.model,v?.type].filter(Boolean).join(' '))+'</span></div>'+
   '<small>VIN '+esc(v?.vin||'–')+' · HSN/TSN '+esc((v?.hsn||'–')+'/'+(v?.tsn||'–'))+'</small>'+
   '<small>EZ '+esc(v?.firstRegistration||'–')+' · HU '+esc(v?.nextHu||'–')+' · km '+esc(v?.mileage??'–')+'</small></div>';
}
function docPositionTable(lines, editable, scope){
 return '<div class="doc-line-wrap"><table class="doc-lines"><thead><tr><th>Pos.</th><th>Art.-Nr.</th><th>Bezeichnung</th><th class="num">Menge</th><th class="num">EP netto</th><th class="num">Rabatt</th><th class="num">MwSt.</th><th class="num">Gesamt</th><th></th></tr></thead><tbody>'+
 (lines?.length?lines.map((l,i)=>'<tr><td class="pos">'+(i+1)+'</td><td><b>'+esc(l.itemNumber||'–')+'</b></td><td><div class="line-desc">'+esc(l.description||'')+(l.approvedByCustomer?'<small class="ok-text">✓ Kundenfreigabe</small>':'')+'</div></td><td class="num">'+esc(l.quantity)+'</td><td class="num">'+docMoney(l.unitNet)+'</td><td class="num">'+esc(Number(l.discountPercent||0).toLocaleString('de-DE'))+' %</td><td class="num">'+esc(Number(l.vatRate||0).toLocaleString('de-DE'))+' %</td><td class="num strong">'+docMoney(docLineNet(l))+'</td><td class="line-actions">'+
 (editable?'<button class="icon-mini" data-'+scope+'-edit="'+l.id+'" title="Position bearbeiten">✎</button><button class="icon-mini danger-text" data-'+scope+'-delete="'+l.id+'" title="Position löschen">×</button>':'')+'</td></tr>').join(''):
 '<tr><td colspan="9" class="doc-empty">Noch keine Positionen. Über „+ Position“ oder Teilekatalog hinzufügen.</td></tr>')+
 '</tbody></table></div>';
}
function docTotalsBox(lines, paid=null){
 const t=docTotals(lines);
 return '<aside class="doc-totals"><div><span>Netto</span><b>'+docMoney(t.net)+'</b></div><div><span>USt.</span><b>'+docMoney(t.vat)+'</b></div><div class="grand"><span>Brutto</span><b>'+docMoney(t.gross)+'</b></div>'+
 (paid!==null?'<div><span>Bezahlt</span><b>'+docMoney(paid)+'</b></div><div class="open"><span>Offen</span><b>'+docMoney(Math.max(0,t.gross-Number(paid||0)))+'</b></div>':'')+'</aside>';
}
function docHeader(kind,number,status,statusClass,cu,v,actions=''){
 return '<div class="doc-head"><div class="doc-title"><span class="eyebrow">'+esc(kind)+'</span><div><h3>'+esc(number)+'</h3><span class="badge '+statusClass+'">'+esc(status)+'</span></div></div><div class="doc-head-actions">'+actions+'</div></div>'+
 '<div class="doc-master">'+docCustomerCard(cu)+docVehicleCard(v)+'</div>';
}
function printWorkDocument(orderId, kind='work-order', documentNumber=''){
 const w=window.open('','_blank'); if(!w)return toast('Popup wurde blockiert.',true);
 (async()=>{
  try{
   const d=await api('/work-orders/'+orderId),o=d.order,cu=customer(o.customerId),v=vehicle(o.vehicleId),co=state.company||{},t=docTotals(d.lines);
   const title=kind==='delivery-note'?'Lieferschein':'Werkstattauftrag';
   const no=documentNumber||o.number;
   const showPrices=kind!=='delivery-note';
   const rows=d.lines.map((l,i)=>'<tr><td>'+(i+1)+'</td><td>'+esc(l.itemNumber||'')+'</td><td>'+esc(l.description||'')+'</td><td>'+esc(l.quantity)+'</td>'+
      (showPrices?'<td>'+docMoney(l.unitNet)+'</td><td>'+docMoney(docLineNet(l))+'</td>':'')+'</tr>').join('');
   w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>'+esc(title+' '+no)+'</title><style>body{font:13px Arial,sans-serif;color:#17212b;padding:34px}h1{margin:0;font-size:24px}.top{display:flex;justify-content:space-between;gap:30px}.muted{color:#667887}.cards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:28px 0}.card{border:1px solid #ccd5dc;padding:12px}.card b{display:block;font-size:15px;margin-bottom:5px}table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #dfe5e9;text-align:left}th{font-size:11px;text-transform:uppercase;color:#667887}.totals{margin:20px 0 0 auto;width:280px}.totals div{display:flex;justify-content:space-between;padding:5px}.grand{font-size:16px;border-top:2px solid #222}.sign{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:65px}.sign div{border-top:1px solid #666;padding-top:6px;color:#667887}@media print{button{display:none}}</style></head><body>'+
   '<div class="top"><div><h1>'+esc(co.legalName||co.name||'Workshop Manager')+'</h1><div class="muted">'+esc([co.email,co.phone].filter(Boolean).join(' · '))+'</div></div><div><b>'+esc(title)+'</b><br>'+esc(no)+'<br>'+new Date().toLocaleDateString('de-DE')+'</div></div>'+
   '<div class="cards"><div class="card"><b>'+esc(cu?.displayName||'')+'</b>'+esc(cu?.street||'')+'<br>'+esc([cu?.postalCode,cu?.city].filter(Boolean).join(' '))+'</div><div class="card"><b>'+esc(v?.licensePlate||'')+'</b>'+esc([v?.make,v?.model,v?.type].filter(Boolean).join(' '))+'<br>VIN '+esc(v?.vin||'–')+' · km '+esc(o.mileageIn??v?.mileage??'–')+'</div></div>'+
   '<p><b>Kundenauftrag:</b> '+esc(o.customerRequest||'–')+'</p>'+
   '<table><thead><tr><th>Pos.</th><th>Art.-Nr.</th><th>Bezeichnung</th><th>Menge</th>'+(showPrices?'<th>EP netto</th><th>Gesamt</th>':'')+'</tr></thead><tbody>'+rows+'</tbody></table>'+
   (showPrices?'<div class="totals"><div><span>Netto</span><b>'+docMoney(t.net)+'</b></div><div><span>USt.</span><b>'+docMoney(t.vat)+'</b></div><div class="grand"><span>Brutto</span><b>'+docMoney(t.gross)+'</b></div></div>':'')+
   '<div class="sign"><div>Werkstatt / Ausgabe</div><div>Kunde / Empfang bestätigt</div></div></body></html>');
   w.document.close(); w.focus(); setTimeout(()=>w.print(),250);
  }catch(e){w.close();toast(e.message,true)}
 })();
}
async function createDeliveryNote(orderId){
 try{
  const d=await api('/work-orders/'+orderId+'/delivery-note',{method:'POST'});
  toast('Lieferschein '+d.number+' erstellt.');
  await loadAll();
  printWorkDocument(orderId,'delivery-note',d.number);
 }catch(e){toast(e.message,true)}
}

/* Replace the old vertical order detail with a compact service-advisor workspace. */
openOrder = async function(id){
 state.selectedOrder=id;renderOrderBoard();
 try{
  const d=await api('/work-orders/'+id),o=d.order,v=vehicle(o.vehicleId),cu=customer(o.customerId),editable=o.status<10,next=nextStatus(o.status),tot=docTotals(d.lines);
  const actions=
   (editable?'<button class="secondary small" id="editOrderBtn">Bearbeiten</button>':'')+
   '<button class="secondary small" id="printOrderBtn">Drucken</button>'+
   '<button class="secondary small" id="deliveryNoteBtn">Lieferschein</button>';
  const steps=[['Anlage',0],['Planung',1],['Ankunft',2],['Annahme',3],['Diagnose',4],['Freigabe',5],['Freigegeben',6],['Arbeit',7],['QC',8],['Fertig',9],['Rechnung',10],['Abgeschlossen',11]];
  $('orderDetail').innerHTML=
   '<div class="document-workspace">'+docHeader('WERKSTATTAUFTRAG',o.number,workStatus[o.status]||o.status,badge(workStatus[o.status]),cu,v,actions)+
   '<div class="doc-meta-strip"><div><span>Fertigstellung</span><b>'+fmtDateTime(o.promisedAt)+'</b></div><div><span>km bei Annahme</span><b>'+esc(o.mileageIn??v?.mileage??'–')+'</b></div><div><span>Tank/Ladung</span><b>'+esc(o.fuelOrChargeLevel||'–')+'</b></div><div><span>Auftragswert</span><b>'+docMoney(tot.gross)+'</b></div></div>'+
   '<div class="doc-progress">'+steps.map(([n,s])=>'<span class="'+(o.status===s?'current':o.status>s?'done':'')+'">'+esc(n)+'</span>').join('')+'</div>'+
   '<div class="doc-toolbar">'+
     (editable?'<button class="primary" id="addLineBtn">+ Position</button><button class="secondary" id="addPartBtn">Lagerteil</button><button class="secondary" id="openAagBtn">AAG-Katalog</button><span class="toolbar-sep"></span><button class="secondary" id="approvalBtn">Kundenfreigabe</button><button class="secondary" id="startTimeBtn">Zeit starten</button>':'')+
     (next!==null&&o.status<10?'<button class="secondary push-right" id="nextStatusBtn">Weiter: '+esc(workStatus[next])+' →</button>':'')+
     (o.status===9?'<button class="primary push-right" id="invoiceBtn">Rechnung erzeugen</button>':'')+
   '</div>'+
   '<div class="doc-tabs"><button class="active" data-doc-tab="positions">Positionen</button><button data-doc-tab="order">Auftrag & Diagnose</button><button data-doc-tab="time">Zeiten</button><button data-doc-tab="approval">Freigaben & Prüfung</button></div>'+
   '<section data-doc-pane="positions" class="doc-pane"><div class="doc-main-grid"><div>'+docPositionTable(d.lines,editable,'orderline')+'</div>'+docTotalsBox(d.lines)+'</div></section>'+
   '<section data-doc-pane="order" class="doc-pane hidden"><div class="doc-info-grid"><div class="doc-info-block"><span>Kundenwunsch</span><p>'+esc(o.customerRequest||'–')+'</p></div><div class="doc-info-block"><span>Diagnose / Befund</span><p>'+esc(o.diagnosis||'–')+'</p></div></div></section>'+
   '<section data-doc-pane="time" class="doc-pane hidden"><div class="doc-list">'+(d.times.length?d.times.map(t=>'<div><span><b>'+esc(employee(t.employeeId)?.name||'Mitarbeiter')+'</b><small>'+fmtDateTime(t.startedAt)+' · '+esc(t.activity||'Arbeitszeit')+'</small></span>'+(t.endedAt?'<b>'+fmtDateTime(t.endedAt)+'</b>':'<button class="secondary small" data-stop-time="'+t.id+'">Stop</button>')+'</div>').join(''):empty('Keine Zeiterfassung.'))+'</div></section>'+
   '<section data-doc-pane="approval" class="doc-pane hidden"><div class="doc-info-grid"><div><h4>Kundenfreigaben</h4><div class="doc-list">'+(d.approvals?.length?d.approvals.map(a=>'<div><span><b>'+docMoney(a.offeredGross)+'</b><small>'+esc(a.channel||'')+'</small></span><span class="badge '+badge(approvalStatus[a.status])+'">'+esc(approvalStatus[a.status]||a.status)+'</span></div>').join(''):empty('Keine Freigaben.'))+'</div></div><div><h4>Prüfprotokolle</h4><div class="doc-list">'+((state.checklistRuns||[]).filter(r=>r.workOrderId===o.id).map(r=>{const t=state.checklists.find(x=>(x.template||x).id===r.checklistTemplateId);return'<div><span><b>'+esc((t?.template||t)?.name||'Checkliste')+'</b><small>'+fmtDateTime(r.startedAt)+'</small></span><span class="badge '+badge(r.completedAt?'fertig':'offen')+'">'+(r.completedAt?'Fertig':'Offen')+'</span></div>'}).join('')||empty('Keine Prüfprotokolle.'))+'</div></div></div></section>'+
   '</div>';
  $('orderDetail').classList.remove('hidden'); docTabs($('orderDetail'));
  $('editOrderBtn')&&($('editOrderBtn').onclick=()=>workOrderEditModal(o));
  $('printOrderBtn').onclick=()=>printWorkDocument(id);
  $('deliveryNoteBtn').onclick=()=>createDeliveryNote(id);
  $('addLineBtn')&&($('addLineBtn').onclick=()=>lineModal(id));
  $('addPartBtn')&&($('addPartBtn').onclick=()=>inventoryPartModal(id));
  $('openAagBtn')&&($('openAagBtn').onclick=()=>{page('catalog');setTimeout(()=>$('aagQuery')?.focus(),50)});
  $('approvalBtn')&&($('approvalBtn').onclick=()=>approvalModal(id));
  $('startTimeBtn')&&($('startTimeBtn').onclick=()=>timeStartModal(id));
  $('nextStatusBtn')&&($('nextStatusBtn').onclick=()=>transition(id,next));
  $('invoiceBtn')&&($('invoiceBtn').onclick=()=>createInvoice(id));
  document.querySelectorAll('[data-orderline-edit]').forEach(b=>b.onclick=()=>lineEditModal(id,d.lines.find(l=>l.id===b.dataset.orderlineEdit)));
  document.querySelectorAll('[data-orderline-delete]').forEach(b=>b.onclick=()=>deleteOrderLine(id,b.dataset.orderlineDelete));
  document.querySelectorAll('[data-stop-time]').forEach(b=>b.onclick=()=>stopTime(id,b.dataset.stopTime));
 }catch(e){toast(e.message,true)}
};

openQuote = async function(quoteId){
 const q=state.quotes.find(x=>x.quoteId===quoteId); if(!q)return;
 try{
  const d=await api('/work-orders/'+q.workOrder.id),o=d.order,cu=customer(o.customerId),v=vehicle(o.vehicleId),editable=!q.converted;
  const actions='<button class="secondary small" id="quotePrintBtn">Drucken</button>'+(editable?'<button class="primary small" id="quoteConvertBtn">In Auftrag wandeln</button>':'<button class="primary small" id="quoteOpenOrderBtn">Auftrag öffnen</button>');
  $('quoteDetail').innerHTML=
   '<div class="document-workspace">'+docHeader('ANGEBOT / KOSTENVORANSCHLAG',q.quoteNumber,q.converted?'In Auftrag umgewandelt':'Offen',badge(q.converted?'aktiv':'offen'),cu,v,actions)+
   '<div class="doc-meta-strip"><div><span>Erstellt</span><b>'+new Date().toLocaleDateString('de-DE')+'</b></div><div><span>Positionen</span><b>'+d.lines.length+'</b></div><div><span>Netto</span><b>'+docMoney(q.netTotal)+'</b></div><div><span>Brutto</span><b>'+docMoney(q.grossTotal)+'</b></div></div>'+
   '<div class="doc-toolbar">'+(editable?'<button class="primary" id="quoteAddLineBtn">+ Position</button><button class="secondary" id="quoteAddPartBtn">Lagerteil</button><button class="secondary" id="quoteAagBtn">AAG-Katalog</button><span class="toolbar-sep"></span><button class="secondary" id="quoteApprovalBtn">Kundenfreigabe</button>':'')+'</div>'+
   '<div class="doc-tabs"><button class="active" data-doc-tab="positions">Kalkulation</button><button data-doc-tab="request">Kundenwunsch</button><button data-doc-tab="approval">Freigaben</button></div>'+
   '<section data-doc-pane="positions" class="doc-pane"><div class="doc-main-grid"><div>'+docPositionTable(d.lines,editable,'quoteline')+'</div>'+docTotalsBox(d.lines)+'</div></section>'+
   '<section data-doc-pane="request" class="doc-pane hidden"><div class="doc-info-grid"><div class="doc-info-block"><span>Kundenwunsch / Leistungsumfang</span><p>'+esc(o.customerRequest||'–')+'</p></div><div class="doc-info-block"><span>Interne Notiz / Diagnose</span><p>'+esc(o.diagnosis||'–')+'</p></div></div></section>'+
   '<section data-doc-pane="approval" class="doc-pane hidden"><div class="doc-list">'+(d.approvals?.length?d.approvals.map(a=>'<div><span><b>'+docMoney(a.offeredGross)+'</b><small>'+esc(a.channel||'')+'</small></span><span class="badge '+badge(approvalStatus[a.status])+'">'+esc(approvalStatus[a.status]||a.status)+'</span></div>').join(''):empty('Keine Kundenfreigabe.'))+'</div></section>'+
   '</div>';
  $('quoteDetail').classList.remove('hidden'); docTabs($('quoteDetail'));
  $('quoteAddLineBtn')&&($('quoteAddLineBtn').onclick=()=>lineModal(o.id,async()=>{await loadAll();await openQuote(quoteId)}));
  $('quoteAddPartBtn')&&($('quoteAddPartBtn').onclick=()=>inventoryPartModal(o.id,async()=>{await loadAll();await openQuote(quoteId)}));
  $('quoteAagBtn')&&($('quoteAagBtn').onclick=()=>{state.selectedOrder=o.id;page('catalog');setTimeout(()=>$('aagQuery')?.focus(),50)});
  $('quoteApprovalBtn')&&($('quoteApprovalBtn').onclick=()=>approvalModal(o.id,async()=>{await loadAll();await openQuote(quoteId)}));
  $('quoteConvertBtn')&&($('quoteConvertBtn').onclick=()=>convertQuote(quoteId));
  $('quoteOpenOrderBtn')&&($('quoteOpenOrderBtn').onclick=()=>{page('orders');openOrder(o.id)});
  $('quotePrintBtn').onclick=()=>printQuote(quoteId);
  document.querySelectorAll('[data-quoteline-edit]').forEach(b=>b.onclick=()=>lineEditModal(o.id,d.lines.find(l=>l.id===b.dataset.quotelineEdit)));
  document.querySelectorAll('[data-quoteline-delete]').forEach(b=>b.onclick=async()=>{await deleteOrderLine(o.id,b.dataset.quotelineDelete);await loadAll();await openQuote(quoteId)});
 }catch(e){toast(e.message,true)}
};

invoiceDetail = async function(id){
 try{
  const d=await api('/invoices/'+id),i=d.invoice,cu=customer(i.customerId),v=vehicle(i.vehicleId),editable=i.status!==5&&i.status!==6,open=Math.max(0,Number(i.grossTotal||0)-Number(i.paidTotal||0));
  const host=$('invoiceDetailPanel');
  if(!host)return;
  const actions='<button class="secondary small" id="invoicePrintBtn">Drucken / PDF</button>'+
   (open>0&&editable?'<button class="primary small" id="invoicePayBtn">Zahlung erfassen</button>':'')+
   (editable?'<button class="secondary small danger-text" id="invoiceCorrectBtn">Storno / Gutschrift</button>':'');
  host.innerHTML='<div class="document-workspace">'+docHeader('RECHNUNG',i.number,invoiceStatus[i.status]||i.status,badge(invoiceStatus[i.status]),cu,v,actions)+
   '<div class="doc-meta-strip"><div><span>Rechnungsdatum</span><b>'+esc(i.issueDate)+'</b></div><div><span>Fällig</span><b>'+esc(i.dueDate)+'</b></div><div><span>Bezahlt</span><b>'+docMoney(i.paidTotal)+'</b></div><div><span>Offen</span><b>'+docMoney(open)+'</b></div></div>'+
   '<div class="doc-tabs"><button class="active" data-doc-tab="positions">Positionen</button><button data-doc-tab="payments">Zahlungen</button></div>'+
   '<section data-doc-pane="positions" class="doc-pane"><div class="doc-main-grid"><div>'+docPositionTable(d.lines,false,'invline')+'</div>'+docTotalsBox(d.lines,i.paidTotal)+'</div></section>'+
   '<section data-doc-pane="payments" class="doc-pane hidden"><div class="doc-list">'+(d.payments?.length?d.payments.map(p=>'<div><span><b>'+docMoney(p.amount)+'</b><small>'+fmtDateTime(p.paidAt)+' · '+esc(p.reference||'ohne Referenz')+'</small></span></div>').join(''):empty('Noch keine Zahlungen.'))+'</div></section></div>';
  host.classList.remove('hidden'); docTabs(host); host.scrollIntoView({behavior:'smooth',block:'start'});
  $('invoicePrintBtn').onclick=()=>printInvoice(id);
  $('invoicePayBtn')&&($('invoicePayBtn').onclick=()=>paymentModal(id));
  $('invoiceCorrectBtn')&&($('invoiceCorrectBtn').onclick=()=>reverseInvoiceModal(id));
 }catch(e){toast(e.message,true)}
};

function renderDeliveryNotes(){
 const host=$('deliveryNoteRows'); if(!host)return;
 host.innerHTML=(state.deliveryNotes||[]).map(x=>'<tr><td><b>'+esc(x.number)+'</b></td><td>'+fmtDate(x.createdAt)+'</td><td>'+esc(x.workOrderNumber||'')+'</td><td>'+esc(x.customerName||'')+'</td><td>'+esc(x.vehiclePlate||'')+'</td><td><button class="secondary small" data-print-delivery="'+x.id+'">Drucken</button></td></tr>').join('')||'<tr><td colspan="6">Noch keine Lieferscheine.</td></tr>';
 document.querySelectorAll('[data-print-delivery]').forEach(b=>{const x=(state.deliveryNotes||[]).find(n=>n.id===b.dataset.printDelivery);b.onclick=()=>x&&printWorkDocument(x.workOrderId,'delivery-note',x.number)});
}
const __baseRenderAll=renderAll;
renderAll=function(){__baseRenderAll();renderDeliveryNotes();};

function wireDocSearch(inputId,rowSelector){
 const i=$(inputId);if(!i)return;
 i.oninput=()=>{const q=i.value.trim().toLowerCase();document.querySelectorAll(rowSelector).forEach(r=>r.style.display=!q||r.textContent.toLowerCase().includes(q)?'':'none')};
}
wireDocSearch('quoteSearch','.quote-list tbody tr');
wireDocSearch('invoiceSearch','.invoice-list tbody tr');
wireDocSearch('deliverySearch','.delivery-list tbody tr');
