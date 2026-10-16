#pragma once
#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>
#include <mbedtls/pk.h>
#include <mbedtls/base64.h>
#include <mbedtls/sha256.h>
#include <mbedtls/ecdsa.h>

// Private key is kept in local NVS and never returned by a network/serial API.
class DeviceIdentity {
  mbedtls_pk_context key;
  bool ready = false;
  uint64_t next = 0, limit = 0;
  String publicKey, fingerprint;
  static int randomBytes(void*, unsigned char* out, size_t size) { esp_fill_random(out, size); return 0; }
  static String base64(const uint8_t* data, size_t size) {
    unsigned char result[1024]; size_t used = 0;
    if (mbedtls_base64_encode(result, sizeof(result), &used, data, size) != 0) return "";
    return String(reinterpret_cast<char*>(result), used);
  }
  bool reserve() {
    Preferences store;
    if (!store.begin("gc-identity", false)) return false;
    next = store.getULong64("next", 1);
    if (!next || next > 9007199254736895ULL) { store.end(); return false; }
    limit = next + 4096;
    const bool ok = store.putULong64("next", limit) == sizeof(uint64_t);
    store.end(); return ok;
  }
public:
  DeviceIdentity() { mbedtls_pk_init(&key); }
  bool begin() {
    Preferences store;
    if (!store.begin("gc-identity", false)) return false;
    const size_t length = store.getBytesLength("private");
    unsigned char der[256];
    int rc;
    if (length) {
      if (length > sizeof(der) || store.getBytes("private", der, length) != length) { store.end(); return false; }
      rc = mbedtls_pk_parse_key(&key, der, length, nullptr, 0);
    } else {
      rc = mbedtls_pk_setup(&key, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
      if (!rc) rc = mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(key), randomBytes, nullptr);
      if (!rc) {
        const int n = mbedtls_pk_write_key_der(&key, der, sizeof(der));
        if (n <= 0 || store.putBytes("private", der + sizeof(der) - n, n) != size_t(n)) rc = -1;
      }
    }
    memset(der, 0, sizeof(der)); store.end();
    if (rc || mbedtls_pk_get_type(&key) != MBEDTLS_PK_ECKEY || mbedtls_pk_ec(key)->grp.id != MBEDTLS_ECP_DP_SECP256R1) return false;
    const int n = mbedtls_pk_write_pubkey_der(&key, der, sizeof(der));
    if (n <= 0) return false;
    publicKey = base64(der + sizeof(der) - n, n);
    unsigned char hash[32];
    mbedtls_sha256_ret(der + sizeof(der) - n, n, hash, 0);
    for (uint8_t b : hash) { char hex[3]; snprintf(hex, sizeof(hex), "%02x", b); fingerprint += hex; }
    ready = !publicKey.isEmpty() && reserve(); return ready;
  }
  String getFingerprint() const { return fingerprint; }
  String sign(const String& id, const char* kind, const String& body, String (*escape)(const String&)) {
    if (!ready) return "";
    if (next >= limit && !reserve()) { ready = false; return ""; }
    char counter[24]; snprintf(counter, sizeof(counter), "%llu", static_cast<unsigned long long>(next++));
    const String message = "{\"device_id\":\"" + escape(id) + "\",\"kind\":\"" + kind + "\",\"seq\":" + counter + ",\"body\":" + body + "}";
    unsigned char hash[32], signature[MBEDTLS_ECDSA_MAX_LEN]; size_t used = 0;
    if (mbedtls_sha256_ret(reinterpret_cast<const unsigned char*>(message.c_str()), message.length(), hash, 0) != 0) return "";
    if (mbedtls_pk_sign(&key, MBEDTLS_MD_SHA256, hash, sizeof(hash), signature, &used, randomBytes, nullptr) != 0) return "";
    return "{\"schema\":\"gc-signed-v1\",\"algorithm\":\"ecdsa-p256-sha256\",\"public_key\":\"" + publicKey + "\",\"message\":\"" + escape(message) + "\",\"signature\":\"" + base64(signature, used) + "\"}";
  }
};
