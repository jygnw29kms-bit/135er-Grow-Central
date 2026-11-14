"""Grow Central paired and authenticated outbound-only device presence.
No remote device operations are accepted in this phase.
"""
import asyncio,base64,json,logging,os,time
from urllib.parse import urlparse
import httpx
from websockets.asyncio.client import connect
from .device_identity import ensure_identity
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
 async with httpx.AsyncClient(timeout=12,trust_env=False) as client:
  r=await client.post(URL+"/api/v2/device/challenge",json={"device_id":identity.device_id})
  r.raise_for_status()
  nonce=r.json()["nonce"]
 timestamp=int(time.time())
 payload=f"GCLOUD2\n{identity.device_id}\n{nonce}\n{timestamp}".encode()
 auth={"type":"auth","device_id":identity.device_id,"nonce":nonce,"timestamp":timestamp,
       "signature":b64(identity.private_key.sign(payload))}
 async with connect(URL.replace("https://","wss://",1)+"/api/v2/device/connect",
                    open_timeout=12,ping_interval=20,ping_timeout=15,max_size=262144) as ws:
  await ws.send(json.dumps(auth))
  result=json.loads(await asyncio.wait_for(ws.recv(),timeout=12))
  if result.get("type")!="auth_ok" or result.get("device_id")!=identity.device_id:
   raise RuntimeError("cloud auth rejected")
  log.info("Device channel authenticated")
  async for raw in ws:
   try:req=json.loads(raw)
   except (ValueError,TypeError):continue
   if isinstance(req,dict) and req.get("type")=="request":
    await ws.send(json.dumps({"type":"error",
      "request_id":str(req.get("request_id",""))[:64],
      "error":"remote_operations_not_enabled"}))
async def main():
 logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
 while True:
  try:await session()
  except asyncio.CancelledError:raise
  except Exception as exc:log.warning("Cloud device channel error: %s: %s",type(exc).__name__,str(exc)[:180])
  await asyncio.sleep(20)
if __name__=="__main__":asyncio.run(main())
