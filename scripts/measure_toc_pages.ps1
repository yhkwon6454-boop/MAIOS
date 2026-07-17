# Measure book page numbers for the contents page (pass 2 of build_book.py).
# Opens docs/MAIOS_책_v1.docx read-only via Word COM, finds each search key
# from build_book.py TOC_ENTRIES, and writes docs/figures/toc_pages.json.
# Rule: take the first occurrence NOT on the contents page itself
# (TOC display text may contain the key).

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$docPath = Join-Path $root "docs\MAIOS_책_v1.docx"
$outPath = Join-Path $root "docs\figures\toc_pages.json"

$keys = @(
    "이 책은 하나의 질문에서 시작되었다",
    "설치부터 온톨로지 결합까지",
    "MAIOS란 무엇인가",
    "명령어 상세",
    "워크스페이스의 구조",
    "파이썬 API",
    "기억·회상·거버넌스를 갖춘 임무 중심 인지형",
    "문제 제기",
    "구현과 검증 방법론",
    "접합 설계",
    "실모델 미검증",
    "대화형 공동개발의 기록"
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docPath, $false, $true)

function Get-OccurrencePages($doc, $text) {
    $pages = @()
    $range = $doc.Content
    $range.Find.ClearFormatting()
    while ($range.Find.Execute($text)) {
        $pages += [int]$range.Information(3)  # wdActiveEndPageNumber
        $null = $range.Collapse(0)            # wdCollapseEnd
    }
    return ,$pages
}

$tocPages = Get-OccurrencePages $doc "차례"
$tocPage = if ($tocPages.Count -gt 0) { $tocPages[0] } else { -1 }

$result = @{}
foreach ($key in $keys) {
    $pages = Get-OccurrencePages $doc $key
    $hit = $null
    foreach ($p in $pages) {
        if ($p -ne $tocPage) { $hit = $p; break }
    }
    if ($null -ne $hit) { $result[$key] = $hit }
    Write-Host "$key -> $hit (candidates: $($pages -join ','), toc: $tocPage)"
}

$doc.Close($false)
$word.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null

$json = ($result.GetEnumerator() | Sort-Object Name | ForEach-Object {
    '  "{0}": {1}' -f $_.Name, $_.Value
}) -join ",`n"
$json = "{`n$json`n}"
[System.IO.File]::WriteAllText($outPath, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "written: $outPath"
