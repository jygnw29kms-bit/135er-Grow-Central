"""Grow Central paired and authenticated outbound-only device presence.
No remote device operations are accepted in this phase.
"""
import asyncio,base64,json,logging,os,time,socket
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
READ_PATHS={
 "/api/health",
 "/api/mars-hydro/ble/fast-fan-status",
 "/api/mars-hydro/ble/fast-lamp-status",
 "/api/v1/homekit/status",
 "/api/v1/rooms",
 "/api/mars-history/summary",
 "/api/cloud/status",
}
async def serve(ws,local):
 async for raw in ws:
  try:req=json.loads(raw)
  except (ValueError,TypeError):continue
  if not isinstance(req,dict):continue
  request_id=req.get("request_id")
  if req.get("type")!="read" or not isinstance(request_id,str) or len(request_id)>64:
   continue
  path=req.get("path")
  if path not in READ_PATHS:
   response={"type":"read_result","request_id":request_id,"ok":False,"error":"path_not_allowed"}
  else:
   try:
    r=await local.get(LOCAL_API+path,headers=local_headers(),timeout=7)
    if not r.is_success:raise ValueError("local_http_"+str(r.status_code))
    payload=r.json()
    if not isinstance(payload,dict):raise ValueError("invalid_payload")
    if path=="/api/v1/homekit/status":
     payload={k:payload.get(k) for k in ("running","paired","accessories_exported")}
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
