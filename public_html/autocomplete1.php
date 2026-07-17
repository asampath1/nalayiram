<?php
include('database.php');

$query = $_GET['query'];

$sql = "SELECT DISTINCT SimilarWords FROM PasuramsArthamTableURL WHERE SimilarWords LIKE '%$query%' LIMIT 10";
$result = $conn->query($sql);

$data = array();
if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $data[] = $row['SimilarWords'];
    }
}

echo json_encode($data);

$conn->close();
?>
