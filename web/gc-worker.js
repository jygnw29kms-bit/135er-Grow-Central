/* Grow Central PWA: shell only; live measurements and commands always network-only. */
const CACHE='gc-shell-20261114-fan-off-1';
const SHELL=['/static/gc-final.css?v=20261114-fan-off-1','/static/gc-final.js?v=20261114-fan-off-1','/static/mars-fc3000-transparent.png','/static/mars-df150m-hires.jpg','/static/gc-hero-leaf.jpg','/static/brand-mark.png','/static/brand-logo.png','/static/gc-icon-192.png','/static/gc-icon-512.png','/static/gc-manifest.webmanifest'];
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const req=event.request,url=new URL(req.url);
 if(req.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/')||url.pathname==='/gc-worker.js')return;
 if(req.mode==='navigate')return;
 if(url.pathname.startsWith('/static/')){
  event.respondWith(fetch(req).then(res=>{
   if(res.ok){const copy=res.clone();caches.open(CACHE).then(cache=>cache.put(req,copy));}
   return res;
  }).catch(()=>caches.match(req)));
 }
});
/* Real Web Push: show the received message immediately, never fetch private
   telemetry or accept cross-origin deep links from payloads. */
self.addEventListener('push',event=>{
 let message={};
 try{message=event.data?event.data.json():{}}catch(_){message={}}
 const title=typeof message.title==='string'?message.title.slice(0,90):'Grow Central · Hinweis';
 const body=typeof message.body==='string'?message.body.slice(0,180):'Neuer Grow-Central-Alarm';
 const tag='gc-room-'+String(message.room_id||'alert').replace(/[^a-zA-Z0-9_-]/g,'').slice(0,80);
 event.waitUntil(self.registration.showNotification(title,{
  body,tag,icon:'/static/gc-icon-192.png',badge:'/static/gc-icon-192.png',
  data:{url:'/'}
 }));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 event.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(windows=>{
  const window=windows.find(w=>w.url.startsWith(self.location.origin));
  return window?window.focus():self.clients.openWindow('/');
 }));
});
