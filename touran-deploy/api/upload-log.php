<?php
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['ok'=>false,'error'=>'POST required']); exit; }
$len = (int)($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($len <= 0 || $len > 2097152) { http_response_code(413); echo json_encode(['ok'=>false,'error'=>'invalid size']); exit; }
$body = file_get_contents('php://input');
if ($body === false || $body === '' || strlen($body) > 2097152) { http_response_code(400); echo json_encode(['ok'=>false,'error'=>'empty body']); exit; }
$install = $_SERVER['HTTP_X_TOURAN_INSTALL'] ?? 'anon';
$install = preg_replace('/[^A-Za-z0-9-]/', '', $install);
if ($install === '' || strlen($install) > 64) $install = 'anon';
$type = $_SERVER['HTTP_X_TOURAN_REPORT'] ?? 'log';
$allowedTypes = ['log','capability','radio-system','selfcheck'];
$type = in_array($type, $allowedTypes, true) ? $type : 'log';
$root = dirname(__DIR__, 3) . '/private/touran-logs';
if (!is_dir($root) && !mkdir($root, 0700, true)) { http_response_code(500); echo json_encode(['ok'=>false,'error'=>'storage unavailable']); exit; }
$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$rateKey = hash('sha256', $ip . '|' . $install);
$rateFile = $root . '/.rate-' . $rateKey;
$now = time();
if (is_file($rateFile)) {
  $last = (int)@file_get_contents($rateFile);
  if ($last > 0 && ($now - $last) < 3) { http_response_code(429); echo json_encode(['ok'=>false,'error'=>'too many requests']); exit; }
}
@file_put_contents($rateFile, (string)$now, LOCK_EX);
$id = gmdate('Ymd_His') . '_' . substr($install, 0, 12) . '_' . bin2hex(random_bytes(5));
$file = $root . '/' . $id . '_' . $type . '.log';
$meta = "# received_utc=" . gmdate('c') . "\n# remote_ip_hash=" . hash('sha256', $ip) . "\n# report_type=" . $type . "\n";
if (file_put_contents($file, $meta . $body, LOCK_EX) === false) { http_response_code(500); echo json_encode(['ok'=>false,'error'=>'write failed']); exit; }
@chmod($file, 0600);
$summary = [
  'vag_blocks_seen' => preg_match_all('/CAP_VAG_[0-9]+/', $body),
  'pid_support_frames' => substr_count($body, 'PID_SUPPORT'),
  'adapter_commands_seen' => preg_match_all('/CAP_AT[A-Z0-9@]+/', $body),
];
echo json_encode(['ok'=>true,'id'=>$id,'summary'=>$summary], JSON_UNESCAPED_SLASHES);
