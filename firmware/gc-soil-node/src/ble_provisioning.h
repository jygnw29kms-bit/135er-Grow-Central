#pragma once
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <mbedtls/base64.h>
#include <mbedtls/ecp.h>
#include <mbedtls/ecdh.h>
#include <mbedtls/gcm.h>
#include <mbedtls/md.h>
#include "identity.h"

static constexpr char GC_BLE_SERVICE_UUID[]="7b0d0001-6f2a-4c2d-9d8a-135e2c000001";
static constexpr char GC_BLE_CONTROL_UUID[]="7b0d0002-6f2a-4c2d-9d8a-135e2c000001";
static constexpr char GC_BLE_STATUS_UUID[]="7b0d0003-6f2a-4c2d-9d8a-135e2c000001";
static constexpr char GC_BLE_PROTOCOL[]="gc-ble-provision-v1";
static constexpr uint8_t GC_PAIR_BUTTON=9; // XIAO ESP32-C3 BOOT

struct BleNetworkConfig { String ssid,wifiPass,host,user,pass,ca,name; uint16_t port=8883; };

class BleProvisioner {
  class ControlCallbacks: public BLECharacteristicCallbacks { BleProvisioner* owner; public: explicit ControlCallbacks(BleProvisioner* o):owner(o){} void onWrite(BLECharacteristic* c) override { owner->queueCommand(c->getValue()); } };
  BLEServer* server=nullptr; BLECharacteristic* control=nullptr; BLECharacteristic* status=nullptr;
  DeviceIdentity* identity=nullptr; String deviceId, announcement, sessionNonce, chunks; uint8_t expectedChunks=0,nextChunk=0;
  bool active=false, keyReady=false, awaitingButton=false, physicallyConfirmed=false; volatile bool pending=false; uint32_t deadline=0, buttonDown=0;
  unsigned char sessionKey[32]{};
  portMUX_TYPE commandMux=portMUX_INITIALIZER_UNLOCKED;
  char commandBuffer[221]{}; volatile bool commandPending=false;

  void queueCommand(const std::string& value) {
    if(value.empty()||value.size()>220)return;
    portENTER_CRITICAL(&commandMux);
    if(!commandPending){memcpy(commandBuffer,value.data(),value.size());commandBuffer[value.size()]=0;commandPending=true;}
    portEXIT_CRITICAL(&commandMux);
  }
  bool takeCommand(String& out) {
    char local[221]{}; bool has=false;
    portENTER_CRITICAL(&commandMux);
    if(commandPending){strncpy(local,commandBuffer,sizeof(local)-1);commandPending=false;commandBuffer[0]=0;has=true;}
    portEXIT_CRITICAL(&commandMux);
    if(has)out=String(local); return has;
  }

  static bool decode64(const String& input, unsigned char* out, size_t outCap, size_t& used) {
    return mbedtls_base64_decode(out,outCap,&used,(const unsigned char*)input.c_str(),input.length())==0;
  }
  static String encode64(const unsigned char* data,size_t size) {
    size_t needed=0; mbedtls_base64_encode(nullptr,0,&needed,data,size); String out; out.reserve(needed+1);
    unsigned char* buf=(unsigned char*)malloc(needed+1); if(!buf)return ""; size_t used=0;
    if(mbedtls_base64_encode(buf,needed+1,&used,data,size)!=0){free(buf);return "";} buf[used]=0;out=String((char*)buf);free(buf);return out;
  }
  void send(const String& value){ if(!status)return; status->setValue(value.c_str());status->notify();delay(8); }
  void sendProof(const String& proof){ const size_t width=120; const uint16_t total=(proof.length()+width-1)/width; if(!total||total>64)return; for(uint16_t i=0;i<total;i++)send("P|"+String(i)+"|"+String(total)+"|"+proof.substring(i*width,min(proof.length(),(i+1)*width))); }
  void resetSession(){ memset(sessionKey,0,sizeof(sessionKey));sessionNonce="";chunks="";expectedChunks=nextChunk=0;keyReady=awaitingButton=physicallyConfirmed=false;deadline=0;buttonDown=0; }
  bool derive(const String& peerB64,String& ourB64) {
    unsigned char peerRaw[65];size_t peerLen=0;if(!decode64(peerB64,peerRaw,sizeof(peerRaw),peerLen)||peerLen!=65)return false;
    mbedtls_ecp_group grp;mbedtls_mpi d,z;mbedtls_ecp_point q,peer;mbedtls_ecp_group_init(&grp);mbedtls_mpi_init(&d);mbedtls_mpi_init(&z);mbedtls_ecp_point_init(&q);mbedtls_ecp_point_init(&peer);
    int rc=mbedtls_ecp_group_load(&grp,MBEDTLS_ECP_DP_SECP256R1);
    if(!rc)rc=mbedtls_ecp_gen_keypair(&grp,&d,&q,[](void*,unsigned char* out,size_t n){esp_fill_random(out,n);return 0;},nullptr);
    if(!rc)rc=mbedtls_ecp_point_read_binary(&grp,&peer,peerRaw,peerLen);
    if(!rc)rc=mbedtls_ecdh_compute_shared(&grp,&z,&peer,&d,[](void*,unsigned char* out,size_t n){esp_fill_random(out,n);return 0;},nullptr);
    unsigned char ours[65],secret[32],salt[32];size_t oursLen=0;
    if(!rc)rc=mbedtls_ecp_point_write_binary(&grp,&q,MBEDTLS_ECP_PF_UNCOMPRESSED,&oursLen,ours,sizeof(ours));
    if(!rc)rc=mbedtls_mpi_write_binary(&z,secret,sizeof(secret));
    if(!rc){
      for(size_t i=0;i<32;i++){char pair[3]={sessionNonce[i*2],sessionNonce[i*2+1],0};salt[i]=(unsigned char)strtoul(pair,nullptr,16);}
      const mbedtls_md_info_t* md=mbedtls_md_info_from_type(MBEDTLS_MD_SHA256); unsigned char prk[32], input[64];
      rc=mbedtls_md_hmac(md,salt,sizeof(salt),secret,sizeof(secret),prk);
      const size_t infoLen=strlen(GC_BLE_PROTOCOL); memcpy(input,GC_BLE_PROTOCOL,infoLen); input[infoLen]=1;
      if(!rc)rc=mbedtls_md_hmac(md,prk,sizeof(prk),input,infoLen+1,sessionKey);
      memset(prk,0,sizeof(prk));memset(input,0,sizeof(input));
    }
    if(!rc)ourB64=encode64(ours,oursLen);
    memset(secret,0,sizeof(secret));mbedtls_ecp_point_free(&peer);mbedtls_ecp_point_free(&q);mbedtls_mpi_free(&z);mbedtls_mpi_free(&d);mbedtls_ecp_group_free(&grp);return rc==0;
  }
  static String field(const String& src,int index){int start=0;for(int i=0;i<index;i++){start=src.indexOf('|',start);if(start<0)return "";start++;}int end=src.indexOf('|',start);return end<0?src.substring(start):src.substring(start,end);}
  static String decodeString(const String& b64){size_t cap=(b64.length()*3)/4+4;unsigned char* buf=(unsigned char*)malloc(cap+1);if(!buf)return "";size_t used=0;String out;if(decode64(b64,buf,cap,used)){buf[used]=0;out=String((char*)buf);}free(buf);return out;}
  bool decryptConfig(const String& encoded,BleNetworkConfig& cfg){
    size_t cap=(encoded.length()*3)/4+4;unsigned char* all=(unsigned char*)malloc(cap);if(!all)return false;size_t used=0;if(!decode64(encoded,all,cap,used)||used<29){free(all);return false;}
    const size_t cipherLen=used-12-16;unsigned char* plain=(unsigned char*)malloc(cipherLen+1);if(!plain){free(all);return false;}
    mbedtls_gcm_context gcm;mbedtls_gcm_init(&gcm);int rc=mbedtls_gcm_setkey(&gcm,MBEDTLS_CIPHER_ID_AES,sessionKey,256);
    if(!rc)rc=mbedtls_gcm_auth_decrypt(&gcm,cipherLen,all,12,(const unsigned char*)deviceId.c_str(),deviceId.length(),all+12+cipherLen,16,all+12,plain);
    mbedtls_gcm_free(&gcm);if(rc){memset(plain,0,cipherLen);free(plain);free(all);return false;}plain[cipherLen]=0;String text((char*)plain);memset(plain,0,cipherLen);free(plain);free(all);
    if(field(text,0)!="V1")return false;cfg.ssid=decodeString(field(text,1));cfg.wifiPass=decodeString(field(text,2));cfg.host=decodeString(field(text,3));cfg.port=(uint16_t)field(text,4).toInt();cfg.user=decodeString(field(text,5));cfg.pass=decodeString(field(text,6));cfg.ca=field(text,7);cfg.name=decodeString(field(text,8));
    return !cfg.ssid.isEmpty()&&!cfg.host.isEmpty()&&cfg.port==8883&&!cfg.user.isEmpty()&&!cfg.pass.isEmpty()&&!cfg.ca.isEmpty();
  }
  void handleHello(const String& value){resetSession();int p1=value.indexOf('|',2);if(p1<0)return;sessionNonce=value.substring(2,p1);String peer=value.substring(p1+1);if(sessionNonce.length()!=64)return;for(size_t i=0;i<sessionNonce.length();++i)if(!isxdigit((unsigned char)sessionNonce[i])){resetSession();return;}String ours;if(!derive(peer,ours)){resetSession();return;}keyReady=true;deadline=millis()+60000;String body="{\"nonce\":\""+sessionNonce+"\",\"protocol\":\""+String(GC_BLE_PROTOCOL)+"\",\"ephemeral\":\""+ours+"\",\"announcement\":"+announcement+"}";String proof=identity->sign(deviceId,"ble_proof",body,[](const String& s){String o;for(char c:s){if(c=='\\')o+="\\\\";else if(c=='\"')o+="\\\"";else if(c=='\n')o+="\\n";else if(c=='\r')o+="\\r";else if((uint8_t)c>=0x20)o+=c;}return o;});sendProof(proof);}
  void handle(const String& value){
    if(!active||value.length()>220)return;
    if(value.startsWith("H|")){handleHello(value);return;}
    if(value.startsWith("A|")&&keyReady&&value.substring(2)==sessionNonce){awaitingButton=true;physicallyConfirmed=false;deadline=millis()+60000;buttonDown=0;return;}
    if(!physicallyConfirmed||!keyReady||!value.startsWith("C|"))return;
    int p1=value.indexOf('|',2),p2=p1<0?-1:value.indexOf('|',p1+1);if(p1<0||p2<0)return;int idx=value.substring(2,p1).toInt(),total=value.substring(p1+1,p2).toInt();if(total<1||total>64||idx!=nextChunk||(expectedChunks&&total!=expectedChunks)){chunks="";expectedChunks=nextChunk=0;return;}if(!expectedChunks)expectedChunks=total;String part=value.substring(p2+1);if(chunks.length()+part.length()>4096){resetSession();return;}chunks+=part;nextChunk++;
    if(nextChunk==expectedChunks){BleNetworkConfig temp;if(decryptConfig(chunks,temp)){config=temp;pending=true;send("D|"+sessionNonce);}else send("E|decrypt");chunks="";expectedChunks=nextChunk=0;}
  }
  BleNetworkConfig config;
public:
  void begin(const String& id,const String& announce,DeviceIdentity& ident){deviceId=id;announcement=announce;identity=&ident;pinMode(GC_PAIR_BUTTON,INPUT_PULLUP);BLEDevice::init(deviceId.c_str());server=BLEDevice::createServer();BLEService* svc=server->createService(GC_BLE_SERVICE_UUID);control=svc->createCharacteristic(GC_BLE_CONTROL_UUID,BLECharacteristic::PROPERTY_WRITE);status=svc->createCharacteristic(GC_BLE_STATUS_UUID,BLECharacteristic::PROPERTY_READ|BLECharacteristic::PROPERTY_NOTIFY);control->setCallbacks(new ControlCallbacks(this));status->setValue("GC-BLE-READY");svc->start();BLEAdvertising* adv=BLEDevice::getAdvertising();adv->addServiceUUID(GC_BLE_SERVICE_UUID);adv->setScanResponse(true);BLEDevice::startAdvertising();active=true;}
  void loop(){if(!active)return;String command;if(takeCommand(command))handle(command);if(deadline&&(int32_t)(millis()-deadline)>=0){resetSession();send("E|timeout");}if(awaitingButton){if(digitalRead(GC_PAIR_BUTTON)==LOW){if(!buttonDown)buttonDown=millis();else if(millis()-buttonDown>=800){awaitingButton=false;physicallyConfirmed=true;deadline=millis()+60000;send("R|"+sessionNonce);}}else buttonDown=0;}}
  bool take(BleNetworkConfig& out){if(!pending)return false;out=config;pending=false;return true;}
  void stop(){if(!active)return;BLEDevice::stopAdvertising();BLEDevice::deinit(true);active=false;resetSession();}
};
