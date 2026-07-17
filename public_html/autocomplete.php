<?php
include('database.php');

$query = $_GET['query'];
$query = strtolower($query); // Ensure the query is lowercase for comparison

$sql = "SELECT distinct Word FROM SuggestedWords WHERE LOWER(Word) LIKE '$query%' ORDER By Word ASC LIMIT 50";
$result = $conn->query($sql);

$data = array();
if ($result->num_rows > 0) {
    while ($row = $result->fetch_assoc()) {
        $data[] = $row['Word'];
    }
}

echo json_encode($data);

$conn->close();
?>
