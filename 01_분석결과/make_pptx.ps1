# 캡스톤_발표덱.html → 캡스톤_발표덱.pptx 생성 (PowerPoint COM)
# 사용법: powershell -File make_pptx.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$html = Join-Path $here "캡스톤_발표덱.html"
$pptx = Join-Path $here "캡스톤_발표덱.pptx"

# ── 무드보드 팔레트 (BGR 정수 — PowerPoint COM은 RGB 역순) ──
function C([int]$r,[int]$g,[int]$b){ return $b*65536 + $g*256 + $r }
$BASALT  = C 31 38 35     # #1F2623
$DEEP    = C 36 56 44     # #24382C
$FOREST  = C 59 93 72     # #3B5D48
$SAGE    = C 159 184 154  # #9FB89A
$STONE   = C 232 226 214  # #E8E2D6
$OFFWH   = C 250 250 247  # #FAFAF7
$INK     = C 34 36 31     # #22241F
$CAMEL   = C 142 74 82    # #8E4A52

# ── HTML에서 슬라이드 텍스트 추출 ──
$raw = Get-Content $html -Raw -Encoding UTF8
$secs = [regex]::Matches($raw, '(?s)<section class="slide([^"]*)">(.*?)</section>')

function Clean([string]$s){
  $s = $s -replace '(?s)<svg.*?</svg>', ''
  $s = $s -replace '<br\s*/?>', "`n"
  $s = $s -replace '</(p|div|h1|h2|h3|tr|li)>', "`n"
  $s = $s -replace '</t[dh]>', "  |  "
  $s = $s -replace '<[^>]+>', ''
  $s = $s -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&lt;', '<' -replace '&gt;', '>'
  # PowerPoint는 문단 구분자로 CR(`r)을 쓴다. LF를 넣으면 텍스트가 잘린다.
  $s = ($s -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }) -join "`r"
  return $s
}

$app = New-Object -ComObject PowerPoint.Application
try {
  $pres = $app.Presentations.Add($false)     # 화면에 안 띄움
  $pres.PageSetup.SlideSize = 3              # ppSlideSizeCustom
  $pres.PageSetup.SlideWidth  = 960          # 16:9 (pt)
  $pres.PageSetup.SlideHeight = 540

  $n = 0
  foreach ($m in $secs) {
    $cls  = $m.Groups[1].Value
    $body = $m.Groups[2].Value
    $n++

    $dark   = $cls -match 'dark|deep'
    $eyeb   = ([regex]::Match($body, '(?s)<div class="eyebrow">(.*?)</div>')).Groups[1].Value
    $head   = ([regex]::Match($body, '(?s)<(h1|h2)[^>]*>(.*?)</\1>')).Groups[2].Value
    $quote  = ([regex]::Match($body, '(?s)<div class="quote">(.*?)</div>')).Groups[1].Value
    $mark   = ([regex]::Match($body, '(?s)<div class="backup-mark">(.*?)</div>')).Groups[1].Value

    $titleSrc = if ($head) { $head } else { $quote }
    $title = Clean $titleSrc
    $eyeb  = Clean $eyeb
    $mark  = Clean $mark

    # 본문 = 헤드라인·눈썹·풋터 제외한 나머지
    $rest = $body
    $rest = $rest -replace '(?s)<div class="eyebrow">.*?</div>', ''
    $rest = $rest -replace '(?s)<(h1|h2)[^>]*>.*?</\1>', ''
    $rest = $rest -replace '(?s)<div class="quote">.*?</div>', ''
    $rest = $rest -replace '(?s)<div class="foot">.*?</div>', ''
    $rest = $rest -replace '(?s)<div class="backup-mark">.*?</div>', ''
    $rest = Clean $rest

    $slide = $pres.Slides.Add($n, 12)        # ppLayoutBlank
    $slide.FollowMasterBackground = $false
    $slide.Background.Fill.ForeColor.RGB = $(if ($dark) { if ($cls -match 'deep') { $DEEP } else { $BASALT } } else { $OFFWH })
    $slide.Background.Fill.Solid()

    $fgTitle = $(if ($dark) { $STONE } else { $INK })
    $fgEye   = $(if ($dark) { $SAGE }  else { $FOREST })
    $fgBody  = $(if ($dark) { $STONE } else { $INK })

    # 눈썹
    if ($eyeb) {
      $tb = $slide.Shapes.AddTextbox(1, 58, 46, 844, 24)
      $tf = $tb.TextFrame.TextRange
      $tf.Text = $eyeb
      $tf.Font.Name = "맑은 고딕"; $tf.Font.Size = 12; $tf.Font.Bold = $true
      $tf.Font.Color.RGB = $fgEye
      $tb.TextFrame.WordWrap = $false
    }
    # 백업 표시
    if ($mark) {
      $tb = $slide.Shapes.AddTextbox(1, 700, 46, 202, 24)
      $tf = $tb.TextFrame.TextRange
      $tf.Text = $mark
      $tf.Font.Name = "맑은 고딕"; $tf.Font.Size = 11; $tf.Font.Bold = $true
      $tf.Font.Color.RGB = $CAMEL
      $tf.ParagraphFormat.Alignment = 3   # right
    }
    # 헤드라인
    if ($title) {
      $tb = $slide.Shapes.AddTextbox(1, 58, 86, 844, 120)
      $tf = $tb.TextFrame.TextRange
      $tf.Text = $title
      $tf.Font.Name = "맑은 고딕"
      $tf.Font.Size = $(if ($n -eq 1) { 40 } else { 30 })
      $tf.Font.Bold = $true
      $tf.Font.Color.RGB = $fgTitle
      $tb.TextFrame.WordWrap = $true
    }
    # 본문
    if ($rest) {
      $tb = $slide.Shapes.AddTextbox(1, 58, 216, 844, 280)
      $tf = $tb.TextFrame.TextRange
      $tf.Text = $rest
      $tf.Font.Name = "맑은 고딕"; $tf.Font.Size = 13
      $tf.Font.Color.RGB = $fgBody
      $tb.TextFrame.WordWrap = $true
      $tf.ParagraphFormat.SpaceWithin = 1.15
    }
    # 페이지 번호
    $tb = $slide.Shapes.AddTextbox(1, 860, 500, 60, 20)
    $tf = $tb.TextFrame.TextRange
    $tf.Text = "$n"
    $tf.Font.Name = "맑은 고딕"; $tf.Font.Size = 10
    $tf.Font.Color.RGB = $(if ($dark) { $SAGE } else { $FOREST })
    $tf.ParagraphFormat.Alignment = 3
  }

  if (Test-Path $pptx) { Remove-Item $pptx -Force }
  $pres.SaveAs($pptx)
  $pres.Close()
  Write-Host "생성 완료: $n 장 · $([math]::Round((Get-Item $pptx).Length/1KB)) KB"
  Write-Host "→ $pptx"
} catch {
  Write-Host "실패: $($_.Exception.Message)"
} finally {
  $app.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
