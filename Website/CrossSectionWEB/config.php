<?php
// config.php

$host   = '127.0.0.1';
$port   = '4306';
$db     = 'gallery_db';
$user   = 'root';
//$pass   = '{=9Q9JI4lMl9P2ty}58#z<j%3me/DLo_141}X<8.j2!&qJ?6';
$pass   = '';
$charset= 'utf8mb4';

$dsn = "mysql:host=$host;port=$port;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];

try {
    $pdo = new PDO($dsn, $user, $pass, $options);
} catch (PDOException $e) {
    die("Database connection failed: " . $e->getMessage());
}
