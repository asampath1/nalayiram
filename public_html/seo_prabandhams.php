<?php
/**
 * Prabandham catalog for prod SEO (title / description / canonical / sitemap).
 * Keep in sync with public_html/divyaprabandham_counts_seed.json names.
 */

declare(strict_types=1);

/** @return list<array{ta: string, en: list<string>}> */
function nalayiram_prabandham_seo_catalog(): array
{
    return [
        ['ta' => 'முதல் திருவந்தாதி', 'en' => ['Mudhal Thiruvandhathi', 'First Thiruvandathi']],
        ['ta' => 'இரண்டாம் திருவந்தாதி', 'en' => ['Irandam Thiruvandhathi', 'Second Thiruvandathi']],
        ['ta' => 'மூன்றாம் திருவந்தாதி', 'en' => ['Moondram Thiruvandhathi', 'Third Thiruvandathi']],
        ['ta' => 'நான்முகன் திருவந்தாதி', 'en' => ['Nanmugan Thiruvandhathi']],
        ['ta' => 'ஸ்ரீ திருச்சந்த விருத்தம்', 'en' => ['Thiruchanda Virutham', 'Thiruchandha Virutham']],
        ['ta' => 'திருவாசிரியம்', 'en' => ['Thiruvachiriyam']],
        ['ta' => 'திருவாய்மொழி', 'en' => ['Thiruvaimozhi', 'Thiruvaymozhi']],
        ['ta' => 'திருவிருத்தம்', 'en' => ['Thiruvirutham']],
        ['ta' => 'பெரிய திருவந்தாதி', 'en' => ['Periya Thiruvandhathi']],
        ['ta' => 'கண்ணிநுண்சிறுத்தாம்பு', 'en' => ['Kanninun Siruthambu', 'Kanninunsiruthambu']],
        ['ta' => 'பெருமாள் திருமொழி', 'en' => ['Perumal Thirumozhi']],
        ['ta' => 'திருப்பல்லாண்டு', 'en' => ['Thirupallandu', 'Thiruppallandu']],
        ['ta' => 'பெரியாழ்வார் திருமொழி', 'en' => ['Periyazhwar Thirumozhi', 'Periyalwar Thirumozhi']],
        ['ta' => 'திருப்பாவை', 'en' => ['Thiruppavai', 'Thirupavai', 'Tiruppavai']],
        ['ta' => 'நாச்சியார் திருமொழி', 'en' => ['Nachiyar Thirumozhi', 'Nachchiyar Thirumozhi']],
        ['ta' => 'திருப்பள்ளியெழுச்சி', 'en' => ['Thiruppalliyezhuchi', 'Thirupalliyezhuchi']],
        ['ta' => 'திருமாலை', 'en' => ['Thirumalai']],
        ['ta' => 'அமலனாதிபிரான்', 'en' => ['Amalanadipiran', 'Amalanathi Piran']],
        ['ta' => 'சிறிய திருமடல்', 'en' => ['Siriya Thirumadal', 'Siiriya Thirumadal']],
        ['ta' => 'திரு நெடும் தாண்டகம்', 'en' => ['Thiru Nedum Thandagam', 'Nedum Thandagam']],
        ['ta' => 'திருக்குறுந்தாண்டகம்', 'en' => ['Thirukkurunthandagam', 'Kurunthandagam']],
        ['ta' => 'திருவெழுகூற்றிருக்கை', 'en' => ['Thiruvozhukootrirukkai', 'Thiruezhukootrirukkai']],
        ['ta' => 'பெரிய திருமடல்', 'en' => ['Periya Thirumadal']],
        ['ta' => 'பெரிய திருமொழி', 'en' => ['Periya Thirumozhi', 'Periya Tirumozhi']],
        ['ta' => 'இராமாநுச நூற்றந்தாதி', 'en' => ['Ramanusa Nootrandadi', 'Iramanusa Nootrandadi']],
        ['ta' => 'உபதேச ரத்னமாலை', 'en' => ['Upadesa Rathnamalai', 'Upadesa Ratnamalai']],
        ['ta' => 'திருவாய்மொழி நூற்றந்தாதி', 'en' => ['Thiruvaimozhi Nootrandadi']],
    ];
}

function nalayiram_normalize_seo_term(string $term): string
{
    $term = str_replace('+', ' ', $term);
    $term = preg_replace('/\s+/u', ' ', trim($term)) ?? '';
    return $term;
}

/**
 * @return array{ta: string, en: string, matched: string}|null
 */
function nalayiram_match_prabandham_seo(string $term): ?array
{
    $term = nalayiram_normalize_seo_term($term);
    if ($term === '') {
        return null;
    }
    $termLower = mb_strtolower($term, 'UTF-8');
    foreach (nalayiram_prabandham_seo_catalog() as $row) {
        $ta = $row['ta'];
        $enList = $row['en'];
        if ($term === $ta) {
            return ['ta' => $ta, 'en' => $enList[0] ?? $ta, 'matched' => $ta];
        }
        foreach ($enList as $en) {
            if ($termLower === mb_strtolower($en, 'UTF-8')) {
                return ['ta' => $ta, 'en' => $enList[0], 'matched' => $en];
            }
        }
    }
    return null;
}

/**
 * Resolve SEO + canonical search term from GET (padhamPrefix / prabandhamPrefix / search).
 *
 * @return array{
 *   is_prabandham: bool,
 *   ta: string,
 *   en: string,
 *   title: string,
 *   description: string,
 *   canonical: string,
 *   keywords: string,
 *   search_term: string
 * }
 */
function nalayiram_resolve_prod_seo(): array
{
    $defaultTitle = 'Nalayira Divya Prabandham PadhaArtham Search';
    $defaultDesc = 'Search Nalayira Divya Prabandham padhavurai by word, prabandham, Āzhvār, or Divya Desam.';
    $defaultCanon = 'https://nalayiram.in/';
    $keywordParts = ['நாலாயிர திவ்ய பிரபந்தம்', 'Nalayira Divya Prabandham', 'padhavurai', 'பதவுரை', 'nalayiram'];
    foreach (nalayiram_prabandham_seo_catalog() as $row) {
        $keywordParts[] = $row['ta'];
        if (!empty($row['en'][0])) {
            $keywordParts[] = $row['en'][0];
        }
    }
    $defaultKeywords = implode(', ', $keywordParts);

    $raw = '';
    if (!empty($_GET['prabandhamPrefix'])) {
        $raw = (string) $_GET['prabandhamPrefix'];
    } elseif (!empty($_GET['padhamPrefix'])) {
        $raw = (string) $_GET['padhamPrefix'];
    } elseif (!empty($_GET['search'])) {
        $raw = (string) $_GET['search'];
    }

    $match = nalayiram_match_prabandham_seo($raw);
    if ($match === null) {
        return [
            'is_prabandham' => false,
            'ta' => '',
            'en' => '',
            'title' => $defaultTitle,
            'description' => $defaultDesc,
            'canonical' => $defaultCanon,
            'keywords' => $defaultKeywords,
            'search_term' => nalayiram_normalize_seo_term($raw),
        ];
    }

    $ta = $match['ta'];
    $en = $match['en'];
    $canon = 'https://nalayiram.in/index.php?padhamPrefix=' . rawurlencode($ta);
    return [
        'is_prabandham' => true,
        'ta' => $ta,
        'en' => $en,
        'title' => "{$ta} ({$en}) — Padhavurai Search | Nalayiram",
        'description' => "Search {$ta} ({$en}) padhavurai in the Nalayira Divya Prabandham on nalayiram.in.",
        'canonical' => $canon,
        'keywords' => "{$ta}, {$en}, நாலாயிர திவ்ய பிரபந்தம், Nalayira Divya Prabandham, padhavurai, பதவுரை, nalayiram",
        'search_term' => $ta,
    ];
}
