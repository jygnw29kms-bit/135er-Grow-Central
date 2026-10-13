#include <Arduino.h>
#include <Preferences.h>
#include <math.h>

static constexpr uint8_t SOIL_PIN = A0;          // XIAO ESP32-C3 D0 / GPIO2
static constexpr uint16_t ADC_MAX = 4095;
static constexpr uint16_t DEFAULT_AIR_RAW = 3767;
static constexpr uint16_t DEFAULT_WATER_RAW = 1310;
static constexpr uint8_t SAMPLE_COUNT = 64;
static constexpr uint16_t SAMPLE_DELAY_MS = 2;
static constexpr uint32_t REPORT_INTERVAL_MS = 1000;
static constexpr float EMA_ALPHA = 0.20f;

Preferences prefs;
uint16_t airRaw = DEFAULT_AIR_RAW;
uint16_t waterRaw = DEFAULT_WATER_RAW;
float emaRaw = NAN;
uint32_t lastReport = 0;

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
  uint16_t samples[SAMPLE_COUNT];
  uint32_t sum = 0;
  uint16_t minVal = ADC_MAX;
  uint16_t maxVal = 0;

  for (uint8_t i = 0; i < SAMPLE_COUNT; ++i) {
    uint16_t v = analogRead(SOIL_PIN);
    samples[i] = v;
    sum += v;
    if (v < minVal) minVal = v;
    if (v > maxVal) maxVal = v;
    delay(SAMPLE_DELAY_MS);
  }

  qsort(samples, SAMPLE_COUNT, sizeof(uint16_t), compareU16);
  const uint16_t median = (samples[(SAMPLE_COUNT / 2) - 1] + samples[SAMPLE_COUNT / 2]) / 2;

  // 12.5% trimmed mean suppresses motion spikes / ADC outliers.
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
  return r;
}

static uint16_t calibrationSnapshot() {
  // Multiple complete measurement windows -> robust field calibration.
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
  prefs.end();
}

static void loadCalibration() {
  prefs.begin("gc-soil", true);
  airRaw = prefs.getUShort("air", DEFAULT_AIR_RAW);
  waterRaw = prefs.getUShort("water", DEFAULT_WATER_RAW);
  prefs.end();

  if (airRaw <= waterRaw + 100 || airRaw > ADC_MAX || waterRaw < 50) {
    airRaw = DEFAULT_AIR_RAW;
    waterRaw = DEFAULT_WATER_RAW;
  }
}

static void printInfo() {
  Serial.println("Grow-Central Soil Node GC-SOIL-01");
  Serial.printf("pin=A0/GPIO2 adc=12bit air_raw=%u water_raw=%u\n", airRaw, waterRaw);
  Serial.println("commands: INFO | CAL AIR | CAL WATER | RESET CAL");
  Serial.println("note: WATER is engineering reference only; final substrate calibration comes later.");
}

static void handleSerialCommands() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "INFO") {
    printInfo();
  } else if (cmd == "CAL AIR") {
    Serial.println("CAL AIR: keep sensor dry/in air...");
    airRaw = calibrationSnapshot();
    saveCalibration();
    emaRaw = NAN;
    Serial.printf("CAL AIR SAVED: %u\n", airRaw);
  } else if (cmd == "CAL WATER") {
    Serial.println("CAL WATER: immerse probe area only, keep electronics dry...");
    waterRaw = calibrationSnapshot();
    saveCalibration();
    emaRaw = NAN;
    Serial.printf("CAL WATER SAVED: %u\n", waterRaw);
  } else if (cmd == "RESET CAL") {
    airRaw = DEFAULT_AIR_RAW;
    waterRaw = DEFAULT_WATER_RAW;
    saveCalibration();
    emaRaw = NAN;
    Serial.println("CALIBRATION RESET TO PROVISIONAL REFERENCES");
  } else if (cmd.length()) {
    Serial.printf("UNKNOWN COMMAND: %s\n", cmd.c_str());
  }
}

static void reportReading(const SoilReading& r) {
  const uint16_t span = r.rawMax - r.rawMin;
  if (r.sensorOk) {
    Serial.printf("GC_SOIL raw=%u median=%u filtered=%.1f pct=%.1f min=%u max=%u span=%u sigma=%.1f quality=%s state=%s uptime=%lu\n",
      r.rawMean, r.rawMedian, r.filteredRaw, r.moisturePct,
      r.rawMin, r.rawMax, span, r.sigma, r.quality, r.state,
      static_cast<unsigned long>(millis()));
  } else {
    Serial.printf("GC_SOIL raw=%u median=%u min=%u max=%u span=%u sigma=%.1f quality=%s state=SENSOR_FAULT uptime=%lu\n",
      r.rawMean, r.rawMedian, r.rawMin, r.rawMax, span, r.sigma, r.quality,
      static_cast<unsigned long>(millis()));
  }
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);
  pinMode(SOIL_PIN, INPUT);
  loadCalibration();
  printInfo();
}

void loop() {
  handleSerialCommands();
  const uint32_t now = millis();
  if (now - lastReport >= REPORT_INTERVAL_MS) {
    lastReport = now;
    SoilReading reading = sampleSoil();
    reportReading(reading);
  }
  delay(5);
}
