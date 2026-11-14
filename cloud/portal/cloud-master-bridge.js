/* Grow Central Cloud transport for the original Final Master UI.
   Auth stays in the parent portal, no token is copied into this frame. */
(()=>{
 'use strict';
 const nativeFetch=window.fetch.bind(window);
 const pending=new Map();
 const origin=location.origin;
 function ask(kind,payload={}){
  const id=crypto.randomUUID();
  return new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Cloud request timed out'))},32000);
   pending.set(id,{resolve,reject,timer});
   window.parent.postMessage({source:'gc-cloud-master',id,kind,...payload},origin);
  });
 }
 async function compactPhoto(body){
  if(!body||typeof body.image_data_url!=='string')return body;
  const raw=body.image_data_url;
  if(!raw.startsWith('data:image/'))throw new Error('Fotoformat nicht unterstützt');
  const image=new Image();
  await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=raw});
  const canvas=document.createElement('canvas');
  const scale=Math.min(1,960/Math.max(image.naturalWidth,image.naturalHeight));
  canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));
  canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('Bildumwandlung nicht verfügbar');
  ctx.drawImage(image,0,0,canvas.width,canvas.height);
  let encoded=canvas.toDataURL('image/jpeg',0.68);
  for(let i=0;encoded.length>165000&&i<4;i++){
   const previous=document.createElement('canvas');previous.width=canvas.width;previous.height=canvas.height;
   previous.getContext('2d').drawImage(canvas,0,0);
   canvas.width=Math.max(160,Math.round(canvas.width*0.75));canvas.height=Math.max(90,Math.round(canvas.height*0.75));
   ctx.drawImage(previous,0,0,canvas.width,canvas.height);
   encoded=canvas.toDataURL('image/jpeg',0.58);
  }
  if(encoded.length>165000)throw new Error('Foto ist für die Cloud-Vorschau zu groß');
  return {...body,image_data_url:encoded};
 }
 window.fetch=(input,init={})=>{
  let url;
  try{url=new URL(typeof input==='string'?input:input.url,location.href)}
  catch{return nativeFetch(input,init)}
  if(url.origin!==origin||!url.pathname.startsWith('/api/'))return nativeFetch(input,init);
  const method=(init.method||'GET').toUpperCase(),path=url.pathname+url.search;
  let body;
  if(init.body){try{body=JSON.parse(init.body)}catch{return Promise.reject(new Error('Invalid JSON request'))}}
  const transmit=path==='/api/v1/grow-photos'&&method==='POST'
   ?compactPhoto(body).then(compact=>ask('fetch',{path,method,body:compact}))
   :ask('fetch',{path,method,body});
  return transmit.then(result=>new Response(JSON.stringify(result.data??{}),{
   status:result.status,
   headers:{'Content-Type':'application/json','Cache-Control':'no-store'}
  }));
 };
 let cameraImage=null,cameraTimer=null,cameraPending=false;
 const transparent='data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
 function frameRequest(){
  if(!cameraImage||cameraPending||document.hidden)return;
  if(!cameraImage.isConnected){cameraImage=null;return}
  cameraPending=true;
  ask('camera').then(result=>{
   cameraPending=false;
   const img=cameraImage;
   if(!img||!img.isConnected)return;
   const value=result.data?.image;
   if(result.status===200&&typeof value==='string'&&value.startsWith('data:image/jpeg;base64,')&&value.length<220000){
    img.src=value;img.style.display='block';
    const blank=img.parentElement?.querySelector('.camblank');if(blank)blank.style.display='none';
   }
  }).catch(()=>{cameraPending=false});
 }
 function inspectPhotos(){
  for(const img of document.querySelectorAll('img.journal-photo')){
   if(img.dataset.cloudPhotoRequested)return;
   const src=img.getAttribute('src')||'';
   const photoId=src.match(/^\\/api\\/v1\\/grow-photos\\/(photo_[a-zA-Z0-9_-]+)$/)?.[1];
   if(!photoId)continue;
   img.dataset.cloudPhotoRequested='1';img.src=transparent;
   ask('photo',{photo_id:photoId}).then(result=>{
    if(result.status===200&&typeof result.data?.image==='string'&&result.data.image.startsWith('data:image/'))
     img.src=result.data.image;
   }).catch(()=>{});
  }
 }
 function inspectCamera(){
  inspectPhotos();
  const img=document.querySelector('.camframe img');
  if(!img){cameraImage=null;return}
  const src=img.getAttribute('src')||'';
  if(src.startsWith('/api/v1/camera/stream')||src.startsWith(origin+'/api/v1/camera/stream')){
   cameraImage=img;img.src=transparent;frameRequest();
  }
  if(cameraImage!==img&&img.getAttribute('src')===transparent){cameraImage=img;frameRequest()}
 }
 const observer=new MutationObserver(inspectCamera);
 document.addEventListener('DOMContentLoaded',()=>{
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['src']});
  inspectCamera();
  cameraTimer=setInterval(()=>{inspectCamera();frameRequest()},12000);
 });
 window.addEventListener('message',event=>{
  if(event.origin!==origin||event.source!==window.parent)return;
  const msg=event.data;
  if(!msg||msg.source!=='gc-cloud-parent'||typeof msg.id!=='string')return;
  const task=pending.get(msg.id);
  if(!task)return;
  pending.delete(msg.id);clearTimeout(task.timer);task.resolve(msg);
 });
 window.addEventListener('pagehide',()=>{
  observer.disconnect();if(cameraTimer)clearInterval(cameraTimer);
  for(const task of pending.values()){clearTimeout(task.timer);task.reject(new Error('Page unloaded'))}
  pending.clear();
 });
})();
