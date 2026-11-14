"""Grow Central paired and authenticated outbound-only device presence.
No remote device operations are accepted in this phase.
"""
import asyncio,base64,json,logging,os,time,socket,re,subprocess
from urllib.parse import urlparse
import httpx
from websockets.asyncio.client import connect
from .device_identity import ensure_identity
from .agent_v2 import LOCAL_API, local_headers
log=logging.getLogger("growcentral.cloud.remote")
URL=os.getenv("GC_CLOUD_URL","https://135ercloud.grow-central.de").rstrip("/")
def b64(value):
 return base64.urlsafe_b64encode(value).decode().rstrip("=")
async def session():
 parsed=urlparse(URL)
 if parsed.scheme!="https" or parsed.hostname!="135ercloud.grow-central.de" or parsed.path not in ("","/"):
  raise RuntimeError("unapproved cloud origin")
 identity=ensure_identity()
 if not identity.device_id:raise RuntimeError("device not paired")
 async with httpx.AsyncClient(timeout=12,trust_env=False,transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
  r=await client.post(URL+"/api/v2/device/challenge",json={"device_id":identity.device_id})
  r.raise_for_status()
  nonce=r.json()["nonce"]
 timestamp=int(time.time())
 payload=f"GCLOUD2\n{identity.device_id}\n{nonce}\n{timestamp}".encode()
 auth={"type":"auth","device_id":identity.device_id,"nonce":nonce,"timestamp":timestamp,
       "signature":b64(identity.private_key.sign(payload))}
 ipv4=socket.getaddrinfo(parsed.hostname,443,socket.AF_INET,socket.SOCK_STREAM)[0][4][0]
 async with connect(URL.replace("https://","wss://",1)+"/api/v2/device/connect",
                    host=ipv4,port=443,open_timeout=12,ping_interval=20,ping_timeout=15,max_size=262144) as ws:
  await ws.send(json.dumps(auth))
  result=json.loads(await asyncio.wait_for(ws.recv(),timeout=12))
  if result.get("type")!="auth_ok" or result.get("device_id")!=identity.device_id:
   raise RuntimeError("cloud auth rejected")
  log.info("Device channel authenticated")
  async with httpx.AsyncClient(timeout=8,trust_env=False) as local:
   await serve(ws,local)
  return
CONTROL_PATHS={
 "lamp":"/api/mars-hydro/ble/fast-lamp-control",
 "fan":"/api/mars-hydro/ble/fast-fan-control",
}
def validate_control(req):
 kind=req.get("kind");action=req.get("action");value=req.get("value")
 if kind not in CONTROL_PATHS or type(value) is not int or req.get("confirm_physical_change") is not True:
  return None
 if action=="power" and value in (0,1):return CONTROL_PATHS[kind]
 if kind=="lamp" and action=="brightness" and 10<=value<=100:return CONTROL_PATHS[kind]
 if kind=="fan" and action=="speed" and 25<=value<=100:return CONTROL_PATHS[kind]
 return None
READ_PATHS={
 "/api/health",
 "/api/mars-hydro/ble/fast-fan-status",
 "/api/mars-hydro/ble/fast-lamp-status",
 "/api/v1/homekit/status",
 "/api/v1/rooms",
 "/api/mars-history/summary",
 "/api/cloud/status",
 "/api/v1/camera/status",
 "/api/v1/smarthome/overview",
 "/api/v1/camera/controls",
 "/api/v1/smarthome/overview",
}
async def serve(ws,local):
 async for raw in ws:
  try:req=json.loads(raw)
  except (ValueError,TypeError):continue
  if not isinstance(req,dict):continue
  request_id=req.get("request_id")
  if not isinstance(request_id,str) or not 1<=len(request_id)<=64:continue
  if req.get("type")=="photo_create":
   room_id=req.get("room_id");image=req.get("image_data_url");title=req.get("title","Foto")
   note=req.get("note","");tags=req.get("tags",[])
   valid=(isinstance(room_id,str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,120}",room_id)
     and isinstance(image,str) and image.startswith("data:image/jpeg;base64,")
     and 1000<=len(image)<=180000 and isinstance(title,str) and 1<=len(title)<=120
     and isinstance(note,str) and len(note)<=5000 and isinstance(tags,list)
     and len(tags)<=20 and all(isinstance(t,str) and len(t)<=40 for t in tags)
     and req.get("confirm_write") is True)
   if not valid:
    await ws.send(json.dumps({"type":"photo_result","request_id":request_id,
                              "ok":False,"error":"invalid_photo_upload"}))
    continue
   try:
    result=await local.post(LOCAL_API+"/api/v1/grow-photos",headers=local_headers(),
      json={"room_id":room_id,"title":title,"note":note,"tags":tags,"image_data_url":image},
      timeout=20)
    result.raise_for_status();photo=result.json()
    response={"type":"photo_result","request_id":request_id,"ok":True,
              "photo_id":str(photo.get("photo_id",""))[:128]}
   except Exception as exc:
    response={"type":"photo_result","request_id":request_id,"ok":False,
              "error":type(exc).__name__,"no_retry":True}
   await ws.send(json.dumps(response))
   continue
  if req.get("type")=="photo_frame":
   photo_id=req.get("photo_id")
   if not isinstance(photo_id,str) or not re.fullmatch(r"photo_[a-zA-Z0-9_-]{1,100}",photo_id):
    await ws.send(json.dumps({"type":"photo_frame_result","request_id":request_id,
                              "ok":False,"error":"invalid_photo_id"}));continue
   try:
    r=await local.get(LOCAL_API+"/api/v1/grow-photos/"+photo_id,
       headers=local_headers(),timeout=10)
    r.raise_for_status()
    mime=r.headers.get("content-type","").split(";")[0]
    if mime not in {"image/jpeg","image/png","image/webp"}:
     raise RuntimeError("photo_mime_invalid")
    raw=r.content
    if len(raw)>145000:
     def compress_photo():
      result=subprocess.run(
       ["ffmpeg","-hide_banner","-loglevel","error","-i","pipe:0",
        "-vf","scale=640:-2","-frames:v","1","-q:v","8",
        "-f","image2pipe","-vcodec","mjpeg","pipe:1"],
       input=raw,capture_output=True,timeout=10,check=False)
      if result.returncode or len(result.stdout)>145000 or len(result.stdout)<1000:
       raise RuntimeError("photo_preview_encoding_failed")
      return result.stdout
     raw=await asyncio.to_thread(compress_photo)
     mime="image/jpeg"
    response={"type":"photo_frame_result","request_id":request_id,"ok":True,
      "image":"data:"+mime+";base64,"+base64.b64encode(raw).decode()}
   except Exception as exc:
    response={"type":"photo_frame_result","request_id":request_id,"ok":False,
              "error":type(exc).__name__}
   await ws.send(json.dumps(response))
   continue
  if req.get("type") in ("plant_create","plant_update"):
   room_id=req.get("room_id");name=req.get("name");plant_id=req.get("plant_id")
   plant_type=req.get("plant_type","other");phase=req.get("phase","vegetative")
   strain=req.get("strain","");start_date=req.get("start_date","");notes=req.get("notes","")
   valid=(isinstance(room_id,str) and re.fullmatch(r"room_[A-Za-z0-9_-]{1,110}",room_id)
     and isinstance(name,str) and 1<=len(name.strip())<=80
     and isinstance(strain,str) and len(strain)<=120
     and isinstance(start_date,str) and (not start_date or re.fullmatch(r"\d{4}-\d{2}-\d{2}",start_date))
     and isinstance(notes,str) and len(notes)<=2000
     and plant_type in ("automatic","feminized","mother","clone","other")
     and phase in ("germination","seedling","vegetative","flowering","flush","finish","harvest","completed","other")
     and req.get("confirm_write") is True)
   if req["type"]=="plant_update":
    valid=valid and isinstance(plant_id,str) and re.fullmatch(r"plant_[A-Za-z0-9_-]{1,110}",plant_id)
   if not valid:
    await ws.send(json.dumps({"type":"plant_result","request_id":request_id,"ok":False,
                              "error":"invalid_plant_data"}));continue
   try:
    path="/api/v1/rooms/"+room_id+"/plants"
    if req["type"]=="plant_update":path+="/"+plant_id
    body={"name":name.strip(),"strain":strain,"plant_type":plant_type,
          "start_date":start_date,"phase":phase,"notes":notes}
    if req["type"]=="plant_create":
     result=await local.post(LOCAL_API+path,headers=local_headers(),json=body,timeout=12)
    else:
     result=await local.put(LOCAL_API+path,headers=local_headers(),json=body,timeout=12)
    result.raise_for_status();plant=result.json()
    response={"type":"plant_result","request_id":request_id,"ok":True,
              "room_id":room_id,"plant_id":str(plant.get("id",""))[:128]}
   except Exception as exc:
    response={"type":"plant_result","request_id":request_id,"ok":False,
              "error":type(exc).__name__,"no_retry":True}
   await ws.send(json.dumps(response))
   continue
  if req.get("type")=="journal_create":
   room_id=req.get("room_id");title=req.get("title");note=req.get("text","");category=req.get("category","note")
   valid=(isinstance(room_id,str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,120}",room_id)
      and isinstance(title,str) and 1<=len(title.strip())<=120
      and isinstance(note,str) and len(note)<=5000
      and category in {"note","observation","watering","feeding","training","other"}
      and req.get("confirm_write") is True)
   if not valid:
    await ws.send(json.dumps({"type":"journal_result","request_id":request_id,"ok":False,
                              "error":"invalid_journal_entry"}))
    continue
   try:
    path="/api/v1/rooms/"+room_id+"/journal"
    body={"title":title.strip(),"text":note,"category":category}
    result=await local.post(LOCAL_API+path,headers=local_headers(),json=body,timeout=10)
    result.raise_for_status()
    entry=result.json()
    response={"type":"journal_result","request_id":request_id,"ok":True,"room_id":room_id,
              "entry_id":str(entry.get("id",""))[:128]}
   except Exception as exc:
    response={"type":"journal_result","request_id":request_id,"ok":False,
              "error":type(exc).__name__,"no_retry":True}
   await ws.send(json.dumps(response))
   continue
  if req.get("type")=="control":
   path=validate_control(req)
   if not path:
    await ws.send(json.dumps({"type":"control_result","request_id":request_id,
                              "ok":False,"error":"invalid_or_unconfirmed_control"}))
    continue
   try:
    kind=req["kind"]
    status_path="/api/mars-hydro/ble/fast-"+kind+"-status"
    state=await local.get(LOCAL_API+status_path,headers=local_headers(),timeout=8)
    state.raise_for_status()
    status=state.json()
    if not status.get("fresh") or not status.get("latest"):
     raise RuntimeError("stale_device_status")
    if req["action"]!="power" and not status["latest"].get("power_on"):
     raise RuntimeError("device_power_off")
    body={"action":req["action"],"value":req["value"],"confirm_physical_change":True}
    result=await local.post(LOCAL_API+path,headers=local_headers(),json=body,timeout=22)
    result.raise_for_status()
    reply=result.json()
    if not reply.get("device_report_confirmed"):
     raise RuntimeError("physical_confirmation_missing")
    response={"type":"control_result","request_id":request_id,"ok":True,
              "device_report_confirmed":True,"kind":kind,"action":req["action"]}
   except Exception as exc:
    response={"type":"control_result","request_id":request_id,"ok":False,
              "error":type(exc).__name__,"no_retry":True}
   await ws.send(json.dumps(response))
   continue
  if req.get("type")=="camera_frame":
   try:
    r=await local.get(LOCAL_API+"/api/v1/camera/snapshot/cloud-preview",
       headers=local_headers(),timeout=17)
    if not r.is_success:raise ValueError("camera_http_"+str(r.status_code))
    if r.headers.get("content-type","").split(";")[0]!="image/jpeg":raise ValueError("invalid_image_format")
    if not 1000<=len(r.content)<=145000:raise ValueError("image_size_out_of_bounds")
    response={"type":"camera_result","request_id":request_id,"ok":True,
              "image":"data:image/jpeg;base64,"+base64.b64encode(r.content).decode()}
   except Exception as exc:
    response={"type":"camera_result","request_id":request_id,"ok":False,
              "error":type(exc).__name__}
   await ws.send(json.dumps(response))
   continue
  if req.get("type")!="read":continue
  path=req.get("path")
  is_room_path=isinstance(path,str) and re.fullmatch(r"/api/v1/rooms/[a-zA-Z0-9_-]{1,120}/(journal|plants|events)(\?limit=[0-9]{1,3})?",path)
  is_camera_query=isinstance(path,str) and re.fullmatch(r"/api/v1/camera/controls\?camera_id=cam[0-9]{1,3}",path)
  is_smart_query=path=="/api/v1/smarthome/overview?refresh=true"
  if path not in READ_PATHS and not is_room_path and not is_camera_query and not is_smart_query:
   response={"type":"read_result","request_id":request_id,"ok":False,"error":"path_not_allowed"}
  else:
   try:
    r=await local.get(LOCAL_API+path,headers=local_headers(),timeout=7)
    if not r.is_success:raise ValueError("local_http_"+str(r.status_code))
    payload=r.json()
    if not isinstance(payload,dict):raise ValueError("invalid_payload")
    if path=="/api/v1/homekit/status":
     payload={k:payload.get(k) for k in ("running","paired","accessories_exported","accessories")}
    serialized=json.dumps(payload,ensure_ascii=False)
    if len(serialized)>180000:raise ValueError("response_too_large")
    response={"type":"read_result","request_id":request_id,"ok":True,"path":path,"data":payload}
   except Exception as exc:
    response={"type":"read_result","request_id":request_id,"ok":False,"error":type(exc).__name__}
  await ws.send(json.dumps(response,ensure_ascii=False))

async def main():
 logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
 while True:
  try:await session()
  except asyncio.CancelledError:raise
  except Exception as exc:log.warning("Cloud device channel error: %s: %s",type(exc).__name__,str(exc)[:180])
  await asyncio.sleep(20)
if __name__=="__main__":asyncio.run(main())
