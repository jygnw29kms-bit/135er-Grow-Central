(()=>{
const KEY='gc.fullUiLayoutDraft.v2';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const valid=p=>p&&p.version===2&&p.shell&&Array.isArray(p.pages)&&p.pages.length;
const height=v=>v==='s'?'88px':v==='l'?'250px':'160px';
function containerFor(node,section){
  if(!node)return null;
  if(node===section)return null;
  const candidate=node.closest('.master-metric,.master-panel,.pairing-panel,.filterbar,.device-table,.cards-grid,.camera-grid,.rule-list,.system-grid,.master-hero,.master-section-head');
  return candidate&&section.contains(candidate)?candidate:node;
}
function activate(target){
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===target));
  document.querySelectorAll('.master-nav button[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===target));
  window.dispatchEvent(new CustomEvent('gc:view',{detail:{id:target}}));
}
function ensurePage(page){
  let section=document.getElementById(page.target);
  if(section)return section;
  section=document.createElement('section');
  section.id=page.target;
  section.className='view master-view gc-custom-page'+(page.advanced?' advanced-only':'');
  section.innerHTML=`<div class="master-section-head"><div><small>BENUTZERDEFINIERT</small><h2>${esc(page.title||page.label)}</h2><p>Eigene Grow-Central Seite.</p></div></div><div class="gc-layout-custom-grid"></div>`;
  document.querySelector('.master-main')?.appendChild(section);
  return section;
}
function ensureNav(page){
  let button=document.querySelector(`.master-nav button[data-view="${CSS.escape(page.target)}"]`);
  if(!button){
    button=document.createElement('button');button.dataset.view=page.target;button.className='gc-custom-nav';
    button.addEventListener('click',()=>activate(page.target));
    document.querySelector('.master-nav')?.appendChild(button);
  }
  let icon=button.querySelector('i'),label=button.querySelector('span');
  if(!icon){icon=document.createElement('i');button.prepend(icon)}
  if(!label){label=document.createElement('span');button.appendChild(label)}
  icon.textContent=page.icon||'?';label.textContent=page.label||page.title||page.id;
  button.hidden=page.visible===false;
  button.classList.toggle('advanced-only',!!page.advanced);
  button.classList.toggle('sub',!!page.parent);
  button.style.order=String(100+(page._order||0));
  document.querySelector('.master-nav')?.appendChild(button);
  return button;
}
function renderCustom(widget,grid){
  if(widget.type==='spacer'){
    const el=document.createElement('div');el.className='gc-layout-spacer';el.dataset.gcLayoutWidget=widget.id;return el;
  }
  const el=document.createElement('article');
  el.className='master-panel gc-layout-custom-widget';el.dataset.gcLayoutWidget=widget.id;
  el.innerHTML=`<div class="master-panel-head"><div><small>${esc(widget.kicker||widget.type.toUpperCase())}</small><h3>${esc(widget.title||'Baustein')}</h3></div></div><p class="master-copy">${esc(widget.text||'')}</p>`;
  grid.appendChild(el);return el;
}
function applyWidgetCopy(widget,el){
  if(!el)return;
  if(widget.title){const h=el.querySelector(':scope > .master-panel-head h3,:scope > header b,:scope > h3');if(h)h.textContent=widget.title}
  if(widget.kicker){const k=el.querySelector(':scope > .master-panel-head small,:scope > small.widget-kicker');if(k)k.textContent=widget.kicker}
  if(widget.text){const t=el.querySelector(':scope > .master-copy,:scope > p');if(t)t.textContent=widget.text}
}
function resolveWidget(widget,page,section){
  if(widget.binding){
    const bound=document.getElementById(widget.binding);
    const resolved=containerFor(bound,section);
    if(resolved)return resolved;
  }
  if(widget.type==='hero')return section.querySelector('.master-hero,.master-section-head');
  if(widget.type==='status'){
    const status=section.querySelector('#statusBanner,.master-health-banner');
    if(status)return containerFor(status,section);
  }
  return null;
}
function applyPage(page,gap){
  const section=ensurePage(page);ensureNav(page);
  section.hidden=page.visible===false;
  section.classList.toggle('advanced-only',!!page.advanced);
  const heading=section.querySelector('.master-section-head h2');if(heading&&page.title)heading.textContent=page.title;
  let custom=section.querySelector(':scope > .gc-layout-custom-grid');
  if(!custom){custom=document.createElement('div');custom.className='gc-layout-custom-grid';const head=section.querySelector(':scope > .master-section-head');head?.after(custom)}
  custom.innerHTML='';
  const parentOrders=new Map();
  page.widgets.forEach((widget,index)=>{
    let el=resolveWidget(widget,page,section);
    if(!el)el=renderCustom(widget,custom);
    if(!el)return;
    el.dataset.gcLayoutWidget=widget.id;
    el.hidden=widget.visible===false;
    el.classList.toggle('advanced-only',!!widget.advanced);
    el.style.setProperty('--gc-layout-span',String(widget.width||12));
    el.style.gridColumn=`span ${Math.max(1,Math.min(12,Number(widget.width)||12))}`;
    el.style.minHeight=height(widget.height);
    applyWidgetCopy(widget,el);
    const parent=el.parentElement;
    if(parent&&parent!==section&&parent!==custom){
      if(!parentOrders.has(parent))parentOrders.set(parent,[]);
      parentOrders.get(parent).push([index,el]);
    }
  });
  parentOrders.forEach((rows,parent)=>{
    if(rows.length<2)return;
    parent.classList.add('gc-layout-runtime-grid');
    parent.style.gridTemplateColumns='repeat(12,minmax(0,1fr))';
    parent.style.gap=`${gap}px`;
    rows.sort((a,b)=>a[0]-b[0]).forEach(([,el])=>parent.appendChild(el));
  });
  custom.style.gridTemplateColumns='repeat(12,minmax(0,1fr))';custom.style.gap=`${gap}px`;
}
function apply(layout){
  if(!valid(layout))return;
  document.documentElement.classList.add('gc-layout-live');
  const shell=layout.shell||{},root=document.querySelector('.master-shell'),sidebar=document.querySelector('.master-sidebar'),main=document.querySelector('.master-main'),top=document.querySelector('.master-topbar');
  const sw=Math.max(160,Math.min(360,Number(shell.sidebarWidth)||224)),gap=Math.max(0,Math.min(40,Number(shell.gap)||10));
  document.documentElement.style.setProperty('--gc-layout-gap',`${gap}px`);
  if(root)root.style.gridTemplateColumns=shell.sidebar===false?'1fr':`${sw}px minmax(0,1fr)`;
  if(sidebar){sidebar.hidden=shell.sidebar===false;sidebar.style.width=`${sw}px`;const brand=sidebar.querySelector('.master-brand span,.fm-brand span small');if(brand&&shell.brand)brand.textContent=shell.brand}
  if(top)top.hidden=shell.topbar===false;
  document.documentElement.style.setProperty('--gc-layout-radius',shell.rounded===false?'0px':'8px');
  const targets=new Set(layout.pages.map(p=>p.target));
  document.querySelectorAll('.master-nav button[data-view]').forEach(button=>{if(!targets.has(button.dataset.view))button.hidden=true});
  layout.pages.forEach((p,i)=>{p._order=i;applyPage(p,gap)});
  const current=document.querySelector('.view.active');if(current&&current.hidden){const d=layout.pages.find(p=>p.default&&p.visible!==false)||layout.pages.find(p=>p.visible!==false);if(d)activate(d.target)}
  window.dispatchEvent(new CustomEvent('gc:layout-applied',{detail:{updatedAt:layout.updatedAt||null}}));
}
async function load(){
  let layout=null;
  try{const r=await fetch('/api/v1/ui-layout',{cache:'no-store',credentials:'same-origin'});if(r.ok)layout=(await r.json())?.layout}catch{}
  if(!valid(layout)){try{const local=JSON.parse(localStorage.getItem(KEY)||'null');if(valid(local))layout=local}catch{}}
  if(valid(layout))apply(layout);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load,{once:true});else load();
})();
