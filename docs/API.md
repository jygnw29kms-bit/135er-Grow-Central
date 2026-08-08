# API

Basis:

```text
http://<raspberry-pi>:8080
```

## Health

```http
GET /api/health
```

## DF100M Status

```http
GET /api/df100m/status
```

## BLE Discovery

```http
GET /api/df100m/discover
```

## Connect

```http
POST /api/df100m/connect?address=<BLE_ADDRESS>
```

## Disconnect

```http
POST /api/df100m/disconnect
```

## GATT Services

```http
GET /api/df100m/services
```

## Speed Test

```http
POST /api/df100m/speed?percent=30
```

**Experimental.** Nicht als validiertes DF100M-Protokoll behandeln.

## Quellen

Siehe [SOURCES.md](SOURCES.md).
