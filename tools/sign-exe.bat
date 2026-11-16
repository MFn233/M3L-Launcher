@echo off
chcp 936 >nul
rem tools\sign-exe.bat
rem
rem 双击 = 用自签名证书签 test\ 里最新那个 exe（本机有效）
rem 也可以传参数，例如：
rem   sign-exe.bat -Pfx D:\cert\m3l.pfx -PfxPassword 123456
rem   sign-exe.bat -VerifyOnly
rem   sign-exe.bat -Ephemeral            （只验证签名流程本身）

setlocal
set "ARGS=%*"

if "%ARGS%"=="" (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0sign-exe.ps1" -SelfSigned
) else (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0sign-exe.ps1" %*
)

echo.
pause
