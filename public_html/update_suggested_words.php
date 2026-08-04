<?php
/**
 * Rebuild SuggestedWords for autocomplete.php.
 * Prefer: poc/.venv/bin/python poc/scripts/refresh_suggested_words.py --apply
 */
declare(strict_types=1);

include __DIR__ . '/database.php';

header('Content-Type: text/plain; charset=UTF-8');

$tables = ['PasuramsArthamTablePOC', 'PasuramsArthamTable'];
$tokens = [];

function compact_hyphen_spaces(string $text): string
{
    return preg_replace('/\s*-\s*/', '-', trim($text));
}

function add_token(array &$tokens, string $word): void
{
    $word = trim($word);
    if ($word === '' || strlen($word) > 255) {
        return;
    }
    $key = $word;
    if (preg_match('/^[\x00-\x7F]+$/', $word)) {
        $key = strtolower($word);
    }
    $tokens[$key] = $word;
}

function extract_similar_tokens(array &$tokens, string $similar): void
{
    foreach (explode(',', $similar) as $raw) {
        $segment = trim($raw);
        if ($segment === '') {
            continue;
        }
        add_token($tokens, $segment);
        $compact = compact_hyphen_spaces($segment);
        if ($compact !== '' && $compact !== $segment) {
            add_token($tokens, $compact);
        }
        if (preg_match('/^(\d+(?:-\d+)+|\d+)(?:\s+.*)?$/', $segment, $m)) {
            add_token($tokens, $m[1]);
        }
        if (preg_match_all('/(\d+(?:-\d+)+(?:\s+[^,\d][^,]*)?)/u', $segment, $found, PREG_SET_ORDER)) {
            foreach ($found as $hit) {
                $piece = trim($hit[1]);
                if ($piece !== '') {
                    add_token($tokens, $piece);
                    if (preg_match('/^(\d+(?:-\d+)+)/', $piece, $code)) {
                        add_token($tokens, $code[1]);
                    }
                }
            }
        }
    }
}

foreach ($tables as $table) {
    $check = $conn->query("SHOW TABLES LIKE '" . $conn->real_escape_string($table) . "'");
    if (!$check || $check->num_rows === 0) {
        continue;
    }
    $check->free();
    $sql = "SELECT DISTINCT SimilarWords, Word, PasuramNumber FROM {$table}";
    $result = $conn->query($sql);
    if (!$result) {
        continue;
    }
    while ($row = $result->fetch_assoc()) {
        $pasuram = (int) ($row['PasuramNumber'] ?? 0);
        if ($pasuram > 0) {
            add_token($tokens, (string) $pasuram);
        }
        $word = trim((string) ($row['Word'] ?? ''));
        if ($word !== '') {
            add_token($tokens, $word);
            extract_similar_tokens($tokens, $word);
        }
        $similar = (string) ($row['SimilarWords'] ?? '');
        if ($similar !== '') {
            extract_similar_tokens($tokens, $similar);
        }
    }
    $result->free();
}

$words = array_values($tokens);
sort($words, SORT_STRING);

$conn->query('TRUNCATE TABLE SuggestedWords');
$stmt = $conn->prepare('INSERT INTO SuggestedWords (Word) VALUES (?)');
foreach ($words as $word) {
    $stmt->bind_param('s', $word);
    $stmt->execute();
}
$stmt->close();
$conn->close();

echo 'Suggested words updated successfully. Count: ' . count($words);
