#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include <freertos/semphr.h>
#include <MQTT.h>
#include <math.h>
#include "identity.h"
#include "ble_provisioning.h"
#include <bootloader_random.h>

static constexpr char FW_VERSION[] = "0.5.3";
static constexpr char PROTOCOL[] = "gc-esp32-mqtt-v1";
static constexpr char SCHEMA[] = "gc-device-v1";
static constexpr char MQTT_ROOT[] = "growcentral/v1";
static constexpr uint8_t SOIL_PIN = A0;          // XIAO ESP32-C3 D0 / GPIO2
static constexpr uint16_t ADC_MAX = 4095;
static constexpr uint16_t DEFAULT_AIR_RAW = 3767;
static constexpr uint16_t DEFAULT_WATER_RAW = 1310;
static constexpr uint16_t DEFAULT_SUBSTRATE_RAW = 2500;
static constexpr uint8_t SAMPLE_COUNT = 64;
static constexpr uint16_t SAMPLE_DELAY_MS = 2;
static constexpr uint32_t REPORT_INTERVAL_MS = 1000;
static constexpr uint32_t MQTT_PUBLISH_INTERVAL_MS = 10000;
static constexpr uint32_t WIFI_RETRY_MS = 10000;
static constexpr uint32_t MQTT_RETRY_MS = 5000;
static constexpr float EMA_ALPHA = 0.20f;
static constexpr float PUBLISH_DELTA_PCT = 0.5f;

Preferences prefs;
WiFiClientSecure net;
MQTTClient mqtt(2048, 2048);
DeviceIdentity identity;
BleProvisioner bleProvisioner;

uint16_t airRaw = DEFAULT_AIR_RAW;
uint16_t waterRaw = DEFAULT_WATER_RAW;
uint16_t substrateRaw = DEFAULT_SUBSTRATE_RAW;
bool airCalibrated = false;
bool waterCalibrated = false;
bool substrateCalibrated = false;
String hardwareUid;
float emaRaw = NAN;
float lastPublishedPct = NAN;
uint32_t lastReport = 0;
uint32_t lastMqttPublish = 0;
uint32_t lastWifiAttempt = 0;
uint32_t lastMqttAttempt = 0;
uint32_t wifiRetry = WIFI_RETRY_MS, mqttRetry = MQTT_RETRY_MS;
volatile bool mqttOnline = false;

String wifiSsid;
String wifiPass;
String mqttHost;
uint16_t mqttPort = 8883;
String mqttUser;
String mqttPass;
String mqttCa;
String deviceName = "Grow-Central Soil Sensor";
String deviceId;
bool bleProvisionPending = false;

struct SoilReading {
  uint16_t rawMean;
  uint16_t rawMedian;
  uint16_t rawMin;
  uint16_t rawMax;
  float sigma;
  float filteredRaw;
  float moisturePct;
  bool sensorOk;
  const char* quality;
  const char* state;
};

SemaphoreHandle_t adcLock = nullptr;
portMUX_TYPE readingLock = portMUX_INITIALIZER_UNLOCKED;
SoilReading latestReading{};
bool readingAvailable = false;

static bool currentReading(SoilReading& out) {
  portENTER_CRITICAL(&readingLock);
  const bool available = readingAvailable;
  if (available) out = latestReading;
  portEXIT_CRITICAL(&readingLock);
  return available;
}

static int compareU16(const void* a, const void* b) {
  const uint16_t ua = *reinterpret_cast<const uint16_t*>(a);
  const uint16_t ub = *reinterpret_cast<const uint16_t*>(b);
  return (ua > ub) - (ua < ub);
}

static float clampf(float value, float lo, float hi) {
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

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

static float rawToPercent(float raw) {
  const float span = float(airRaw) - float(waterRaw);
  if (fabsf(span) < 50.0f) return NAN;
  return clampf((float(airRaw) - raw) * 100.0f / span, 0.0f, 100.0f);
}

static const char* moistureState(float pct) {
  if (isnan(pct)) return "UNCALIBRATED";
  if (pct < 10.0f) return "AIR_DRY";
  if (pct < 30.0f) return "DRY";
  if (pct < 55.0f) return "MOIST";
  if (pct < 80.0f) return "WET";
  return "SATURATED";
}

static const char* signalQuality(float sigma, uint16_t span) {
  if (span > 250 || sigma > 60.0f) return "POOR";
  if (span > 100 || sigma > 30.0f) return "FAIR";
  if (span > 45 || sigma > 15.0f) return "GOOD";
  return "EXCELLENT";
}

static SoilReading sampleSoil() {
  xSemaphoreTake(adcLock, portMAX_DELAY);
  uint16_t samples[SAMPLE_COUNT];
  uint16_t minVal = ADC_MAX;
  uint16_t maxVal = 0;

  for (uint8_t i = 0; i < SAMPLE_COUNT; ++i) {
    const uint16_t v = analogRead(SOIL_PIN);
    samples[i] = v;
    if (v < minVal) minVal = v;
    if (v > maxVal) maxVal = v;
    delay(SAMPLE_DELAY_MS);
  }

  qsort(samples, SAMPLE_COUNT, sizeof(uint16_t), compareU16);
  const uint16_t median = (samples[(SAMPLE_COUNT / 2) - 1] + samples[SAMPLE_COUNT / 2]) / 2;
  const uint8_t trim = SAMPLE_COUNT / 8;
  uint32_t trimmedSum = 0;
  uint8_t trimmedN = 0;
  for (uint8_t i = trim; i < SAMPLE_COUNT - trim; ++i) {
    trimmedSum += samples[i];
    ++trimmedN;
  }
  const float mean = float(trimmedSum) / float(trimmedN);

  float variance = 0.0f;
  for (uint8_t i = trim; i < SAMPLE_COUNT - trim; ++i) {
    const float d = float(samples[i]) - mean;
    variance += d * d;
  }
  variance /= float(trimmedN);
  const float sigma = sqrtf(variance);

  if (isnan(emaRaw)) emaRaw = mean;
  else emaRaw += EMA_ALPHA * (mean - emaRaw);

  const uint16_t span = maxVal - minVal;
  const bool plausible = mean > 80.0f && mean < 4050.0f;
  const bool stable = span < 500 && sigma < 120.0f;
  const bool ok = plausible && stable;
  const float pct = ok ? rawToPercent(emaRaw) : NAN;

  SoilReading r{};
  r.rawMean = uint16_t(lroundf(mean));
  r.rawMedian = median;
  r.rawMin = minVal;
  r.rawMax = maxVal;
  r.sigma = sigma;
  r.filteredRaw = emaRaw;
  r.moisturePct = pct;
  r.sensorOk = ok;
  r.quality = signalQuality(sigma, span);
  r.state = ok ? moistureState(pct) : "SENSOR_FAULT";
  xSemaphoreGive(adcLock);
  return r;
}

static uint16_t calibrationSnapshot() {
  uint32_t sum = 0;
  constexpr uint8_t windows = 8;
  for (uint8_t i = 0; i < windows; ++i) {
    SoilReading r = sampleSoil();
    sum += r.rawMedian;
    delay(80);
  }
  return uint16_t(sum / windows);
}

static void saveCalibration() {
  prefs.begin("gc-soil", false);
  prefs.putUShort("air", airRaw);
  prefs.putUShort("water", waterRaw);
  prefs.putUShort("substrate", substrateRaw);
  prefs.putBool("air_ok", airCalibrated);
  prefs.putBool("water_ok", waterCalibrated);
  prefs.putBool("substrate_ok", substrateCalibrated);
  prefs.end();
}

static void loadCalibration() {
  prefs.begin("gc-soil", true);
  airRaw = prefs.getUShort("air", DEFAULT_AIR_RAW);
  waterRaw = prefs.getUShort("water", DEFAULT_WATER_RAW);
  substrateRaw = prefs.getUShort("substrate", DEFAULT_SUBSTRATE_RAW);
  airCalibrated = prefs.getBool("air_ok", false);
  waterCalibrated = prefs.getBool("water_ok", false);
  substrateCalibrated = prefs.getBool("substrate_ok", false);
  prefs.end();
  if (airRaw <= waterRaw + 100 || airRaw > ADC_MAX || waterRaw < 50) {
    airRaw = DEFAULT_AIR_RAW;
    waterRaw = DEFAULT_WATER_RAW;
    airCalibrated = false;
    waterCalibrated = false;
    substrateCalibrated = false;
  }
  if (substrateCalibrated && !(substrateRaw > waterRaw + 50 && substrateRaw + 50 < airRaw)) {
    substrateRaw = DEFAULT_SUBSTRATE_RAW;
    substrateCalibrated = false;
  }
}

static void loadNetworkConfig() {
  prefs.begin("gc-net", true);
  wifiSsid = prefs.getString("ssid", "");
  wifiPass = prefs.getString("wpass", "");
  mqttHost = prefs.getString("mhost", "");
  mqttPort = prefs.getUShort("mport", 8883);
  mqttCa = prefs.getString("ca", "");
  mqttUser = prefs.getString("muser", "");
  mqttPass = prefs.getString("mpass", "");
  deviceName = prefs.getString("name", "Grow-Central Soil Sensor");
  bleProvisionPending = prefs.getBool("blepend", false);
  prefs.end();
}

static String caDerBase64ToPem(const String& encoded) {
  String pem = "-----BEGIN CERTIFICATE-----\n";
  for (size_t i = 0; i < encoded.length(); i += 64) pem += encoded.substring(i, i + 64) + "\n";
  pem += "-----END CERTIFICATE-----\n";
  return pem;
}

static void saveNetworkConfig() {
  prefs.begin("gc-net", false);
  prefs.putString("ssid", wifiSsid);
  prefs.putString("wpass", wifiPass);
  prefs.putString("mhost", mqttHost);
  prefs.putUShort("mport", mqttPort);
  prefs.putString("muser", mqttUser);
  prefs.putString("mpass", mqttPass);
  prefs.putString("ca", mqttCa);
  prefs.putString("name", deviceName);
  prefs.end();
}

static void saveBleProvisionPending(bool value) {
  prefs.begin("gc-net", false); prefs.putBool("blepend", value); prefs.end(); bleProvisionPending = value;
}

static void clearNetworkConfig() {
  prefs.begin("gc-net", false);
  prefs.clear();
  prefs.end();
  wifiSsid = "";
  wifiPass = "";
  mqttHost = "";
  mqttPort = 8883;
  mqttUser = "";
  mqttPass = "";
  mqttCa = "";
  deviceName = "Grow-Central Soil Sensor";
  bleProvisionPending = false;
  mqtt.disconnect();
  WiFi.disconnect(true, true);
}

static String topic(const char* leaf) {
  return String(MQTT_ROOT) + "/devices/" + deviceId + "/" + leaf;
}

static bool calibrationReady() { return airCalibrated && waterCalibrated && substrateCalibrated && airRaw > substrateRaw + 50 && substrateRaw > waterRaw + 50; }

static String calibrationJson() {
  return String("{\"ready\":") + (calibrationReady() ? "true" : "false") +
    ",\"air_done\":" + (airCalibrated ? "true" : "false") +
    ",\"wet_done\":" + (waterCalibrated ? "true" : "false") +
    ",\"substrate_done\":" + (substrateCalibrated ? "true" : "false") +
    ",\"air_raw\":" + String(airRaw) + ",\"wet_raw\":" + String(waterRaw) +
    ",\"substrate_raw\":" + String(substrateRaw) + ",\"substrate_reference\":\"fresh_potting_soil\"}";
}

static String announcementPayload() {
  String payload = "{\"schema\":\"" + String(SCHEMA) + "\",\"protocol\":\"" + String(PROTOCOL) +
                   "\",\"id\":\"" + jsonEscape(deviceId) + "\",\"name\":\"" + jsonEscape(deviceName) +
                   "\",\"device_class\":\"sensor\",\"model\":\"GC-SOIL-XIAO-C3-HW390\",\"firmware\":\"" +
                   String(FW_VERSION) + "\",\"hardware_uid\":\"" + hardwareUid + "\",\"driver_id\":\"gc.hw390.analog\",\"driver_verification\":\"gc_hardware_validated\",\"sensor_health_model\":\"gc-sensor-health-v1\",\"calibration\":" + calibrationJson() + ",\"capabilities\":[\"soil_moisture\"]}";
  return payload;
}

static void publishAnnouncement() {
  if (!mqtt.connected()) return;
  const String signedPayload = identity.sign(deviceId, "announce", announcementPayload(), jsonEscape);
  if (!signedPayload.isEmpty()) mqtt.publish(topic("announce"), signedPayload, true, 1);
}

static String statePayload(const SoilReading& r) {
  const int32_t rssi = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
  String payload;
  payload.reserve(520);
  payload += "{\"soil_moisture\":";
  payload += r.sensorOk && !isnan(r.moisturePct) ? String(r.moisturePct, 1) : "null";
  payload += ",\"meta\":{";
  payload += "\"raw\":" + String(r.rawMean);
  payload += ",\"median\":" + String(r.rawMedian);
  payload += ",\"filtered_raw\":" + String(r.filteredRaw, 1);
  payload += ",\"min\":" + String(r.rawMin);
  payload += ",\"max\":" + String(r.rawMax);
  payload += ",\"sigma\":" + String(r.sigma, 1);
  payload += ",\"quality\":\"" + String(r.quality) + "\"";
  payload += ",\"moisture_state\":\"" + String(r.state) + "\"";
  payload += ",\"sensor_ok\":" + String(r.sensorOk ? "true" : "false");
  payload += ",\"air_raw\":" + String(airRaw);
  payload += ",\"water_raw\":" + String(waterRaw);
  payload += ",\"substrate_raw\":" + String(substrateRaw);
  payload += ",\"rssi_dbm\":" + String(rssi);
  payload += ",\"uptime_ms\":" + String(millis());
  payload += ",\"firmware\":\"" + String(FW_VERSION) + "\"}}";

  return payload;
}

static void publishState(const SoilReading& r, bool force = false) {
  if (!mqtt.connected()) return;
  const uint32_t now = millis();
  const bool due = now - lastMqttPublish >= MQTT_PUBLISH_INTERVAL_MS;
  const bool changed = isnan(lastPublishedPct) || fabsf(r.moisturePct - lastPublishedPct) >= PUBLISH_DELTA_PCT;
  if (!force && !due && !changed) return;

  const String payload = statePayload(r);
  const String signedPayload = identity.sign(deviceId, "state", payload, jsonEscape);
  if (!signedPayload.isEmpty() && mqtt.publish(topic("state"), signedPayload, true, 1)) {
    lastPublishedPct = r.moisturePct;
    lastMqttPublish = now;
  }
}

String proofQueue[4];
uint8_t proofHead = 0, proofCount = 0;

static void onMqttMessage(String& incomingTopic, String& payload) {
  if (incomingTopic != topic("challenge") || payload.length() > 256) return;
  // Challenge has one fixed-size hexadecimal nonce; no network configuration or actuator commands.
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
  SoilReading reading{};
  if (!currentReading(reading)) return;
  const String nonce = proofQueue[proofHead];
  proofQueue[proofHead] = "";
  proofHead = (proofHead + 1) % 4;
  --proofCount;
  const String state = statePayload(reading);
  const String body = "{\"nonce\":\"" + nonce + "\",\"hardware_uid\":\"" + hardwareUid + "\",\"calibration\":" + calibrationJson() + ",\"state\":" + state + "}";
  const String proof = identity.sign(deviceId, "proof", body, jsonEscape);
  if (!proof.isEmpty()) mqtt.publish(topic("proof"), proof, false, 1);
}

static void deriveDeviceId() {
  const uint64_t mac = ESP.getEfuseMac();
  char uid[17];
  snprintf(uid, sizeof(uid), "%016llx", static_cast<unsigned long long>(mac));
  hardwareUid = String(uid);
  char suffix[7];
  snprintf(suffix, sizeof(suffix), "%06lx", static_cast<unsigned long>(mac & 0xFFFFFFUL));
  deviceId = String("gc-soil-") + suffix;
  deviceId.toLowerCase();
}

static void startWifiIfConfigured() {
  if (wifiSsid.isEmpty() || WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
  lastWifiAttempt = millis();
  Serial.printf("GC_NET wifi_connect ssid=%s\n", wifiSsid.c_str());
}

static void maintainWifi() {
  if (wifiSsid.isEmpty()) return;
  if (WiFi.status() == WL_CONNECTED) { wifiRetry = WIFI_RETRY_MS; return; }
  const uint32_t now = millis();
  if (now - lastWifiAttempt >= wifiRetry) {
    startWifiIfConfigured();
    wifiRetry = min(wifiRetry * 2, uint32_t(60000));
  }
}

static void configureMqttClient() {
  if (mqttHost.isEmpty()) return;
  net.setCACert(mqttCa.c_str());
  net.setHandshakeTimeout(10);
  net.setTimeout(10);
  mqtt.begin(mqttHost.c_str(), mqttPort, net);
  mqtt.setKeepAlive(30);
  mqtt.setTimeout(5000);
  mqtt.setWill(topic("availability").c_str(), "offline", true, 1);
}

static void connectMqttIfReady() {
  if (mqtt.connected()) { mqttRetry = MQTT_RETRY_MS; return; }
  if (mqttHost.isEmpty() || WiFi.status() != WL_CONNECTED) return;
  const uint32_t now = millis();
  if (now - lastMqttAttempt < mqttRetry) return;
  lastMqttAttempt = now;
  mqttRetry = min(mqttRetry * 2, uint32_t(60000));

  if (mqttCa.isEmpty() || mqttUser.isEmpty() || mqttPass.isEmpty() || mqttPort != 8883) {
    Serial.println("GC_NET TLS broker CA and individual credentials required (port 8883)");
    return;
  }
  if (time(nullptr) < 1700000000) {
    static bool timeRequested = false;
    if (!timeRequested) { configTime(0, 0, "pool.ntp.org", "time.cloudflare.com"); timeRequested = true; }
    return; // Certificate validation needs a clock; measurements keep running.
  }
  configureMqttClient();
  const bool ok = mqttUser.isEmpty()
    ? mqtt.connect(deviceId.c_str())
    : mqtt.connect(deviceId.c_str(), mqttUser.c_str(), mqttPass.c_str());
  if (!ok) {
    char tlsError[192] = {};
    const int tlsCode = net.lastError(tlsError, sizeof(tlsError));
    Serial.printf("GC_NET tls_error=%d detail=%s utc_epoch=%lld\n",
      tlsCode, tlsError, static_cast<long long>(time(nullptr)));
    Serial.printf("GC_NET mqtt_failed host=%s port=%u err=%d rc=%d\n",
      mqttHost.c_str(), mqttPort, int(mqtt.lastError()), int(mqtt.returnCode()));
    return;
  }

  mqtt.subscribe(topic("challenge"), 1);
  mqtt.publish(topic("availability"), "online", true, 1);
  publishAnnouncement();
  if (bleProvisionPending) { saveBleProvisionPending(false); bleProvisioner.stop(); }
  Serial.printf("GC_NET mqtt_online broker=%s:%u device=%s\n", mqttHost.c_str(), mqttPort, deviceId.c_str());
}

static void printNetworkInfo() {
  Serial.printf("GC_NET utc_epoch=%lld ca_bytes=%u tls_handshake_timeout_s=10\n",
    static_cast<long long>(time(nullptr)), unsigned(mqttCa.length()));
  Serial.printf("GC_NET device=%s name=%s fw=%s\n", deviceId.c_str(), deviceName.c_str(), FW_VERSION);
  Serial.printf("GC_NET wifi_configured=%s wifi_status=%d ssid=%s ip=%s rssi=%d\n",
    wifiSsid.isEmpty() ? "no" : "yes", int(WiFi.status()), wifiSsid.c_str(),
    WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "-",
    WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0);
  Serial.printf("GC_NET mqtt_configured=%s mqtt_connected=%s host=%s port=%u user=%s\n",
    mqttHost.isEmpty() ? "no" : "yes", mqtt.connected() ? "yes" : "no",
    mqttHost.c_str(), mqttPort, mqttUser.isEmpty() ? "-" : mqttUser.c_str());
}

static void printInfo() {
  Serial.printf("Grow-Central Soil Node %s firmware=%s\n", deviceId.c_str(), FW_VERSION);
  Serial.printf("GC_ID fingerprint=%s hardware_uid=%s\n", identity.getFingerprint().c_str(), hardwareUid.c_str());
  Serial.printf("pin=A0/GPIO2 adc=12bit air_raw=%u water_raw=%u substrate_raw=%u calibrated=%s air_calibrated=%s wet_calibrated=%s substrate_calibrated=%s\n", airRaw, waterRaw, substrateRaw, calibrationReady() ? "yes" : "no", airCalibrated ? "yes" : "no", waterCalibrated ? "yes" : "no", substrateCalibrated ? "yes" : "no");
  Serial.println("commands:");
  Serial.println("  INFO | CAL AIR | CAL WATER | CAL SUBSTRATE | RESET CAL");
  Serial.println("  USB ID <64-character nonce> (signed identity, no private key)");
  Serial.println("  NET INFO");
  Serial.println("  NET WIFI <ssid>|<password>");
  Serial.println("  NET MQTT <host>|<port>|<user>|<password>");
  Serial.println("  NET CA <base64 DER CA certificate> (USB only)");
  Serial.println("  NET NAME <display name> | NET CLEAR | REBOOT");
  Serial.println("AIR and WATER define the electrical range; FRESH SUBSTRATE is an agronomic reference, not field capacity.");
}

static void parseWifiCommand(const String& value) {
  const int sep = value.indexOf('|');
  if (sep < 1) {
    Serial.println("ERR usage: NET WIFI <ssid>|<password>");
    return;
  }
  wifiSsid = value.substring(0, sep);
  wifiPass = value.substring(sep + 1);
  wifiSsid.trim();
  if (wifiSsid.isEmpty()) {
    Serial.println("ERR empty SSID");
    return;
  }
  saveNetworkConfig();
  mqtt.disconnect();
  WiFi.disconnect(true, false);
  delay(100);
  lastWifiAttempt = 0;
  startWifiIfConfigured();
  Serial.println("OK WiFi configuration saved");
}

static void parseMqttCommand(const String& value) {
  int p1 = value.indexOf('|');
  int p2 = p1 < 0 ? -1 : value.indexOf('|', p1 + 1);
  int p3 = p2 < 0 ? -1 : value.indexOf('|', p2 + 1);
  if (p1 < 1) {
    Serial.println("ERR usage: NET MQTT <host>|<port>|<user>|<password>");
    return;
  }
  mqttHost = value.substring(0, p1);
  mqttHost.trim();
  const String portPart = p2 < 0 ? value.substring(p1 + 1) : value.substring(p1 + 1, p2);
  const long parsedPort = portPart.toInt();
  mqttPort = parsedPort > 0 && parsedPort <= 65535 ? uint16_t(parsedPort) : 8883;
  mqttUser = p2 < 0 ? "" : (p3 < 0 ? value.substring(p2 + 1) : value.substring(p2 + 1, p3));
  mqttPass = p3 < 0 ? "" : value.substring(p3 + 1);
  saveNetworkConfig();
  mqtt.disconnect();
  lastMqttAttempt = 0;
  Serial.println("OK MQTT configuration saved");
}

static void handleSerialCommands() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (!cmd.length()) return;
  String upper = cmd;
  upper.toUpperCase();

  if (upper.startsWith("USB ID ")) {
    const String nonce = cmd.substring(7);
    if (nonce.length() != 64) { Serial.println("ERR invalid identity challenge"); return; }
    for (size_t i = 0; i < nonce.length(); ++i) {
      if (!isxdigit(static_cast<unsigned char>(nonce[i]))) { Serial.println("ERR invalid identity challenge"); return; }
    }
    const String body = "{\"nonce\":\"" + nonce + "\",\"announcement\":" + announcementPayload() + "}";
    const String proof = identity.sign(deviceId, "proof", body, jsonEscape);
    if (proof.isEmpty()) Serial.println("ERR device identity unavailable");
    else Serial.println("GC_USB_ID " + proof);
  } else if (upper == "INFO") {
    printInfo();
    printNetworkInfo();
  } else if (upper == "CAL AIR") {
    Serial.println("CAL AIR: keep sensor dry/in air...");
    airRaw = calibrationSnapshot();
    airCalibrated = true;
    saveCalibration();
    emaRaw = NAN;
    Serial.printf("CAL AIR SAVED: %u\n", airRaw);
  } else if (upper == "CAL WATER") {
    Serial.println("CAL WATER: immerse probe area only, keep electronics dry...");
    waterRaw = calibrationSnapshot();
    waterCalibrated = true;
    saveCalibration();
    emaRaw = NAN;
    Serial.printf("CAL WATER SAVED: %u\n", waterRaw);
  } else if (upper == "CAL SUBSTRATE") {
    Serial.println("CAL SUBSTRATE: place probe in representative fresh potting soil...");
    const uint16_t candidate = calibrationSnapshot();
    if (!airCalibrated || !waterCalibrated) {
      Serial.println("ERR calibrate AIR and WATER first");
    } else if (!(candidate > waterRaw + 50 && candidate + 50 < airRaw)) {
      Serial.printf("ERR substrate reference implausible: %u\n", candidate);
    } else {
      substrateRaw = candidate;
      substrateCalibrated = true;
      saveCalibration();
      emaRaw = NAN;
      Serial.printf("CAL SUBSTRATE SAVED: %u\n", substrateRaw);
    }
  } else if (upper == "RESET CAL") {
    airRaw = DEFAULT_AIR_RAW;
    waterRaw = DEFAULT_WATER_RAW;
    substrateRaw = DEFAULT_SUBSTRATE_RAW;
    airCalibrated = false;
    waterCalibrated = false;
    substrateCalibrated = false;
    saveCalibration();
    emaRaw = NAN;
    Serial.println("CALIBRATION RESET TO PROVISIONAL REFERENCES");
  } else if (upper == "NET INFO") {
    printNetworkInfo();
  } else if (upper.startsWith("NET WIFI ")) {
    parseWifiCommand(cmd.substring(9));
  } else if (upper.startsWith("NET CA ")) {
    String certificate = cmd.substring(7);
    certificate.trim();
    if (certificate.length() < 100 || certificate.length() > 1600) {
      Serial.println("ERR invalid CA certificate length");
      return;
    }
    for (size_t i = 0; i < certificate.length(); ++i) {
      const char c = certificate[i];
      if (!isalnum(static_cast<unsigned char>(c)) && c != '+' && c != '/' && c != '=') { Serial.println("ERR invalid certificate encoding"); return; }
    }
    String pem = "-----BEGIN CERTIFICATE-----\n";
    for (size_t i = 0; i < certificate.length(); i += 64) pem += certificate.substring(i, i + 64) + "\n";
    pem += "-----END CERTIFICATE-----\n";
    mqttCa = pem;
    saveNetworkConfig();
    mqtt.disconnect();
    Serial.println("OK broker CA stored");
  } else if (upper.startsWith("NET MQTT ")) {
    parseMqttCommand(cmd.substring(9));
  } else if (upper.startsWith("NET NAME ")) {
    deviceName = cmd.substring(9);
    deviceName.trim();
    if (deviceName.isEmpty()) deviceName = "Grow-Central Soil Sensor";
    saveNetworkConfig();
    publishAnnouncement();
    Serial.println("OK device name saved");
  } else if (upper == "NET CLEAR") {
    clearNetworkConfig();
    Serial.println("OK network configuration cleared");
  } else if (upper == "REBOOT") {
    Serial.println("REBOOTING");
    delay(100);
    ESP.restart();
  } else {
    Serial.println("UNKNOWN COMMAND");
  }
}

static void reportReading(const SoilReading& r) {
  const uint16_t span = r.rawMax - r.rawMin;
  if (r.sensorOk) {
    Serial.printf("GC_SOIL raw=%u median=%u filtered=%.1f pct=%.1f min=%u max=%u span=%u sigma=%.1f quality=%s state=%s wifi=%d mqtt=%d uptime=%lu\n",
      r.rawMean, r.rawMedian, r.filteredRaw, r.moisturePct,
      r.rawMin, r.rawMax, span, r.sigma, r.quality, r.state,
      WiFi.status() == WL_CONNECTED ? 1 : 0, mqttOnline ? 1 : 0,
      static_cast<unsigned long>(millis()));
  } else {
    Serial.printf("GC_SOIL raw=%u median=%u min=%u max=%u span=%u sigma=%.1f quality=%s state=SENSOR_FAULT wifi=%d mqtt=%d uptime=%lu\n",
      r.rawMean, r.rawMedian, r.rawMin, r.rawMax, span, r.sigma, r.quality,
      WiFi.status() == WL_CONNECTED ? 1 : 0, mqttOnline ? 1 : 0,
      static_cast<unsigned long>(millis()));
  }
}

static void measurementTask(void*) {
  TickType_t wake = xTaskGetTickCount();
  for (;;) {
    const SoilReading reading = sampleSoil();
    portENTER_CRITICAL(&readingLock);
    latestReading = reading;
    readingAvailable = true;
    portEXIT_CRITICAL(&readingLock);
    reportReading(reading);
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(REPORT_INTERVAL_MS));
  }
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  // Temporarily enable the hardware entropy source before generating the first key.
  // It must be disabled before normal ADC measurements start.
  bootloader_random_enable();
  const bool identityReady = identity.begin();
  bootloader_random_disable();
  if (!identityReady) Serial.println("GC_ID initialization failed; unsigned messages disabled");
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);
  pinMode(SOIL_PIN, INPUT);
  adcLock = xSemaphoreCreateMutex();
  deriveDeviceId();
  loadCalibration();
  loadNetworkConfig();
  if (bleProvisionPending || wifiSsid.isEmpty() || mqttHost.isEmpty() || mqttUser.isEmpty() || mqttPass.isEmpty() || mqttCa.isEmpty()) {
    bleProvisioner.begin(deviceId, announcementPayload(), identity);
    Serial.println("GC_BLE provisioning active; accept in Grow-Central and hold BOOT when prompted");
  }
  mqtt.setOptions(30, true, 1500);
  mqtt.onMessage(onMqttMessage);
  printInfo();
  printNetworkInfo();
  if (!adcLock || xTaskCreate(measurementTask, "gc-measure", 4096, nullptr, 2, nullptr) != pdPASS) {
    Serial.println("GC_SOIL measurement task failed");
  }
  startWifiIfConfigured();
}

void loop() {
  handleSerialCommands();
  bleProvisioner.loop();
  BleNetworkConfig bleConfig;
  if (bleProvisioner.take(bleConfig)) {
    wifiSsid = bleConfig.ssid; wifiPass = bleConfig.wifiPass; mqttHost = bleConfig.host; mqttPort = bleConfig.port;
    mqttUser = bleConfig.user; mqttPass = bleConfig.pass; mqttCa = caDerBase64ToPem(bleConfig.ca); deviceName = bleConfig.name;
    saveNetworkConfig();
    saveBleProvisionPending(true);
    lastWifiAttempt = 0; lastMqttAttempt = 0;
    Serial.println("GC_BLE secure provisioning committed");
    startWifiIfConfigured();
  }
  maintainWifi();
  connectMqttIfReady();
  if (mqtt.connected()) mqtt.loop();
  handleIdentityProof();
  mqttOnline = mqtt.connected();

  SoilReading reading{};
  if (currentReading(reading)) publishState(reading);
  delay(5);
}
