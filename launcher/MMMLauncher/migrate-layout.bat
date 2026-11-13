@echo off
chcp 936 >nul
setlocal enabledelayedexpansion
title M3L 目录迁移

rem 把旧布局的运行时文件搬进 M3L\ 子目录。
rem
rem 用法：
rem   直接双击                  迁移本 bat 所在目录（放在启动器旁边就是启动器目录）
rem   migrate-layout.bat D:\M3L  指定启动器目录
rem   migrate-layout.bat --dry    只看计划，不动文件
rem
rem 规则与启动器内的自动迁移一致：只在目标不存在时搬，绝不覆盖。

set "BASE="
set "DRY="

if /i "%~1"=="--dry" (set "DRY=1") else (if not "%~1"=="" set "BASE=%~1")
if /i "%~2"=="--dry" set "DRY=1"

if not defined BASE set "BASE=%~dp0"
if "%BASE:~-1%"=="\" set "BASE=%BASE:~0,-1%"

if not exist "%BASE%\" (
	echo [错误] 目录不存在：%BASE%
	echo.
	pause
	exit /b 1
)

set "ROOT=%BASE%\M3L"

echo --------------------------------------------------
echo 启动器目录：%BASE%
echo 目标目录  ：%ROOT%
echo --------------------------------------------------
echo.

set "MODE=dry"
set "COUNT=0"
call :collect

if "%COUNT%"=="0" (
	echo 没有需要迁移的文件。
	echo.
	pause
	exit /b 0
)

echo.
if defined DRY (
	echo （--dry：只列计划，未改动任何文件）
	echo.
	pause
	exit /b 0
)

set "YES="
set /p "YES=确认执行？(y = 执行，其它 = 取消) "
if /i not "%YES%"=="y" (
	echo 已取消，未改动任何文件。
	echo.
	pause
	exit /b 0
)

echo.
set "MODE=run"
set "COUNT=0"
call :collect

echo.
echo 完成：共处理 %COUNT% 项。
echo.
pause
exit /b 0

rem ---------- 清单：改这里就同时改启动器里的 m3paths ----------

:collect
call :mv "%BASE%\config.json"         "%ROOT%\config.json"
call :mv "%BASE%\config.pending.json" "%ROOT%\config.pending.json"
call :mv "%BASE%\mod-meta-cache.json" "%ROOT%\cache\mod-meta-cache.json"
call :mv "%BASE%\mod-scan.txt"        "%ROOT%\diag\mod-scan.txt"
call :mv "%BASE%\mod-diag.txt"        "%ROOT%\diag\mod-diag.txt"
call :mv "%BASE%\authlib-injector"    "%ROOT%\authlib-injector"

rem 老版本可能把日志包放得过 exe 旁边
for %%F in ("%BASE%\m3l-logs-*.zip") do call :mv "%%~fF" "%ROOT%\logs\%%~nxF"

exit /b 0

:mv
set "SRC=%~1"
set "DST=%~2"

if not exist "%SRC%" exit /b 0

if exist "%DST%" (
	echo   跳过（新位置已有，旧文件确认无用后可删）：%SRC%
	exit /b 0
)

set /a COUNT+=1

if /i "%MODE%"=="dry" (
	echo   %SRC%
	echo       -^> %DST%
	exit /b 0
)

for %%D in ("%DST%") do set "PDIR=%%~dpD"
if not exist "%PDIR%" mkdir "%PDIR%" >nul 2>nul

move /y "%SRC%" "%DST%" >nul 2>nul
if errorlevel 1 (
	echo   失败：%SRC%
) else (
	echo   移动：%SRC%
	echo       -^> %DST%
)

exit /b 0
