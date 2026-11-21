<?php
/** Read original effective listener configuration; never dispatch an event or consume a job. */
declare(strict_types=1);
use Shlinkio\Shlink\EventDispatcher\Listener\EnabledListenerCheckerInterface;

if (getenv('SHLINK_RUNTIME') !== 'rr' || getenv('RR_MODE') !== 'http') {
    throw new RuntimeException('Probe requires the declared RoadRunner HTTP configuration');
}
$container = require '/etc/shlink/config/container.php';
$config = $container->get('config');
$checker = $container->get(EnabledListenerCheckerInterface::class);
if (get_class($checker) !== 'Shlinkio\\Shlink\\Core\\EventDispatcher\\Helper\\EnabledListenerChecker') {
    throw new RuntimeException('Unexpected listener checker');
}
$rows = [];
$enabled = [];
foreach ($config['events']['async'] ?? [] as $event => $listeners) {
    foreach ($listeners as $listener) {
        $registered = $checker->shouldRegisterListener($event, $listener, true);
        $row = ['event' => $event, 'listener' => $listener, 'registered' => $registered];
        $rows[] = $row;
        if ($registered) {
            $enabled[] = $row;
        }
    }
}
if (count($rows) === 0) {
    throw new RuntimeException('Missing original asynchronous event declarations');
}
echo json_encode([
    'scope' => 'effective original asynchronous listener configuration; not a queue measurement',
    'checker' => get_class($checker),
    'runtime' => getenv('SHLINK_RUNTIME'),
    'worker_mode' => getenv('RR_MODE'),
    'listeners' => $rows,
    'enabled_count' => count($enabled),
    'status' => count($enabled) === 0 ? 'no_enabled_async_listeners' : 'unexpected_enabled_listeners',
], JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR), "\n";
exit(count($enabled) === 0 ? 0 : 1);
