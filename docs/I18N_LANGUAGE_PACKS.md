# GrowCentral Internationalization & Language Packs

## Product rule

GrowCentral is an international controlled-growing platform. The product name remains `GrowCentral` in every locale.

The UI is currently German-first, but the architecture must be locale-neutral. English is the canonical source language for translation keys and semantic meaning. German remains a fully supported bundled locale.

## User experience

Settings -> Language provides:

- current language selector
- bundled languages (initially `de`, `en`)
- `System language` option based on browser / PWA locale
- `Install language pack` action
- installed language-pack list with version, author, source and validation state
- remove / disable action for third-party packs
- instant preview / switch without reinstalling GrowCentral

The selected locale is stored per user when authentication is available. A device-local preference is used only as a fallback before login.

## Canonical key model

Application code never embeds translated business/UI strings directly. Code references stable English semantic keys, for example:

```text
settings.language.title
settings.language.system
settings.language.install_pack
rooms.empty_state
sensor.soil_moisture
sensor.offline
alerts.temperature_high
auth.remember_me
```

The key itself is the API contract. English (`en`) is the mandatory reference catalog. Every bundled and third-party locale maps the same keys to translated values.

Do not use full English sentences as keys. Keys must survive copy edits without breaking packs.

## Directory structure

```text
i18n/
  schema/
    language-pack.schema.json
  locales/
    en/
      manifest.json
      messages.json
    de/
      manifest.json
      messages.json
  README.md

/var/lib/growcentral/i18n/
  community/
    <locale>/<pack-id>/
      manifest.json
      messages.json
```

Bundled locales live in the repository and ship with GrowCentral. Community packs are stored outside the application source tree and never overwrite bundled files.

## Language pack format

A pack is a ZIP archive with exactly two root files:

- `manifest.json`
- `messages.json`

Example manifest:

```json
{
  "format": 1,
  "id": "community.fr-FR.example",
  "locale": "fr-FR",
  "language_name": "Français",
  "english_name": "French",
  "version": "1.0.0",
  "growcentral_min": "0.8.0",
  "growcentral_max": "1.x",
  "reference_catalog": "2026.10.17",
  "author": "Example Translator",
  "license": "CC0-1.0",
  "direction": "ltr"
}
```

Example messages:

```json
{
  "settings.language.title": "Langue",
  "settings.language.system": "Langue du système",
  "sensor.offline": "Capteur hors ligne"
}
```

Only string values are accepted in format 1. HTML, JavaScript, CSS, URLs and executable templates are forbidden.

## Fallback order

Lookup order:

1. selected locale / installed community pack
2. bundled language with the same base language where available (`pt-BR` -> `pt`)
3. bundled English `en`

A missing translation must never make a screen unusable. Missing keys are logged diagnostically and shown in English.

## Security model

Language packs are treated as untrusted data, never as plugins.

Import validation must:

1. reject archives above a strict compressed and uncompressed size limit;
2. reject absolute paths, `..`, symlinks and nested archive tricks;
3. accept only the two documented files;
4. validate UTF-8 and JSON structure against the bundled schema;
5. reject duplicate JSON keys;
6. validate BCP 47 locale identifiers;
7. validate semantic-version compatibility with the running GrowCentral version;
8. reject unknown manifest fields unless the format version explicitly permits them;
9. limit key count, key length and translated-string length;
10. reject control characters except normal whitespace;
11. never render pack strings as raw HTML;
12. store imported files under a generated internal directory rather than trusting archive names;
13. calculate and retain SHA-256 for audit information;
14. make installation an authenticated administrative action;
15. support deletion and rollback to bundled English/German without restart.

The backend must not execute code, load Python modules, load browser scripts, inject CSS or accept arbitrary URLs from a language pack.

## Signing and trust levels

Two trust levels are supported:

### Bundled / Official

- maintained in the GrowCentral repository
- reviewed through normal CI
- included in releases
- considered trusted content

### Community

- manually imported by an administrator
- marked visibly as `Community language pack`
- validated using the exact same parser/schema
- never receives additional runtime permissions

A future GrowCentral language-pack directory may distribute signed packs. Signature verification can improve provenance but does not replace strict content validation.

## Translator workflow

GrowCentral exports a translation template derived from the English reference catalog:

```json
{
  "settings.language.title": "Language",
  "settings.language.system": "System language",
  "sensor.offline": "Sensor offline"
}
```

A translator copies the template and replaces only values. Keys remain unchanged.

The UI should provide:

- `Download English translation template`
- coverage percentage
- missing-key report
- obsolete-key report
- validation before installation

This allows a community member to map English GrowCentral terminology to any language without learning the application source code.

## Formatting

Translations must use named variables rather than string concatenation:

```text
"device.last_seen": "Last seen {time}"
```

Variables are defined by the English catalog and may not be added or removed by a language pack. Import validation compares placeholders.

Pluralization should use CLDR / Intl-compatible rules rather than hand-written German/English branches.

Date, number, currency and unit formatting use the browser/server locale libraries. Sensor values remain canonical internally and are converted only for presentation.

## RTL support

The manifest supports `direction: rtl`. Layout code must use logical CSS properties (`margin-inline`, `padding-inline`, `inset-inline`) rather than left/right assumptions where practical.

## API outline

Suggested authenticated API surface:

```text
GET    /api/settings/language
PUT    /api/settings/language
GET    /api/i18n/locales
GET    /api/i18n/template/en
POST   /api/i18n/packs/validate
POST   /api/i18n/packs
DELETE /api/i18n/packs/{pack_id}
```

Import uses multipart upload with a strict request-size limit. Validation happens before permanent storage. Changing language does not require a server restart.

## CI requirements

CI must fail if:

- English reference catalog contains duplicate/invalid keys
- bundled German contains unknown keys
- placeholders differ from English
- bundled JSON does not match the schema
- production UI introduces untranslated hard-coded user-facing strings in designated UI modules

Coverage may initially permit incomplete German-to-English migration, but the threshold should increase until `en` and `de` are 100% for production UI.

## Migration from current German UI

1. Create English reference catalog from existing UI concepts.
2. Assign stable keys.
3. Move existing German text to `de/messages.json`.
4. Translate reference values to English.
5. Replace hard-coded strings feature by feature.
6. Add Settings language selector.
7. Add backend locale API and per-user preference.
8. Add secure pack validator/importer.
9. Add template export and coverage diagnostics.
10. Gate future production UI through i18n CI checks.

Do not attempt an unsafe global search/replace. Migration is incremental and must preserve existing functionality.

## Branding and terminology

`GrowCentral` is never translated.

Technical device/vendor names are not translated unless a localized vendor name is officially provided. Translation packs control descriptive UI wording, not hardware identity, API identifiers, database keys or protocol values.


## First-Boot-Regel

Die Sprache ist der **erste interaktive Schritt** des First-Boot. GrowCentral liest `navigator.languages` / `navigator.language` und markiert `de` oder `en` nur als Vorschlag. Der Benutzer bestätigt die Auswahl ausdrücklich. Erst danach werden Netzwerk, Zeitzone und Zugangsdaten gezeigt. Die bestätigte Locale wird als `GC_LOCALE` in die Runtime-Konfiguration übernommen. Kleine Flaggen dienen nur als visuelle Hilfe; maßgeblich sind Sprachname und Locale-Code.
