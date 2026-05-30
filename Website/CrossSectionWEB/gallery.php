<?php

require __DIR__ . '/config.php';
?>
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <title>Galéria</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 960px;
            margin: 40px auto;
            padding: 0 20px;
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
        }
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 16px;
        }
        .gallery-thumb {
            position: relative;
            border: 2px solid #eee;
            border-radius: 8px;
            overflow: hidden;
            background: #f9f9f9;
            cursor: pointer;
        }
        .gallery-thumb img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            display: block;
        }
        .caption {
            padding: 8px;
            font-size: 0.9rem;
            background: #fff;
            border-top: 1px solid #ddd;
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
<h1>Galéria Obrázkov</h1>

<div class="gallery-grid">
    <?php
    $stmt = $pdo->prepare("SELECT * FROM media_main WHERE type = 'photo' ORDER BY uploaded_at DESC");
    $stmt->execute();
    $photos = $stmt->fetchAll();

    if (count($photos) === 0) {
        echo "<p>Žiadne fotografie nenahraté.</p>";
    } else {
        foreach ($photos as $p) {
            $url = htmlspecialchars($p['filepath']);
            $alt = htmlspecialchars($p['title']);
            echo '<div class="gallery-thumb">';
            echo    "<img src=\"$url\" alt=\"$alt\">";
            echo    '<div class="caption">' . $alt . '</div>';
            echo '</div>';
        }
    }
    ?>
</div>

<a class="back-link" href="upload.html">Nahrať ďalší súbor</a>
</body>
</html>
