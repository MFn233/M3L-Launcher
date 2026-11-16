# tools\sign-exe.ps1
#
# 给发布出来的 exe 打代码签名。
#
# 为什么需要它：未签名的 exe 会被按"信誉"对待 —— 启动可能被 SmartScreen 拦，
# 往受保护目录写文件会被拒（我们实际遇到过 Error Code 0x5）。
#
# 两种用法：
#   1) 本机自测（免费）：-SelfSigned 生成/复用一张自签名证书，只对自己这台机器有效；
#   2) 正式分发：-Pfx <证书.pfx> -PfxPassword <密码>，用买的 OV/EV 证书签。
#
# 有 signtool.exe（Windows SDK）时会优先用它（支持 RFC3161 时间戳）；
# 没有就用系统自带的 Set-AuthenticodeSignature —— 它能签名，但不加时间戳。
#
# 例：
#   pwsh -File tools\sign-exe.ps1 -SelfSigned
#   pwsh -File tools\sign-exe.ps1 -SelfSigned -Trust
#   pwsh -File tools\sign-exe.ps1 -Pfx D:\cert\m3l.pfx -PfxPassword 123456
#   pwsh -File tools\sign-exe.ps1 -VerifyOnly

param(
	[string]$Exe = "",

	# 证书来源（二选一）
	[string]$Pfx = "",
	[string]$PfxPassword = "",
	[switch]$SelfSigned,

	# 内存里临时造一张自签名证书来签名，不碰证书存储、不落盘。
	# 用途：验证签名流程本身是否通（CI/沙箱里也能跑）；
	# 注意：这张证书没有任何可信度，对外分发没有意义。
	[switch]$Ephemeral,

	[string]$Subject = "CN=MFn, O=MFn, C=CN",

	# 把自签名证书导入"受信任的根"，本机验证会显示 Valid。
	# 只在本机自测用：等于把自己发的证书当成可信根，别在正式环境这么做。
	[switch]$Trust,

	# 自签名证书导出路径（可选，便于给别的机器信任）
	[string]$CerOut = "",

	# 时间戳服务器：正式分发必须加，否则证书过期后旧签名会失效
	[string]$Timestamp = "http://timestamp.digicert.com",
	[switch]$NoTimestamp,

	[switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot

function Write-Step($text) { Write-Host ""; Write-Host "== $text" }
function Write-Item($k, $v)  { Write-Host ("   {0,-14} {1}" -f $k, $v) }

# ---------- 找 exe ----------

if (-not $Exe) {
	# 默认签 test\ 里最新那个发布产物
	$cand = Get-ChildItem (Join-Path $repo "test") -Filter "MMMLauncher - *.exe" -File -ErrorAction SilentlyContinue |
		Sort-Object LastWriteTime -Descending | Select-Object -First 1

	if ($cand) { $Exe = $cand.FullName }
}

if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) {
	Write-Host "  [FAIL] 找不到要签名的 exe（可用 -Exe 指定）：$Exe"
	exit 1
}

$file = Get-Item -LiteralPath $Exe

Write-Host ""
Write-Step "目标"
Write-Item "file"  $file.FullName
Write-Item "size"  ("{0:N0} KB" -f ($file.Length / 1KB))
Write-Item "built" $file.LastWriteTime

# ---------- 只验证 ----------

if ($VerifyOnly) {
	$sig = Get-AuthenticodeSignature -LiteralPath $Exe
	Write-Step "签名状态"
	Write-Item "status"  $sig.Status
	Write-Item "签名者"  $(if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { "（无）" })
	Write-Item "指纹"    $(if ($sig.SignerCertificate) { $sig.SignerCertificate.Thumbprint } else { "（无）" })
	Write-Item "时间戳"  $(if ($sig.TimeStamperCertificate) { $sig.TimeStamperCertificate.Subject } else { "（无）" })

	# 退出码：0 有效 / 2 已签名但链条不受信 / 3 未签名
	if ($sig.Status -eq "Valid") { exit 0 }
	if ($sig.Status -eq "NotSigned") { exit 3 }
	exit 2
}

# ---------- 取证书 ----------

$cert = $null

if ($Pfx) {
	if (-not (Test-Path -LiteralPath $Pfx)) {
		Write-Host "  [FAIL] 证书文件不存在：$Pfx"
		exit 1
	}

	$sec = ConvertTo-SecureString $PfxPassword -AsPlainText -Force
	$cert = Get-PfxCertificate -FilePath $Pfx -Password $sec
}
elseif ($Ephemeral) {
	# 内存证书：不写证书存储，所以受限环境也能跑。
	# 必须带 Code Signing EKU，否则 Set-AuthenticodeSignature 会拒绝
	#（"指定的证书不适用于代码签名"）。
	Write-Step "生成内存证书（仅用于验证流程）"

	$rsa = [System.Security.Cryptography.RSA]::Create(2048)
	$req = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
		$Subject,
		$rsa,
		[System.Security.Cryptography.HashAlgorithmName]::SHA256,
		[System.Security.Cryptography.RSASignaturePadding]::Pkcs1)

	$req.CertificateExtensions.Add(
		[System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
			[System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature, $false))

	$oids = [System.Security.Cryptography.OidCollection]::new()
	$null = $oids.Add([System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.3"))
	$req.CertificateExtensions.Add(
		[System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($oids, $false))

	$req.CertificateExtensions.Add(
		[System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $false))

	$cert = $req.CreateSelfSigned([System.DateTimeOffset]::Now.AddDays(-1), [System.DateTimeOffset]::Now.AddYears(1))

	# 临时证书没有意义加时间戳
	$NoTimestamp = $true
}
elseif ($SelfSigned) {
	# 复用已有的自签名证书，没有才新建
	$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
		Where-Object { $_.Subject -eq $Subject } |
		Sort-Object NotAfter -Descending | Select-Object -First 1

	if (-not $cert) {
		Write-Step "新建自签名证书"
		Write-Item "subject" $Subject

		# 证书写进"当前用户的证书存储"（%APPDATA%\Microsoft\Crypto），
		# 受限环境（沙箱 / 只读用户配置）会返回 NTE_PERM，这里给出明确指引。
		try {
			$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject `
				-KeyUsage DigitalSignature -KeyExportPolicy Exportable `
				-NotAfter (Get-Date).AddYears(5)
		}
		catch {
			Write-Host "  [FAIL] 无法创建证书：$($_.Exception.Message)"
			Write-Host "         证书要写进当前用户的证书存储，受限环境（沙箱/只读配置）会被拒绝。"
			Write-Host "         请在普通桌面终端里运行；或用 -Pfx 指定已有证书。"
			exit 1
		}

		Write-Item "thumbprint" $cert.Thumbprint
	}
	else {
		Write-Step "复用已有自签名证书"
		Write-Item "thumbprint" $cert.Thumbprint
		Write-Item "到期"       $cert.NotAfter
	}

	if ($CerOut) {
		Export-Certificate -Cert $cert -FilePath $CerOut | Out-Null
		Write-Item "导出 .cer" $CerOut
	}

	if ($Trust) {
		# 导入当前用户的受信任根（本机验证才会是 Valid）
		$cer = if ($CerOut) { $CerOut } else { Join-Path $env:TEMP "m3l-selfsigned.cer" }
		Export-Certificate -Cert $cert -FilePath $cer -Force | Out-Null
		Import-Certificate -FilePath $cer -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
		Write-Item "已加入信任根" "是（当前用户）"
	}
}
else {
	$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
		Sort-Object NotAfter -Descending | Select-Object -First 1

	if (-not $cert) {
		Write-Host "  [FAIL] 当前用户没有代码签名证书。"
		Write-Host "         本机自测用 -SelfSigned；正式分发用 -Pfx + -PfxPassword。"
		exit 1
	}
}

Write-Step "证书"
Write-Item "subject"    $cert.Subject
Write-Item "thumbprint" $cert.Thumbprint
Write-Item "到期"       $cert.NotAfter

# ---------- 签名 ----------

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signtool) {
	$signtool = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
		Select-Object -First 1
}

$useTimestamp = -not $NoTimestamp

if ($signtool) {
	Write-Step "签名（signtool）"
	$exePath = if ($signtool.Source) { $signtool.Source } else { $signtool.FullName }

	# 变量名不能叫 $args：那是 PowerShell 的自动变量，赋值会直接报错
	$signArgs = @("sign", "/fd", "sha256", "/a", "/s", "My")
	if ($useTimestamp) { $signArgs += @("/tr", $Timestamp, "/td", "sha256") }
	$signArgs += $file.FullName

	& $exePath @signArgs
	if ($LASTEXITCODE -ne 0) { Write-Host "  [FAIL] signtool 返回 $LASTEXITCODE"; exit 1 }
}
else {
	Write-Step "签名（Set-AuthenticodeSignature）"
	Write-Host "   系统里没有 signtool.exe（Windows SDK），改用 PowerShell 内置接口。"
	if ($useTimestamp) {
		Write-Host "   注意：这条路径不加时间戳 —— 正式分发请装 Windows SDK 后用 signtool。"
	}
	$sig = Set-AuthenticodeSignature -LiteralPath $file.FullName -Certificate $cert -HashAlgorithm SHA256
	Write-Item "结果" $sig.Status
}

# ---------- 验证 ----------

$check = Get-AuthenticodeSignature -LiteralPath $Exe

Write-Step "验证"
Write-Item "status"  $check.Status
Write-Item "签名者"  $(if ($check.SignerCertificate) { $check.SignerCertificate.Subject } else { "（无）" })
Write-Item "时间戳"  $(if ($check.TimeStamperCertificate) { $check.TimeStamperCertificate.Subject } else { "（无）" })

if ($check.Status -eq "Valid") {
	Write-Host ""
	Write-Host "  [ OK ] 签名有效。"
	exit 0
}

# 走到这里说明"签名已写入，但不是 Valid"：自签名证书的常见结果。
#   NotTrusted   —— 链不受信
#   UnknownError —— "已处理证书链，但是在不受信任的根中终止"
# 只要文件里能取到签名证书，就是签名成功、只是不可信。
if ($check.SignerCertificate) {
	Write-Host ""
	Write-Host "  [注意] 已签名，但证书链不被信任："
	Write-Host "         $($check.Status) —— $($check.StatusMessage)"
	Write-Host "         本机看效果可加 -Trust 把自签名证书加入受信任根；"
	Write-Host "         对外分发请用买的 OV/EV 证书，并装 Windows SDK 用 signtool 加时间戳。"
	exit 2
}

Write-Host ""
Write-Host "  [FAIL] 签名状态：$($check.Status)"
if ($check.StatusMessage) { Write-Host "         $($check.StatusMessage)" }
exit 1
