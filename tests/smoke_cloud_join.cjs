// Executable browser-like smoke test for the Cloud guest join flow.
// Uses no real account credentials, no network and no browser storage.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('cloud/portal/join-room.js','utf8');
const elements={};
const calls=[],historyCalls=[];
function el(id){
 if(!elements[id]){
  const e={id,hidden:false,disabled:false,value:'',textContent:'',className:'',
   listeners:{},children:[],replaceChildren(){this.children=[]},
   append(child){this.children.push(child)},
   addEventListener(name,fn){this.listeners[name]=fn},
   querySelector(){return {disabled:false}},
   };
  elements[id]=e;
 }
 return elements[id];
}
const document={getElementById:el,createElement:tag=>({tag,textContent:''})};
const token='V'.repeat(44);
const location={hash:'#room-invite='+token,pathname:'/join-room.html',origin:'https://135ercloud.grow-central.de',protocol:'https:'};
const room='room_betatest',device='aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa';
let requestSequence=0;
class Socket {
 static OPEN=1;
 constructor(url){this.url=url;this.readyState=Socket.OPEN;Socket.last=this;
  setImmediate(()=>this.onopen?.());}
 send(raw){
  const msg=JSON.parse(raw);
  calls.push({socket:msg});
  if(msg.type==='auth')setImmediate(()=>this.onmessage?.({data:JSON.stringify({
   type:'auth_ok',guest_scoped:true,room_id:room,device_id:device,role:'grower'})}));
  if(msg.type==='read')setImmediate(()=>this.onmessage?.({data:JSON.stringify({
   type:'read_result',ok:true,request_id:msg.request_id,
   data:msg.path.endsWith('/plants')?{plants:[{name:'Basilikum',phase:'vegetative'}]}:
                                     {entries:[{title:'Wasser',text:'Testnotiz'}]}
  })}));
 }
 close(){this.readyState=3;this.onclose?.();}
}
const fetch=async(url,options)=>{
 calls.push({url,options});
 let data={};
 if(url==='/api/v2/account/login')data={access_token:'x'.repeat(48)};
 else if(url==='/api/v2/collaboration/accept')data={
  room_id:room,device_id:device,role:'grower'};
 else throw Error('Unexpected API '+url);
 return {ok:true,status:200,json:async()=>data};
};
const ctx={
 document,location,history:{replaceState:(...args)=>historyCalls.push(args)},
 fetch,WebSocket:Socket,URL,URLSearchParams,
 crypto:{randomUUID:()=> '12345678-1234-4234-8234-'+String(++requestSequence).padStart(12,'0')},
 setTimeout,clearTimeout,console,Promise,
};
vm.createContext(ctx);
vm.runInContext(source,ctx,{filename:'join-room.js'});
el('email').value='grower@example.invalid';
el('password').value='a test-only passphrase';
(async()=>{
 await el('loginForm').listeners.submit({preventDefault(){}});
 assert.strictEqual(el('roomPanel').hidden,false);
 assert.strictEqual(el('accountPanel').hidden,true);
 assert.strictEqual(historyCalls.length,1);
 assert(el('membership').textContent.includes('grower'));
 assert(el('plants').children[0].textContent.includes('Basilikum'));
 assert(el('journal').children[0].textContent.includes('Wasser'));
 const redeemed=calls.find(v=>v.url==='/api/v2/collaboration/accept');
 assert(redeemed && JSON.parse(redeemed.options.body).invite_token===token);
 assert.strictEqual(redeemed.options.credentials,'omit');
 assert(calls.some(v=>v.socket?.type==='auth' && v.socket.room_id===room));
 assert(calls.filter(v=>v.socket?.type==='read').every(v=>v.socket.path.includes(room)));
 el('logout').listeners.click();
 assert.strictEqual(el('roomPanel').hidden,true);
 console.log('PASS: cloud join, account auth, one-use invite, scoped socket reads, logout');
})().catch(e=>{console.error(e);process.exitCode=1});
