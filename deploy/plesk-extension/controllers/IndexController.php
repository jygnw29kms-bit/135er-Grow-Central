<?php

class IndexController extends pm_Controller_Action
{
    private const CORE_URL = 'http://127.0.0.1:18765';
    private const ADMIN_URL = 'http://127.0.0.1:18766';
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
        $token = is_readable(self::TOKEN_FILE) ? trim((string) @file_get_contents(self::TOKEN_FILE)) : '';
        $stats = $token !== '' ? $this->requestJson(self::ADMIN_URL . '/api/admin/stats', $token) : null;
        $devices = $token !== '' ? $this->requestJson(self::ADMIN_URL . '/api/admin/devices', $token) : null;
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
                'name' => 'Grow-Central Projektseite',
                'path' => '/var/www/vhosts/grow-central.de/httpdocs',
                'url' => 'https://grow-central.de/',
                'ready' => is_file('/var/www/vhosts/grow-central.de/httpdocs/index.html'),
            ],
        ];

        $this->view->assign([
            'checks' => $checks,
            'core' => $core,
            'admin' => $admin,
            'stats' => $stats,
            'devices' => is_array($devices) ? $devices : [],
            'settings' => $settings,
            'adminTokenConfigured' => strlen($token) >= 32,
            'fileManagerUrl' => '/smb/file-manager/list/domainId/8',
            'monitoringUrl' => '/modules/monitoring/',
            'terminalUrl' => '/modules/ssh-terminal/',
        ]);
    }
}

