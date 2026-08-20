# Claim guard hook -- blocks unverified/refuted claims from being written as fact.
#
# Wired as PreToolUse(Write|Edit). Compares the pending content against
# claims.json and exits 2 with an explanation when a refuted claim, or an
# unverified hypothesis stated as fact, would be saved.
#
# Exemption: if any line within +/-3 lines of the match contains the rule's
# "exempt" pattern, it passes. Documents that record a retraction must not
# be blocked by the very claim they retract.
#
# THIS FILE MUST STAY PURE ASCII.
# PowerShell 5.1 reads a BOM-less .ps1 as ANSI, which mangles every Korean
# identifier and string literal into parse errors. All Korean text lives in
# claims.json, which is read as explicit UTF-8 bytes below.

$ErrorActionPreference = 'Stop'

function Write-Err([string]$msg) {
  $s = [Console]::OpenStandardError()
  $b = [System.Text.Encoding]::UTF8.GetBytes($msg)
  $s.Write($b, 0, $b.Length)
  $s.Flush()
}

try {
  $si = [Console]::OpenStandardInput()
  $ms = New-Object System.IO.MemoryStream
  $si.CopyTo($ms)
  $raw = [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
} catch { exit 0 }

if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
try { $j = $raw | ConvertFrom-Json } catch { exit 0 }

$tool = [string]$j.tool_name
if ($tool -ne 'Write' -and $tool -ne 'Edit') { exit 0 }

$path = [string]$j.tool_input.file_path
# Never inspect the ledger or this script: they quote the banned strings by design.
if ($path -match 'claims\.json|claim-guard\.ps1') { exit 0 }

if ($tool -eq 'Write') { $content = [string]$j.tool_input.content }
else                   { $content = [string]$j.tool_input.new_string }
if ([string]::IsNullOrWhiteSpace($content)) { exit 0 }

$rulesPath = Join-Path $PSScriptRoot 'claims.json'
if (-not (Test-Path $rulesPath)) { exit 0 }
try {
  $bytes = [System.IO.File]::ReadAllBytes($rulesPath)
  $doc = [System.Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json
} catch { exit 0 }

$labels = $doc.labels
$msg = $doc.messages
[string[]]$lines = $content -split "`r?`n"
$hits = @()

foreach ($rule in $doc.claims) {
  if ($rule.status -eq 'verified') { continue }
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -notmatch $rule.pattern) { continue }
    $lo = [Math]::Max(0, $i - 3)
    $hi = [Math]::Min($lines.Count - 1, $i + 3)
    $window = ($lines[$lo..$hi]) -join "`n"
    if ($rule.exempt -and $window -match $rule.exempt) { continue }
    $hits += [PSCustomObject]@{ Rule = $rule; Line = $i + 1; Text = $lines[$i].Trim() }
    break
  }
}

if ($hits.Count -eq 0) { exit 0 }

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine($msg.header + $path)
[void]$sb.AppendLine('')
foreach ($h in $hits) {
  $r = $h.Rule
  $label = $labels.($r.status)
  if (-not $label) { $label = '[' + $r.status + ']' }
  $snippet = $h.Text
  if ($snippet.Length -gt 90) { $snippet = $snippet.Substring(0, 90) + '...' }
  [void]$sb.AppendLine($label + ' ' + $r.id + '  (line ' + $h.Line + ')')
  [void]$sb.AppendLine($msg.at_line + $snippet)
  [void]$sb.AppendLine($msg.why + $r.why)
  [void]$sb.AppendLine($msg.instead + $r.instead)
  if ($r.source) { [void]$sb.AppendLine($msg.source + $r.source) }
  [void]$sb.AppendLine('')
}
[void]$sb.AppendLine($msg.footer)

Write-Err $sb.ToString()
exit 2
