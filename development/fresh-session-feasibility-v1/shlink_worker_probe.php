<?php
/** Read only the declared worker settings, never print raw process environments. */
declare(strict_types=1);
$settings = ['DB_DRIVER', 'DEFAULT_DOMAIN', 'IS_HTTPS_ENABLED', 'REDIS_SERVERS',
    'REDIS_PUB_SUB_ENABLED', 'MERCURE_ENABLED', 'RABBITMQ_ENABLED', 'MATOMO_ENABLED',
    'AUTO_RESOLVE_TITLES', 'SKIP_INITIAL_GEOLITE_DOWNLOAD', 'WEB_WORKER_NUM',
    'TASK_WORKER_NUM', 'SHLINK_RUNTIME'];
$workers = [];
foreach (glob('/proc/[0-9]*/cmdline') as $path) {
    $command = @file_get_contents($path);
    if ($command === false || strpos($command, 'bin/roadrunner-worker.php') === false) {
        continue;
    }
    $raw = @file_get_contents(dirname($path) . '/environ');
    if ($raw === false) {
        throw new RuntimeException('Cannot observe owned worker environment');
    }
    $environment = [];
    foreach (explode("\0", $raw) as $entry) {
        $parts = explode('=', $entry, 2);
        if (count($parts) === 2) {
            $environment[$parts[0]] = $parts[1];
        }
    }
    if (($environment['RR_MODE'] ?? null) !== 'http') {
        continue;
    }
    $selected = [];
    foreach ($settings as $key) {
        $expected = getenv($key);
        if ($expected === false || ($environment[$key] ?? null) !== $expected) {
            throw new RuntimeException('HTTP worker configuration mismatch: ' . $key);
        }
        $selected[$key] = $environment[$key];
    }
    if (empty($environment['INITIAL_API_KEY']) || $environment['INITIAL_API_KEY'] !== getenv('INITIAL_API_KEY')) {
        throw new RuntimeException('HTTP worker initial key mismatch');
    }
    $workers[] = ['pid' => basename(dirname($path)), 'mode' => 'http', 'settings' => $selected,
        'initial_api_key_sha256' => hash('sha256', $environment['INITIAL_API_KEY'])];
}
if (count($workers) !== 1) {
    throw new RuntimeException('Expected exactly one original HTTP worker');
}
echo json_encode(['status' => 'worker_spawn_configuration_verified', 'workers' => $workers,
    'scope' => 'process spawn environment; effective listener config is verified separately through the original container bootstrap'],
    JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR), "\n";
