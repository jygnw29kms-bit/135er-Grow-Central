#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ESPmDNS.h>
#include <FS.h>
#include <SD_MMC.h>
#include <esp_camera.h>
#include <esp_http_server.h>
#include <time.h>
#include <MQTT.h>
#include "identity.h"
#include "ble_provisioning.h"

static constexpr char FW_VERSION[] = "0.1.0";
static constexpr char PROTOCOL[] = "gc-esp32-mqtt-v1";
static constexpr char SCHEMA[] = "gc-device-v1";
static constexpr char MQTT_ROOT[] = "growcentral/v1";
static constexpr char DEFAULT_NAME[] = "135er-GC-Cam";
static constexpr char HOSTNAME[] = "135er-gc-cam";
static constexpr uint32_t MQTT_RETRY_MS = 5000;
static constexpr uint32_t WIFI_RETRY_MS = 10000;
static constexpr uint32_t STATE_INTERVAL_MS = 30000;
static constexpr uint64_t MIN_SD_BYTES = 2ULL * 1024ULL * 1024ULL * 1024ULL;

// AI Thinker ESP32-CAM pin map.
static constexpr int PWDN_GPIO_NUM = 32;
static constexpr int RESET_GPIO_NUM = -1;
static constexpr int XCLK_GPIO_NUM = 0;
static constexpr int SIOD_GPIO_NUM = 26;
static constexpr int SIOC_GPIO_NUM = 27;
static constexpr int Y9_GPIO_NUM = 35;
static constexpr int Y8_GPIO_NUM = 34;
static constexpr int Y7_GPIO_NUM = 39;
static constexpr int Y6_GPIO_NUM = 36;
static constexpr int Y5_GPIO_NUM = 21;
static constexpr int Y4_GPIO_NUM = 19;
static constexpr int Y3_GPIO_NUM = 18;
static constexpr int Y2_GPIO_NUM = 5;
static constexpr int VSYNC_GPIO_NUM = 25;
static constexpr int HREF_GPIO_NUM = 23;
static constexpr int PCLK_GPIO_NUM = 22;

Preferences prefs;
WiFiClientSecure net;
MQTTClient mqtt(2048, 2048);
DeviceIdentity identity;
BleProvisioner bleProvisioner;
httpd_handle_t httpServer = nullptr;

String wifiSsid;
String wifiPass;
String mqttHost;
uint16_t mqttPort = 8883;
String mqttUser;
String mqttPass;
String mqttCa;
String deviceName = DEFAULT_NAME;
String deviceId;
String hardwareUid;
String cameraToken;

bool cameraReady = false;
bool sdReady = false;
bool provisioningMode = false;
uint64_t sdTotalBytes = 0;
uint64_t sdFreeBytes = 0;
uint32_t lastWifiAttempt = 0;
uint32_t lastMqttAttempt = 0;
uint32_t lastStatePublish = 0;
String proofQueue[4];
uint8_t proofHead = 0;
uint8_t proofCount = 0;

static String jsonEscape(const String& src) {
  String out;
  out.reserve(src.length() + 8);
  for (size_t i = 0; i < src.length(); ++i) {
    const char c = src[i];
    switch (c) {
      case '\\': out += "\\\\"; break;
      case '"': out += "\\\""; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default: if (static_cast<uint8_t>(c) >= 0x20) out += c; break;
    }
  }
  return out;
}

static String topic(const char* leaf) {
  return String(MQTT_ROOT) + "/devices/" + deviceId + "/" + leaf;
}

static String randomHex(size_t bytes) {
  String out;
  out.reserve(bytes * 2);
  for (size_t i = 0; i < bytes; ++i) {
    char part[3];
    snprintf(part, sizeof(part), "%02x", static_cast<unsigned>(esp_random() & 0xff));
    out += part;
  }
  return out;
}

static void deriveIdentityNames() {
  const uint64_t mac = ESP.getEfuseMac();
  char uid[17];
  snprintf(uid, sizeof(uid), "%016llx", static_cast<unsigned long long>(mac));
  hardwareUid = String(uid);
  char suffix[7];
  snprintf(suffix, sizeof(suffix), "%06lx", static_cast<unsigned long>(mac & 0xFFFFFFUL));
  deviceId = String("gc-cam-") + suffix;
  deviceId.toLowerCase();
}

static void loadNetworkConfig() {
  prefs.begin("gc-net", true);
  wifiSsid = prefs.getString("ssid", "");
  wifiPass = prefs.getString("wpass", "");
  mqttHost = prefs.getString("mhost", "");
  mqttPort = prefs.getUShort("mport", 8883);
  mqttUser = prefs.getString("muser", "");
  mqttPass = prefs.getString("mpass", "");
  mqttCa = prefs.getString("ca", "");
  deviceName = prefs.getString("name", DEFAULT_NAME);
  prefs.end();
  deviceName.trim();
  if (deviceName.isEmpty()) deviceName = DEFAULT_NAME;
}

static void saveNetworkConfig(const BleNetworkConfig& cfg) {
  prefs.begin("gc-net", false);
  prefs.putString("ssid", cfg.ssid);
  prefs.putString("wpass", cfg.wifiPass);
  prefs.putString("mhost", cfg.host);
  prefs.putUShort("mport", cfg.port);
  prefs.putString("muser", cfg.user);
  prefs.putString("mpass", cfg.pass);
  prefs.putString("ca", cfg.ca);
  prefs.putString("name", cfg.name.isEmpty() ? String(DEFAULT_NAME) : cfg.name);
  prefs.end();
}

static void clearNetworkConfig() {
  prefs.begin("gc-net", false);
  prefs.clear();
  prefs.end();
}

static void loadOrCreateCameraToken() {
  prefs.begin("gc-cam", false);
  cameraToken = prefs.getString("token", "");
  if (cameraToken.length() != 32) {
    cameraToken = randomHex(16);
    prefs.putString("token", cameraToken);
  }
  prefs.end();
}

static bool networkConfigReady() {
  return !wifiSsid.isEmpty() && !mqttHost.isEmpty() && mqttPort == 8883 &&
         !mqttUser.isEmpty() && !mqttPass.isEmpty() && !mqttCa.isEmpty();
}

static String announcementPayload() {
  return "{\"schema\":\"" + String(SCHEMA) + "\",\"protocol\":\"" + String(PROTOCOL) +
         "\",\"id\":\"" + jsonEscape(deviceId) + "\",\"name\":\"" + jsonEscape(deviceName) +
         "\",\"device_class\":\"camera\",\"model\":\"GC-CAM-AI-THINKER-ESP32\",\"firmware\":\"" +
         String(FW_VERSION) + "\",\"hardware_uid\":\"" + hardwareUid +
         "\",\"capabilities\":[\"snapshot\",\"stream\"]}";
}

static String cameraBaseUrl() {
  if (WiFi.status() != WL_CONNECTED) return "";
  return "http://" + WiFi.localIP().toString();
}

static String statePayload() {
  const String base = cameraBaseUrl();
  const String snap = base.isEmpty() ? "" : base + "/snapshot.jpg?token=" + cameraToken;
  const String stream = base.isEmpty() ? "" : base + "/stream.mjpeg?token=" + cameraToken;
  String payload;
  payload.reserve(640);
  payload += "{\"snapshot\":\"" + jsonEscape(snap) + "\",\"stream\":\"" + jsonEscape(stream) + "\",\"meta\":{";
  payload += "\"hostname\":\"" + String(HOSTNAME) + "\"";
  payload += ",\"ip\":\"" + (WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String()) + "\"";
  payload += ",\"camera_ready\":" + String(cameraReady ? "true" : "false");
  payload += ",\"sd_ready\":" + String(sdReady ? "true" : "false");
  payload += ",\"sd_total_mb\":" + String(static_cast<unsigned long>(sdTotalBytes / 1048576ULL));
  payload += ",\"sd_free_mb\":" + String(static_cast<unsigned long>(sdFreeBytes / 1048576ULL));
  payload += ",\"resolution\":\"800x600\"";
  payload += ",\"rssi_dbm\":" + String(WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0);
  payload += ",\"uptime_ms\":" + String(millis());
  payload += ",\"firmware\":\"" + String(FW_VERSION) + "\"}}";
  return payload;
}

static void publishAnnouncement() {
  if (!mqtt.connected()) return;
  const String signedPayload = identity.sign(deviceId, "announce", announcementPayload(), jsonEscape);
  if (!signedPayload.isEmpty()) mqtt.publish(topic("announce"), signedPayload, true, 1);
}

static void publishState(bool force = false) {
  if (!mqtt.connected()) return;
  const uint32_t now = millis();
  if (!force && now - lastStatePublish < STATE_INTERVAL_MS) return;
  const String signedPayload = identity.sign(deviceId, "state", statePayload(), jsonEscape);
  if (!signedPayload.isEmpty() && mqtt.publish(topic("state"), signedPayload, true, 1)) lastStatePublish = now;
}

static void onMqttMessage(String& incomingTopic, String& payload) {
  if (incomingTopic != topic("challenge") || payload.length() > 256) return;
  const int field = payload.indexOf("\"nonce\"");
  if (field < 0) return;
  const int colon = payload.indexOf(':', field + 7);
  const int start = payload.indexOf('"', colon + 1);
  const int end = payload.indexOf('"', start + 1);
  if (colon < 0 || start < 0 || end - start != 65) return;
  const String nonce = payload.substring(start + 1, end);
  for (size_t i = 0; i < nonce.length(); ++i) if (!isxdigit(static_cast<unsigned char>(nonce[i]))) return;
  if (proofCount < 4) {
    proofQueue[(proofHead + proofCount) % 4] = nonce;
    ++proofCount;
  }
}

static void handleIdentityProof() {
  if (!proofCount || !mqtt.connected()) return;
  const String nonce = proofQueue[proofHead];
  proofQueue[proofHead] = "";
  proofHead = (proofHead + 1) % 4;
  --proofCount;
  const String body = "{\"nonce\":\"" + nonce + "\",\"hardware_uid\":\"" + hardwareUid + "\",\"state\":" + statePayload() + "}";
  const String proof = identity.sign(deviceId, "proof", body, jsonEscape);
  if (!proof.isEmpty()) mqtt.publish(topic("proof"), proof, false, 1);
}

static bool initCamera() {
  camera_config_t config{};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_SVGA;
  config.jpeg_quality = psramFound() ? 11 : 14;
  config.fb_count = psramFound() ? 2 : 1;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  const esp_err_t rc = esp_camera_init(&config);
  if (rc != ESP_OK) {
    Serial.printf("GC_CAM camera_init_failed=0x%x\n", rc);
    return false;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor) {
    sensor->set_framesize(sensor, FRAMESIZE_SVGA);
    sensor->set_quality(sensor, psramFound() ? 11 : 14);
  }
  return true;
}

static void updateSdStats() {
  if (!sdReady) return;
  sdTotalBytes = SD_MMC.totalBytes();
  const uint64_t used = SD_MMC.usedBytes();
  sdFreeBytes = sdTotalBytes > used ? sdTotalBytes - used : 0;
}

static bool initStorage() {
  if (!SD_MMC.begin("/sdcard", true, false)) {
    Serial.println("GC_SD mount_failed");
    return false;
  }
  sdTotalBytes = SD_MMC.totalBytes();
  if (sdTotalBytes < MIN_SD_BYTES) {
    Serial.printf("GC_SD partition_too_small bytes=%llu expected_at_least=%llu; reformat card as one FAT32 volume\n",
                  static_cast<unsigned long long>(sdTotalBytes), static_cast<unsigned long long>(MIN_SD_BYTES));
    SD_MMC.end();
    sdTotalBytes = sdFreeBytes = 0;
    return false;
  }
  SD_MMC.mkdir("/gc");
  SD_MMC.mkdir("/gc/snapshots");
  SD_MMC.mkdir("/gc/timelapse");
  SD_MMC.mkdir("/gc/logs");
  SD_MMC.mkdir("/gc/recovery");
  updateSdStats();
  File info = SD_MMC.open("/gc/device.json", FILE_WRITE);
  if (info) {
    info.printf("{\"name\":\"%s\",\"hostname\":\"%s\",\"device_id\":\"%s\",\"firmware\":\"%s\",\"schema\":\"gc-camera-storage-v1\"}\n",
                deviceName.c_str(), HOSTNAME, deviceId.c_str(), FW_VERSION);
    info.close();
  }
  Serial.printf("GC_SD ready total_mb=%llu free_mb=%llu\n",
                static_cast<unsigned long long>(sdTotalBytes / 1048576ULL),
                static_cast<unsigned long long>(sdFreeBytes / 1048576ULL));
  return true;
}

static bool secureEqual(const char* left, const String& right) {
  if (!left || strlen(left) != right.length()) return false;
  uint8_t diff = 0;
  for (size_t i = 0; i < right.length(); ++i) diff |= static_cast<uint8_t>(left[i] ^ right[i]);
  return diff == 0;
}

static bool requestAuthorized(httpd_req_t* req) {
  char query[128];
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK) return false;
  char token[48];
  if (httpd_query_key_value(query, "token", token, sizeof(token)) != ESP_OK) return false;
  return secureEqual(token, cameraToken);
}

static esp_err_t unauthorized(httpd_req_t* req) {
  httpd_resp_set_status(req, "401 Unauthorized");
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_sendstr(req, "{\"detail\":\"camera token required\"}");
}

static esp_err_t serviceUnavailable(httpd_req_t* req, const char* detail) {
  httpd_resp_set_status(req, "503 Service Unavailable");
  httpd_resp_set_type(req, "text/plain");
  return httpd_resp_sendstr(req, detail);
}

static esp_err_t healthHandler(httpd_req_t* req) {
  String body = "{\"ok\":true,\"service\":\"135er-GC-Cam\",\"device_id\":\"" + deviceId +
                "\",\"hostname\":\"" + String(HOSTNAME) + "\",\"firmware\":\"" + String(FW_VERSION) +
                "\",\"camera_ready\":" + String(cameraReady ? "true" : "false") +
                ",\"sd_ready\":" + String(sdReady ? "true" : "false") + "}";
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  return httpd_resp_send(req, body.c_str(), body.length());
}

static esp_err_t snapshotHandler(httpd_req_t* req) {
  if (!requestAuthorized(req)) return unauthorized(req);
  if (!cameraReady) return serviceUnavailable(req, "camera unavailable");
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) return serviceUnavailable(req, "capture failed");
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  const esp_err_t rc = httpd_resp_send(req, reinterpret_cast<const char*>(fb->buf), fb->len);
  esp_camera_fb_return(fb);
  return rc;
}

static String captureFilename() {
  const time_t now = time(nullptr);
  if (now > 1700000000) {
    struct tm utc{};
    gmtime_r(&now, &utc);
    char name[64];
    strftime(name, sizeof(name), "/gc/snapshots/%Y%m%dT%H%M%SZ.jpg", &utc);
    return String(name);
  }
  return "/gc/snapshots/uptime-" + String(millis()) + ".jpg";
}

static esp_err_t captureHandler(httpd_req_t* req) {
  if (!requestAuthorized(req)) return unauthorized(req);
  if (!cameraReady || !sdReady) return serviceUnavailable(req, "camera or SD unavailable");
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) return serviceUnavailable(req, "capture failed");
  const String path = captureFilename();
  File file = SD_MMC.open(path, FILE_WRITE);
  bool ok = false;
  if (file) {
    ok = file.write(fb->buf, fb->len) == fb->len;
    file.close();
  }
  esp_camera_fb_return(fb);
  updateSdStats();
  if (!ok) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "SD write failed");
  String body = "{\"ok\":true,\"path\":\"" + path + "\"}";
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_send(req, body.c_str(), body.length());
}

static esp_err_t streamHandler(httpd_req_t* req) {
  if (!requestAuthorized(req)) return unauthorized(req);
  if (!cameraReady) return serviceUnavailable(req, "camera unavailable");
  static const char* contentType = "multipart/x-mixed-replace;boundary=gcframe";
  static const char* boundary = "\r\n--gcframe\r\n";
  httpd_resp_set_type(req, contentType);
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  while (true) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) break;
    char header[96];
    const int hlen = snprintf(header, sizeof(header), "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", static_cast<unsigned>(fb->len));
    esp_err_t rc = httpd_resp_send_chunk(req, boundary, strlen(boundary));
    if (rc == ESP_OK) rc = httpd_resp_send_chunk(req, header, hlen);
    if (rc == ESP_OK) rc = httpd_resp_send_chunk(req, reinterpret_cast<const char*>(fb->buf), fb->len);
    esp_camera_fb_return(fb);
    if (rc != ESP_OK) break;
    delay(80);
  }
  httpd_resp_send_chunk(req, nullptr, 0);
  return ESP_OK;
}

static bool startHttpServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 8;
  config.stack_size = 8192;
  if (httpd_start(&httpServer, &config) != ESP_OK) return false;
  const httpd_uri_t health{.uri="/health", .method=HTTP_GET, .handler=healthHandler, .user_ctx=nullptr};
  const httpd_uri_t snapshot{.uri="/snapshot.jpg", .method=HTTP_GET, .handler=snapshotHandler, .user_ctx=nullptr};
  const httpd_uri_t capture{.uri="/capture", .method=HTTP_POST, .handler=captureHandler, .user_ctx=nullptr};
  const httpd_uri_t stream{.uri="/stream.mjpeg", .method=HTTP_GET, .handler=streamHandler, .user_ctx=nullptr};
  return httpd_register_uri_handler(httpServer, &health) == ESP_OK &&
         httpd_register_uri_handler(httpServer, &snapshot) == ESP_OK &&
         httpd_register_uri_handler(httpServer, &capture) == ESP_OK &&
         httpd_register_uri_handler(httpServer, &stream) == ESP_OK;
}

static void startMdns() {
  if (!MDNS.begin(HOSTNAME)) {
    Serial.println("GC_NET mdns_failed");
    return;
  }
  MDNS.addService("http", "tcp", 80);
  MDNS.addServiceTxt("http", "tcp", "service", "grow-central-camera");
  MDNS.addServiceTxt("http", "tcp", "name", DEFAULT_NAME);
  MDNS.addServiceTxt("http", "tcp", "device_id", deviceId.c_str());
  MDNS.addServiceTxt("http", "tcp", "protocol", PROTOCOL);
  Serial.printf("GC_NET mdns=%s.local\n", HOSTNAME);
}

static void startWifiIfConfigured() {
  if (wifiSsid.isEmpty()) return;
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setHostname(HOSTNAME);
  WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
  lastWifiAttempt = millis();
}

static void maintainWifi() {
  if (wifiSsid.isEmpty() || WiFi.status() == WL_CONNECTED) return;
  const uint32_t now = millis();
  if (now - lastWifiAttempt < WIFI_RETRY_MS) return;
  WiFi.disconnect();
  WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
  lastWifiAttempt = now;
}

static void connectMqttIfReady() {
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED || mqttHost.isEmpty() || mqttCa.isEmpty()) return;
  const uint32_t now = millis();
  if (now - lastMqttAttempt < MQTT_RETRY_MS) return;
  lastMqttAttempt = now;
  if (time(nullptr) < 1700000000) return;
  net.setCACert(mqttCa.c_str());
  net.setHandshakeTimeout(10);
  mqtt.begin(mqttHost.c_str(), mqttPort, net);
  if (!mqtt.connect(deviceId.c_str(), mqttUser.c_str(), mqttPass.c_str())) {
    Serial.printf("GC_NET mqtt_failed error=%d return=%d\n", int(mqtt.lastError()), int(mqtt.returnCode()));
    return;
  }
  mqtt.subscribe(topic("challenge"), 1);
  mqtt.publish(topic("availability"), "online", true, 1);
  publishAnnouncement();
  publishState(true);
  Serial.printf("GC_NET mqtt_online broker=%s:%u device=%s\n", mqttHost.c_str(), mqttPort, deviceId.c_str());
}

static void finishNetworkStartupOnce() {
  static bool done = false;
  if (done || WiFi.status() != WL_CONNECTED) return;
  done = true;
  configTime(0, 0, "pool.ntp.org", "time.cloudflare.com", "time.google.com");
  startMdns();
  cameraReady = initCamera();
  sdReady = initStorage();
  const bool webReady = startHttpServer();
  Serial.printf("GC_CAM ready camera=%s web=%s sd=%s ip=%s name=%s\n",
                cameraReady ? "yes" : "no", webReady ? "yes" : "no", sdReady ? "yes" : "no",
                WiFi.localIP().toString().c_str(), deviceName.c_str());
}

static void handleSerial() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  String upper = cmd;
  upper.toUpperCase();
  if (upper == "INFO") {
    Serial.printf("GC_CAM id=%s name=%s host=%s.local fw=%s uid=%s fingerprint_tail=%s ip=%s sd=%s\n",
                  deviceId.c_str(), deviceName.c_str(), HOSTNAME, FW_VERSION, hardwareUid.c_str(),
                  identity.getFingerprint().substring(max(0, int(identity.getFingerprint().length()) - 16)).c_str(),
                  WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "-", sdReady ? "ready" : "not-ready");
  } else if (upper == "NET CLEAR") {
    clearNetworkConfig();
    Serial.println("OK network configuration cleared; rebooting into secure BLE provisioning");
    delay(250);
    ESP.restart();
  } else if (upper == "REBOOT") {
    ESP.restart();
  } else if (upper.startsWith("USB ID ")) {
    const String nonce = cmd.substring(7);
    if (nonce.length() != 64) { Serial.println("ERR invalid identity challenge"); return; }
    for (size_t i = 0; i < nonce.length(); ++i) if (!isxdigit(static_cast<unsigned char>(nonce[i]))) { Serial.println("ERR invalid identity challenge"); return; }
    const String body = "{\"nonce\":\"" + nonce + "\",\"announcement\":" + announcementPayload() + "}";
    const String proof = identity.sign(deviceId, "proof", body, jsonEscape);
    if (proof.isEmpty()) Serial.println("ERR device identity unavailable"); else Serial.println("GC_USB_ID " + proof);
  } else {
    Serial.println("GC_CAM commands: INFO | USB ID <64hex> | NET CLEAR | REBOOT");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(250);
  delay(250);
  deriveIdentityNames();
  if (!identity.begin()) {
    Serial.println("GC_CAM fatal identity_init_failed");
    return;
  }
  loadOrCreateCameraToken();
  loadNetworkConfig();
  mqtt.setOptions(30, true, 1500);
  mqtt.onMessage(onMqttMessage);
  if (!networkConfigReady()) {
    provisioningMode = true;
    bleProvisioner.begin(deviceId, announcementPayload(), identity);
    Serial.printf("GC_BLE provisioning active device=%s name=%s; hold GPIO0 only when Grow-Central prompts\n", deviceId.c_str(), deviceName.c_str());
    Serial.printf("GC_ID fingerprint_tail=%s\n", identity.getFingerprint().substring(max(0, int(identity.getFingerprint().length()) - 16)).c_str());
    return;
  }
  startWifiIfConfigured();
}

void loop() {
  handleSerial();
  if (provisioningMode) {
    bleProvisioner.loop();
    BleNetworkConfig config;
    if (bleProvisioner.take(config)) {
      saveNetworkConfig(config);
      Serial.println("GC_BLE configuration saved; rebooting before camera starts");
      delay(400);
      ESP.restart();
    }
    delay(5);
    return;
  }
  maintainWifi();
  finishNetworkStartupOnce();
  connectMqttIfReady();
  if (mqtt.connected()) mqtt.loop();
  handleIdentityProof();
  publishState();
  delay(5);
}
