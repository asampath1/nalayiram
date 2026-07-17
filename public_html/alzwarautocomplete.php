<?php
if (isset($_GET['query'])) {
    $query = $_GET['query'];

    // Array of fixed values

    $alwars =             [
            "Nammalwar-நம்மாழ்வார்",
            "Madhurakavi Alwar-மதுரகவியாழ்வார்",
            "Periyalwar-பெரியாழ்வார்",
            "Andal-ஆண்டாள்",
            "Thondaradpipodi Alwar-தொண்டரடிப்பொடிஆழ்வார்",
            "Thiruppan Alwar-திருப்பாண் ஆழ்வார்",
            "Thirumangai Alwar-திருமங்கையாழ்வார்",
            "Poigai Alwar-பொய்கையாழ்வார்",
            "Boothathalwar-பூதத்தாழ்வார்",
            "Peyalwar-பேயாழ்வார்",
            "Thirumazhisai Alwar-திருமழிசையாழ்வார்",
            "Kulasekara Alwar-குலசேகர ஆழ்வார்",
            "Nadamuni -நாதமுனி"
    ];

    // Filter the results
    $result = array_filter($alwars, function($alwar) use ($query) {
        return stripos($alwar, $query) !== false;
    });

    // Return the results as a JSON array
    echo json_encode(array_values($result));
}
?>
