<?php
header('Content-Type: application/json; charset=UTF-8');

require __DIR__ . '/config.php';

try {
    $stmtPhotos = $pdo->prepare("
        SELECT title, filepath, keywords
        FROM media_main
        WHERE type = 'photo'
        ORDER BY uploaded_at DESC
    ");
    $stmtPhotos->execute();
    $photos = $stmtPhotos->fetchAll(PDO::FETCH_ASSOC);

    $stmtVideos = $pdo->prepare("
        SELECT title, filepath, keywords
        FROM media_main
        WHERE type = 'video'
        ORDER BY uploaded_at DESC
    ");
    $stmtVideos->execute();
    $videos = $stmtVideos->fetchAll(PDO::FETCH_ASSOC);

    $stmtPDFs = $pdo->prepare("
        SELECT title, filepath
        FROM media_main
        WHERE type = 'pdf'
        ORDER BY uploaded_at DESC
    ");
    $stmtPDFs->execute();
    $pdfs = $stmtPDFs->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode([
        'photos' => $photos,
        'videos' => $videos,
        'pdfs'   => $pdfs
    ], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'error' => 'Database error: ' . $e->getMessage()
    ]);
}
