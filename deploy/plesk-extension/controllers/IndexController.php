<?php

class IndexController extends pm_Controller_Action
{
    private const CORE_URL = 'http://127.0.0.1:18765';
    private const ADMIN_URL = 'http://127.0.0.1:18766';
    private const PLATFORM_URL = 'http://127.0.0.1:18767';
    private const TOKEN_FILE = '/opt/psa/var/modules/grow-central/admin.token';
    private const SETTINGS_FILE = '/opt/psa/var/modules/grow-central/settings.json';

    private function requestJson(string $url, string $token = ''): ?array
    {
        $headers = ["Accept: application/json"];
        if ($token !== '') {
            $headers[] = 'X-Growcentral-Admin: ' . $token;
        }
        $context = stream_context_create([
            'http' => [
                'method' => 'GET',
                'header' => implode("\r\n", $headers),
                'timeout' => 3,
                'ignore_errors' => true,
            ],
        ]);
        $raw = @file_get_contents($url, false, $context);
        if (!is_string($raw) || $raw === '') {
            return null;
        }
        $decoded = json_decode($raw, true);
        return is_array($decoded) ? $decoded : null;
    }

    public function indexAction()
    {
        $core = $this->requestJson(self::CORE_URL . '/health');
        $admin = $this->requestJson(self::ADMIN_URL . '/health');
        $platform = $this->requestJson(self::PLATFORM_URL . '/health');
        $token = is_readable(self::TOKEN_FILE) ? trim((string) @file_get_contents(self::TOKEN_FILE)) : '';
        $stats = $token !== '' ? $this->requestJson(self::ADMIN_URL . '/api/admin/stats', $token) : null;
        $devices = $token !== '' ? $this->requestJson(self::ADMIN_URL . '/api/admin/devices', $token) : null;
        $platformReports = $token !== '' ? $this->requestJson(self::PLATFORM_URL . '/api/admin/platform', $token) : null;
        $settings = [];
        if (is_readable(self::SETTINGS_FILE)) {
            $rawSettings = json_decode((string) @file_get_contents(self::SETTINGS_FILE), true);
            if (is_array($rawSettings)) {
                $settings = $rawSettings;
            }
        }

        $checks = [
            [
                'name' => 'Grow-Central Cloud-Core V6',
                'path' => '/opt/135er-growcentral-cloud',
                'url' => 'https://135ercloud.grow-central.de/',
                'ready' => is_array($core),
            ],
            [
                'name' => 'Plesk-Administration V7',
                'path' => '127.0.0.1:18766 · nur intern',
                'url' => null,
                'ready' => is_array($admin),
            ],
            [
                'name' => 'Plattform-/HomeKit-Status',
                'path' => '127.0.0.1:18767 · nur intern',
                'url' => null,
                'ready' => is_array($platform),
            ],
            [
                'name' => 'Grow-Central Projektseite',
                'path' => '/var/www/vhosts/grow-central.de/httpdocs',
                'url' => 'https://grow-central.de/',
                'ready' => is_file('/var/www/vhosts/grow-central.de/httpdocs/index.html'),
            ],
        ];

        $coreVersion = is_array($core) ? ($core['version'] ?? $core['api_version'] ?? 'erkannt') : 'nicht erreichbar';
        $adminVersion = is_array($admin) ? ($admin['version'] ?? 'erkannt') : 'nicht erreichbar';
        $platformVersion = is_array($platform) ? ($platform['version'] ?? 'erkannt') : 'nicht erreichbar';
        $compatibility = [
            [
                'component' => 'Cloud-Core',
                'expected' => 'V6 kompatibel',
                'actual' => (string) $coreVersion,
                'ready' => is_array($core),
                'note' => 'Öffentliche API, Gerätebindung und Remote-Dienste',
            ],
            [
                'component' => 'Cloud-Administration',
                'expected' => 'V7',
                'actual' => (string) $adminVersion,
                'ready' => is_array($admin) && ((string) $adminVersion === '7' || (string) $adminVersion === '7.0'),
                'note' => 'Freischaltungen, Pakete, Gerätestatus und Administration',
            ],
            [
                'component' => 'Plattform-Status',
                'expected' => 'Schema/Service 1',
                'actual' => (string) $platformVersion,
                'ready' => is_array($platform) && (string) $platformVersion === '1',
                'note' => 'Signierte Pi-Berichte zu Version, API und HomeKit-Publikation',
            ],
            [
                'component' => 'Geräteprotokoll',
                'expected' => 'gc-device-v1 + Ed25519',
                'actual' => 'serverseitig vorbereitet',
                'ready' => is_array($core) && is_array($admin),
                'note' => 'Pi/ESP melden ihre Laufzeitversion über den Plattform-Status',
            ],
            [
                'component' => 'Apple Home / HomeKit',
                'expected' => 'HomeKit-Diagnose Schema 1',
                'actual' => is_array($platform) ? 'Cloud-Spiegel bereit' : 'lokal verfügbar / Cloud-Spiegel fehlt',
                'ready' => true,
                'note' => 'Cloud bleibt optional; Publikationsstatus wird primär lokal geführt',
            ],
        ];

        $this->view->assign([
            'checks' => $checks,
            'core' => $core,
            'admin' => $admin,
            'platform' => $platform,
            'stats' => $stats,
            'devices' => is_array($devices) ? $devices : [],
            'platformReports' => is_array($platformReports) ? ($platformReports['reports'] ?? []) : [],
            'settings' => $settings,
            'compatibility' => $compatibility,
            'adminTokenConfigured' => strlen($token) >= 32,
            'fileManagerUrl' => '/smb/file-manager/list/domainId/8',
            'monitoringUrl' => '/modules/monitoring/',
            'terminalUrl' => '/modules/ssh-terminal/',
        ]);
    }
}

