<?php
/**
 * Refresh DivyaDesamAlwarMatrix on the Hostinger DB (127.0.0.1 via database.php).
 *
 * Also refreshes legacy DivyaDesamAlwarMatrixPOC (used by older divyadesam_alwar_matrix.php
 * still deployed on the server until you upload the new env-aware matrix page).
 *
 * Usage (browser or curl) — key is required:
 *   refresh_divyadesam_alwar_matrix.php?key=kanchi-dd-matrix-2026&env=all
 */
declare(strict_types=1);

const MATRIX_REFRESH_KEY = 'kanchi-dd-matrix-2026';
const MATRIX_TABLE = 'DivyaDesamAlwarMatrix';
const LEGACY_MATRIX_TABLE = 'DivyaDesamAlwarMatrixPOC';

$MATRIX_ENVS = [
    'poc' => 'PasuramsArthamTablePOC',
    'test' => 'PasuramsArthamTableTest',
    'prod' => 'PasuramsArthamTable',
];

header('Content-Type: text/plain; charset=UTF-8');

$key = $_GET['key'] ?? '';
if ($key !== MATRIX_REFRESH_KEY) {
    http_response_code(403);
    echo "Forbidden — open this full URL in your browser (key is required):\n\n";
    echo "https://nalayiram.in/refresh_divyadesam_alwar_matrix.php?key=" . MATRIX_REFRESH_KEY . "&env=all\n\n";
    echo "Expected output: [prod] Wrote 196 cells ... footer total 1206\n";
    exit;
}

$envArg = isset($_GET['env']) ? strtolower(trim($_GET['env'])) : 'all';
if ($envArg === 'all') {
    $envs = array_keys($MATRIX_ENVS);
} elseif (isset($MATRIX_ENVS[$envArg])) {
    $envs = [$envArg];
} else {
    http_response_code(400);
    echo "Invalid env. Use poc, test, prod, or all.\n";
    exit;
}

include __DIR__ . '/database.php';

$aggregateSql = "
SELECT
    d.DivyaDesam,
    p.Alzwar,
    COUNT(DISTINCT p.PasuramNumber) AS pasuram_count
FROM %s p
INNER JOIN DivyaDesamTable d
    ON p.PasuramNumber = d.PasuramNumber
WHERE p.Alzwar IS NOT NULL AND TRIM(p.Alzwar) <> ''
  AND d.DivyaDesam IS NOT NULL AND TRIM(d.DivyaDesam) <> ''
GROUP BY d.DivyaDesam, p.Alzwar
ORDER BY d.DivyaDesam, p.Alzwar
";

function ensureMatrixTable(mysqli $conn): bool
{
    $sql = "
CREATE TABLE IF NOT EXISTS " . MATRIX_TABLE . " (
    Environment VARCHAR(10) NOT NULL,
    DivyaDesam VARCHAR(512) NOT NULL,
    Alzwar VARCHAR(255) NOT NULL,
    PasuramCount INT NOT NULL,
    RefreshedAt DATETIME NOT NULL,
    PRIMARY KEY (Environment, DivyaDesam(191), Alzwar(191)),
    KEY idx_matrix_env_alwar (Environment, Alzwar(191)),
    KEY idx_matrix_env_divyadesam (Environment, DivyaDesam(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
";
    return (bool) $conn->query($sql);
}

function ensureLegacyMatrixTable(mysqli $conn): bool
{
    $sql = "
CREATE TABLE IF NOT EXISTS " . LEGACY_MATRIX_TABLE . " (
    DivyaDesam VARCHAR(512) NOT NULL,
    Alzwar VARCHAR(255) NOT NULL,
    PasuramCount INT NOT NULL,
    RefreshedAt DATETIME NOT NULL,
    PRIMARY KEY (DivyaDesam(191), Alzwar(191))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
";
    return (bool) $conn->query($sql);
}

/** @return array{0: list<array{0: string, 1: string, 2: int}>, 1: int}|null */
function fetchAggregateRows(mysqli $conn, string $pasuramTable)
{
    global $aggregateSql;
    $sql = sprintf($aggregateSql, $pasuramTable);
    $result = $conn->query($sql);
    if ($result === false) {
        return null;
    }

    $rows = [];
    $cellSum = 0;
    while ($row = $result->fetch_assoc()) {
        $count = (int) $row['pasuram_count'];
        $rows[] = [$row['DivyaDesam'], $row['Alzwar'], $count];
        $cellSum += $count;
    }
    $result->free();

    return [$rows, $cellSum];
}

function refreshEnvMatrix(mysqli $conn, string $env, array $rows, string $refreshedAt): int
{
    $envEsc = $conn->real_escape_string($env);
    if (!$conn->query('DELETE FROM ' . MATRIX_TABLE . " WHERE Environment = '{$envEsc}'")) {
        echo "[{$env}] DELETE failed: " . $conn->error . "\n";
        return 0;
    }

    $insertSql = '
INSERT INTO ' . MATRIX_TABLE . ' (Environment, DivyaDesam, Alzwar, PasuramCount, RefreshedAt)
VALUES (?, ?, ?, ?, ?)
';
    $stmt = $conn->prepare($insertSql);
    if ($stmt === false) {
        echo "[{$env}] Prepare failed: " . $conn->error . "\n";
        return 0;
    }

    $written = 0;
    foreach ($rows as [$divyadesam, $alzwar, $count]) {
        $bindEnv = $env;
        $bindDivyaDesam = $divyadesam;
        $bindAlzwar = $alzwar;
        $bindCount = $count;
        $bindRefreshedAt = $refreshedAt;
        $stmt->bind_param('sssis', $bindEnv, $bindDivyaDesam, $bindAlzwar, $bindCount, $bindRefreshedAt);
        if ($stmt->execute()) {
            $written++;
        }
    }
    $stmt->close();

    return $written;
}

function refreshLegacyMatrix(mysqli $conn, array $rows, string $refreshedAt, string $sourceLabel): int
{
    if (!$conn->query('DELETE FROM ' . LEGACY_MATRIX_TABLE)) {
        echo "[legacy] DELETE failed: " . $conn->error . "\n";
        return 0;
    }

    $insertSql = '
INSERT INTO ' . LEGACY_MATRIX_TABLE . ' (DivyaDesam, Alzwar, PasuramCount, RefreshedAt)
VALUES (?, ?, ?, ?)
';
    $stmt = $conn->prepare($insertSql);
    if ($stmt === false) {
        echo "[legacy] Prepare failed: " . $conn->error . "\n";
        return 0;
    }

    $written = 0;
    foreach ($rows as [$divyadesam, $alzwar, $count]) {
        $bindDivyaDesam = $divyadesam;
        $bindAlzwar = $alzwar;
        $bindCount = $count;
        $bindRefreshedAt = $refreshedAt;
        $stmt->bind_param('ssis', $bindDivyaDesam, $bindAlzwar, $bindCount, $bindRefreshedAt);
        if ($stmt->execute()) {
            $written++;
        }
    }
    $stmt->close();

    $cellSum = 0;
    foreach ($rows as [, , $count]) {
        $cellSum += $count;
    }
    echo "[legacy] Wrote {$written} cells to " . LEGACY_MATRIX_TABLE . " from {$sourceLabel}; footer total {$cellSum}; at {$refreshedAt}\n";

    return $written;
}

function printVerify(mysqli $conn, string $env): void
{
    $envEsc = $conn->real_escape_string($env);
    $result = $conn->query(
        'SELECT COUNT(*) AS n, MAX(RefreshedAt) AS refreshed_at, SUM(PasuramCount) AS total
         FROM ' . MATRIX_TABLE . " WHERE Environment = '{$envEsc}'"
    );
    if ($result && ($row = $result->fetch_assoc())) {
        echo "[verify {$env}] " . MATRIX_TABLE . ": cells={$row['n']}, total={$row['total']}, refreshed={$row['refreshed_at']}\n";
    }
}

if (!ensureMatrixTable($conn)) {
    http_response_code(500);
    echo 'CREATE TABLE failed: ' . $conn->error . "\n";
    exit;
}
if (!ensureLegacyMatrixTable($conn)) {
    http_response_code(500);
    echo 'CREATE legacy table failed: ' . $conn->error . "\n";
    exit;
}

$refreshedAt = date('Y-m-d H:i:s');
$legacySourceTable = null;
$legacyRows = null;

foreach ($envs as $env) {
    $pasuramTable = $MATRIX_ENVS[$env];
    $fetched = fetchAggregateRows($conn, $pasuramTable);
    if ($fetched === null) {
        echo "[{$env}] Aggregate failed: " . $conn->error . "\n";
        continue;
    }
    [$rows, $cellSum] = $fetched;

    $written = refreshEnvMatrix($conn, $env, $rows, $refreshedAt);
    echo "[{$env}] Wrote {$written} cells to " . MATRIX_TABLE . " from {$pasuramTable}; footer total {$cellSum}; at {$refreshedAt}\n";
    printVerify($conn, $env);

    if ($env === 'prod' || ($env === 'poc' && $legacySourceTable === null)) {
        $legacyRows = $rows;
        $legacySourceTable = $pasuramTable;
    }
}

if ($legacyRows !== null && $legacySourceTable !== null) {
    refreshLegacyMatrix($conn, $legacyRows, $refreshedAt, $legacySourceTable);
    $legacyVerify = $conn->query(
        'SELECT COUNT(*) AS n, MAX(RefreshedAt) AS refreshed_at, SUM(PasuramCount) AS total FROM ' . LEGACY_MATRIX_TABLE
    );
    if ($legacyVerify && ($row = $legacyVerify->fetch_assoc())) {
        echo '[verify legacy] ' . LEGACY_MATRIX_TABLE . ": cells={$row['n']}, total={$row['total']}, refreshed={$row['refreshed_at']}\n";
    }
}

echo "\nDone.\n";
echo "1) Reload divyadesam_alwar_matrix.php — grand total should be 1206, kulasekara column 82.\n";
echo "2) Upload the NEW divyadesam_alwar_matrix.php from your project so ?env=prod uses index.php (live site still has the old POC-only page).\n";

$conn->close();
