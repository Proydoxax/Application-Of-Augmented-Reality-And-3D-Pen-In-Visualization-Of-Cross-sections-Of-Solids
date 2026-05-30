<?php
// upload.php
ini_set('display_errors', 1);
error_reporting(E_ALL);

require __DIR__ . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    die('<div class="message error">Chyba: Použite formulár na nahratie priečinka.</div>');
}

if (
    !isset($_FILES['files']) ||
    !isset($_FILES['files']['tmp_name']) ||
    count($_FILES['files']['tmp_name']) === 0
) {
    die('<div class="message error">Chyba: Žiadne súbory neboli vybrané.</div>');
}

$baseTitle = trim($_POST['title'] ?? '');
$type      = $_POST['type'] ?? '';
$keywords  = trim($_POST['keywords'] ?? '');

$allowedTypes = ['photo', 'video'];
if ($baseTitle === '' || !in_array($type, $allowedTypes, true)) {
    die('<div class="message error">Chyba: Neplatný názov alebo typ súboru.</div>');
}

switch ($type) {
    case 'photo':
        $destDir = __DIR__ . '/uploads/photos/database_photos/';
        break;
    case 'video':
        $destDir = __DIR__ . '/uploads/videos/database_photos/';
        break;
    default:
        die('<div class="message error">Chyba: Neznámy typ súboru.</div>');
}

if (!is_dir($destDir) && !mkdir($destDir, 0755, true)) {
    die('<div class="message error">Chyba: Nepodarilo sa vytvoriť adresár pre nahrávanie.</div>');
}

$files     = $_FILES['files'];
$numFiles  = count($files['tmp_name']);
$successes = [];
$errors    = [];

for ($i = 0; $i < $numFiles; $i++) {
    if (!is_uploaded_file($files['tmp_name'][$i])) {
        $errors[] = "Súbor #{$i} nebol validný nahraný súbor.";
        continue;
    }

    $originalPath = $files['name'][$i];
    $baseName     = basename($originalPath);
    $safeName     = preg_replace('/[^A-Za-z0-9_\-\.]/', '_', $baseName);
    if ($safeName === '') {
        $safeName = 'file_' . time() . "_{$i}";
    }

    $targetPath = $destDir . $safeName;
    if (file_exists($targetPath)) {
        $pathInfo    = pathinfo($safeName);
        $timestamp   = time();
        $newFilename = $pathInfo['filename'] . '_' . $timestamp . '.' . $pathInfo['extension'];
        $targetPath  = $destDir . $newFilename;
        $safeName    = $newFilename;
    }

    if (!move_uploaded_file($files['tmp_name'][$i], $targetPath)) {
        $errors[] = "Nepodarilo sa presunúť súbor '$baseName'.";
        continue;
    }

    $dbTitle = $baseTitle . ' ' . ($i + 1);

    $relativePath = 'uploads/' . ($type === 'photo' ? 'photos/' : 'videos/') . $safeName;

    try {
        $sql  = "INSERT INTO media_main (title, filename, filepath, type, keywords) 
                 VALUES (:title, :filename, :filepath, :type, :keywords)";
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            ':title'    => $dbTitle,
            ':filename' => $safeName,
            ':filepath' => $relativePath,
            ':type'     => $type,
            ':keywords' => $keywords === '' ? null : $keywords
        ]);
        $newId = $pdo->lastInsertId();
        $successes[] = "Súbor '$baseName' nahraný (ID: $newId).";
    } catch (PDOException $e) {
        if (file_exists($targetPath)) {
            unlink($targetPath);
        }
        $errors[] = "Chyba databázy pri '$baseName': " . $e->getMessage();
    }
}

?>
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <title>Výsledok Nahrávania</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 40px auto;
            padding: 0 20px;
        }
        h1 {
            color: #23DAFF;
        }
        .message {
            margin-top: 20px;
            padding: 10px;
            border-radius: 4px;
            font-size: 0.95rem;
        }
        .success {
            background-color: #e0f8e9;
            border: 1px solid #9ae69c;
            color: #1d7f3c;
        }
        .error {
            background-color: #fde0e0;
            border: 1px solid #e69c9c;
            color: #7f1d1d;
        }
        ul {
            margin-top: 10px;
        }
        a.back-link {
            display: inline-block;
            margin-top: 20px;
            padding: 8px 14px;
            background-color: #23DAFF;
            color: #fff;
            text-decoration: none;
            border-radius: 4px;
        }
        a.back-link:hover {
            background-color: #1bb8db;
        }
    </style>
</head>
<body>
<h1>Výsledok Nahrávania</h1>

<?php if (!empty($successes)): ?>
    <div class="message success">
        <p><strong>Nasledujúce súbory boli úspešne nahrané:</strong></p>
        <ul>
            <?php foreach ($successes as $msg): ?>
                <li><?php echo htmlspecialchars($msg); ?></li>
            <?php endforeach; ?>
        </ul>
    </div>
<?php endif; ?>

<?php if (!empty($errors)): ?>
    <div class="message error">
        <p><strong>Nasledujúce chyby sa vyskytli:</strong></p>
        <ul>
            <?php foreach ($errors as $err): ?>
                <li><?php echo htmlspecialchars($err); ?></li>
            <?php endforeach; ?>
        </ul>
    </div>
<?php endif; ?>

<a class="back-link" href="upload.html">Späť na nahrávanie</a>
</body>
</html>
