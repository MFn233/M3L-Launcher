@echo off
rem Deploy the authoritative MMM-C source into the aardio user lib directory.
rem
rem Both projects (core\launch\MMMLCore and launcher\MMMLauncher) do `import MMMLC`,
rem which loads the copy in the aardio user lib folder. After editing
rem core\launch\MMMLC.aardio you must run this script, or the IDE keeps using old code.
rem
rem DST is machine specific: change it if aardio lives elsewhere.

setlocal
set SRC=%~dp0..\core\launch\MMMLC.aardio
set DST=D:\Develop\aardio\lib\MMMLC.aardio

if not exist "%SRC%" (
    echo [ERROR] source not found: %SRC%
    exit /b 1
)

if not exist "D:\Develop\aardio\lib" (
    echo [ERROR] aardio user lib dir not found: D:\Develop\aardio\lib
    exit /b 1
)

copy /y "%SRC%" "%DST%" >nul
if errorlevel 1 (
    echo [ERROR] copy failed: %DST%
    exit /b 1
)

echo deployed: %DST%
