param(
	[string]$Exe = ""
)

# check-publish.ps1
# Check whether a published EXE actually contains the resources it needs.
#
# Why this exists: with libEmbed="true" aardio compiles the imported libraries
# into the EXE as PE resources (type "LIB", name = uppercase namespace), and
# embeds dialog sources as "DLG/NAME.AARDIO". If the publish step skips either,
# the EXE still starts on the dev machine (it can fall back to the local
# aardio install) but fails on everyone else's machine.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\check-publish.ps1
#   powershell -ExecutionPolicy Bypass -File tools\check-publish.ps1 -Exe "path\to\app.exe"
#
# Output is ASCII on purpose: the console code page is GBK on most machines,
# so Chinese text in batch/PowerShell output tends to turn into garbage.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
if (-not $Exe) {
	$Exe = Join-Path $root "launcher\MMMLauncher\dist\MMMLauncher.exe"
}

if (-not (Test-Path $Exe)) {
	Write-Host "  [FAIL] not found: $Exe"
	exit 1
}

$file = Get-Item $Exe
Write-Host ""
Write-Host "  file : $($file.Name)"
Write-Host "  size : $([math]::Round($file.Length/1KB)) KB"
Write-Host "  built: $($file.LastWriteTime)"
Write-Host ""

$bytes = [System.IO.File]::ReadAllBytes($Exe)
$utf16 = [System.Text.Encoding]::Unicode.GetString($bytes)

# Names that must be inside the EXE.
# 1. project libraries: every lib\*.aardio -> uppercase basename
# 2. the shared user library MMMLC (lives in the repo, deployed to aardio user lib)
# 3. dialogs: every dlg\*.aardio -> DLG\NAME.AARDIO
$libDir = Join-Path $root "launcher\MMMLauncher\lib"
$dlgDir = Join-Path $root "launcher\MMMLauncher\dlg"

$libs = @("MMMLC")
if (Test-Path $libDir) {
	Get-ChildItem $libDir -Filter *.aardio | ForEach-Object {
		$libs += $_.BaseName.ToUpper()
	}
}
$libs = $libs | Sort-Object -Unique

$dlgs = @()
if (Test-Path $dlgDir) {
	Get-ChildItem $dlgDir -Filter *.aardio | ForEach-Object {
		$dlgs += "DLG/" + $_.BaseName.ToUpper() + ".AARDIO"
	}
	$dlgs = $dlgs | Sort-Object -Unique
}

$missing = 0

Write-Host "  --- libraries (embedded as PE resource type LIB) ---"
foreach ($name in $libs) {
	if ($utf16.Contains($name)) {
		Write-Host "    [ OK ] $name"
	} else {
		Write-Host "    [MISS] $name"
		$missing++
	}
}

Write-Host ""
Write-Host "  --- dialogs (embedded as DLG/NAME.AARDIO) ---"
foreach ($name in $dlgs) {
	if ($utf16.Contains($name)) {
		Write-Host "    [ OK ] $name"
	} else {
		Write-Host "    [MISS] $name"
		$missing++
	}
}

Write-Host ""
if ($missing -eq 0) {
	Write-Host "  RESULT: OK - this EXE carries every library and dialog."
	exit 0
} else {
	Write-Host "  RESULT: FAIL - $missing item(s) missing."
	Write-Host ""
	Write-Host "  Common causes:"
	Write-Host "   1. published with the 'embed libraries' option off (project property libEmbed)"
	Write-Host "   2. a dlg\*.aardio was added but never 'synced to local directory' in the IDE"
	Write-Host "   3. the file inspected is an older build, or the publish output went elsewhere"
	exit 2
}
