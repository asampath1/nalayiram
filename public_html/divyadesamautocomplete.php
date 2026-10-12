<?php
if (isset($_GET['query'])) {
    $query = $_GET['query'];

    require_once __DIR__ . '/includes/divyadesam_regions_poc.php';
    $divyadesams = divyadesam_poc_flat_list();

    // Filter the results
    $result = array_filter($divyadesams, function($divyadesam) use ($query) {
        return stripos($divyadesam, $query) !== false;
    });

    // Return the results as a JSON array
    echo json_encode(array_values($result));
}
?>
