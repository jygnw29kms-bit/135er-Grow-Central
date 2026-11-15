/* Grow Central Cloud: push-only worker. No cached live measurements or remote commands. */
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
