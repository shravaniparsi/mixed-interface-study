<?php
// Ephemeral ordinary actor for an isolated qualification container; stdin is never logged.
$d = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
$files = [];
foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator('/config', FilesystemIterator::SKIP_DOTS)) as $file) {
    if ($file->isFile() && $file->getFilename() === 'grocy.db') $files[] = $file->getPathname();
}
if (count($files) !== 1) throw new RuntimeException('Expected one initialized Grocy database');
$db = new PDO('sqlite:' . $files[0]);
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$db->beginTransaction();
$q = $db->prepare('INSERT INTO users(username, first_name, last_name, password) VALUES(?,?,?,?)');
$q->execute([$d['username'], 'Study', 'Actor', password_hash($d['password'], PASSWORD_ARGON2ID)]);
$id = (int)$db->lastInsertId();
$names = ['MASTER_DATA_EDIT','STOCK','TASKS','USERS_READ'];
$lookup = $db->prepare('SELECT id FROM permission_hierarchy WHERE name=?');
$insert = $db->prepare('INSERT INTO user_permissions(user_id,permission_id) VALUES(?,?)');
foreach ($names as $name) {
    $lookup->execute([$name]); $permissions = $lookup->fetchAll(PDO::FETCH_COLUMN);
    if (count($permissions) !== 1) throw new RuntimeException('Permission binding not unique: '.$name);
    $insert->execute([$id,(int)$permissions[0]]);
}
$key = bin2hex(random_bytes(24));
$q = $db->prepare('INSERT INTO api_keys(api_key,user_id,expires,key_type,description) VALUES(?,?,?,?,?)');
$q->execute([$key,$id,'2999-12-31 23:59:59','default','Ephemeral study actor']);
$q = $db->prepare('SELECT permission_name FROM user_permissions_resolved WHERE user_id=?');
$q->execute([$id]); $resolved = $q->fetchAll(PDO::FETCH_COLUMN);
if (in_array('ADMIN',$resolved,true)) throw new RuntimeException('Unexpected administrative role');
foreach ($names as $name) if (!in_array($name,$resolved,true)) throw new RuntimeException('Missing scoped role');
$db->commit();
echo 'STUDY_AUTH='.json_encode(['username'=>$d['username'],'password'=>$d['password'],'token'=>$key,'user_id'=>$id,'permissions'=>$names]).PHP_EOL;
