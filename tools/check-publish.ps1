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
Write-Host "  --- version (project property vs lib/m3app.aardio) ---"
# 版本号有两处：工程属性 FileVersion（四段）与 m3app.aardio 的 VERSION（前三位）。
# 两者对不上时，关于页在 F5 与发布版里会显示不同的数字，所以这里提示一句。
$aprojPath = Join-Path $root "launcher\MMMLauncher\default.aproj"
$m3appPath = Join-Path $root "launcher\MMMLauncher\lib\m3app.aardio"
$verWarn = 0

$projVer = $null
if (Test-Path $aprojPath) {
	$aprojText = Get-Content $aprojPath -Raw -Encoding UTF8
	if ($aprojText -match 'FileVersion="([^"]+)"') { $projVer = $matches[1] }
}

$m3appVer = $null
if (Test-Path $m3appPath) {
	$m3appText = Get-Content $m3appPath -Raw -Encoding UTF8
	if ($m3appText -match 'VERSION\s*=\s*"([^"]+)"') { $m3appVer = $matches[1] }
}

$exeVer = $file.VersionInfo.FileVersion

Write-Host "    aproj FileVersion : $projVer"
Write-Host "    m3app VERSION     : $m3appVer"
Write-Host "    exe  FileVersion  : $exeVer"

if ($projVer -and $m3appVer) {
	$projShort = ($projVer -split '\.')[0..2] -join '.'
	if ($projShort -ne $m3appVer) {
		Write-Host "    [WARN] first three segments differ: aproj=$projShort m3app=$m3appVer"
		$verWarn = 1
	} else {
		Write-Host "    [ OK ] first three segments match ($projShort)"
	}
} else {
	Write-Host "    [WARN] could not read one of them"
	$verWarn = 1
}

Write-Host ""
if ($missing -eq 0) {
	Write-Host "  RESULT: OK - this EXE carries every library and dialog."
	if ($verWarn -ne 0) {
		Write-Host "          (version numbers need attention, see [WARN] above)"
	}
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
