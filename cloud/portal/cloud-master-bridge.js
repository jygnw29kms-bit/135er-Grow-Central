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
 window.fetch=(input,init={})=>{
  let url;
  try{url=new URL(typeof input==='string'?input:input.url,location.href)}
  catch{return nativeFetch(input,init)}
  if(url.origin!==origin||!url.pathname.startsWith('/api/'))return nativeFetch(input,init);
  const method=(init.method||'GET').toUpperCase(),path=url.pathname+url.search;
  let body;
  if(init.body){try{body=JSON.parse(init.body)}catch{return Promise.reject(new Error('Invalid JSON request'))}}
  return ask('fetch',{path,method,body}).then(result=>new Response(JSON.stringify(result.data??{}),{
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
 function inspectCamera(){
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
