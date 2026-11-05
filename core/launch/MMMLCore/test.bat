@echo off
rem ---------------------------------------------------------------
rem  MMMLCore 测试脚本
rem  用法:  test.bat                     启动 1.12.2-OptiFine_G5
rem         test.bat fo                  启动 Fabulously Optimized
rem         test.bat fo --dry-run        只打印参数,不启动
rem  日志:  每次运行写一份 logs\<时间>.log
rem  前提:  先在 aardio IDE 里发布工程,生成 dist\MMMLCore.exe
rem ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "EXE=dist\MMMLCore.exe"
if not exist "%EXE%" goto no_exe

for %%F in ("%EXE%") do echo EXE timestamp: %%~tF

set "MC=C:\Users\DELL\Desktop\MMML\test\.minecraft"
set "JAVA8=C:\Users\DELL\AppData\Roaming\.minecraft\runtime\jre-legacy\bin\java.exe"
set "JAVA21=C:\Users\DELL\AppData\Roaming\.minecraft\runtime\java-runtime-delta\bin\java.exe"

if /i "%~1"=="fo" goto fo

set "VER=1.12.2-OptiFine_G5"
set "JAVA=%JAVA8%"
goto run

:fo
set "VER=Fabulously Optimized"
set "JAVA=%JAVA21%"

:run
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "STAMP="
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss" 2^>nul') do set "STAMP=%%i"
if not defined STAMP set "STAMP=run-%RANDOM%"
set "LOG=%LOGDIR%\%STAMP%.log"

echo Version : %VER%
echo Java    : %JAVA%
echo Log file: %LOG%
echo.

"%EXE%" --game-dir "%MC%" --version "%VER%" --username MFn233 --memory 4096 --java "%JAVA%" --log-file "%LOG%" %2 %3 %4 %5
set "RC=%ERRORLEVEL%"

>> "%LOG%" echo.
>> "%LOG%" echo [test.bat] exit code %RC%

echo.
echo Exit code: %RC%
echo Log file : %LOG%
pause
goto :eof

:no_exe
echo [ERROR] %EXE% not found.
echo Publish the project in the aardio IDE first.
pause
goto :eof
