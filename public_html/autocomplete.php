<?php
include('database.php');

$query = isset($_GET['query']) ? $_GET['query'] : '';
$query = mysqli_real_escape_string($conn, strtolower($query));

$sql = "SELECT DISTINCT Word FROM SuggestedWords WHERE LOWER(Word) LIKE ? ORDER BY Word ASC LIMIT 50";
$stmt = $conn->prepare($sql);
$like = $query . '%';
$stmt->bind_param('s', $like);
$stmt->execute();
$result = $stmt->get_result();

$data = array();
while ($row = $result->fetch_assoc()) {
    $data[] = $row['Word'];
}

echo json_encode($data);

$stmt->close();
$conn->close();
?>
