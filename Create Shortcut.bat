@echo off
:: Run this ONCE to create a desktop shortcut that works from anywhere
setlocal enabledelayedexpansion

set "APP_DIR=%~dp0"
set "VBS=%TEMP%\make_shortcut.vbs"

:: Find pythonw executable (runs without console window)
for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do set "PYTHON_PATH=%%i"

:: Fallback to python.exe if pythonw not found
if not defined PYTHON_PATH (
    for /f "delims=" %%i in ('where python.exe 2^>nul') do set "PYTHON_PATH=%%i"
)

if not defined PYTHON_PATH (
    echo Error: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

:: Create shortcut on Desktop (handles OneDrive Desktop correctly)
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS%"
echo Set objShell = CreateObject("Shell.Application") >> "%VBS%"
echo Set objDesktop = objShell.NameSpace(0) >> "%VBS%"
echo sLinkFile = objDesktop.Self.Path ^& "\PranshulOS.lnk" >> "%VBS%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS%"
echo oLink.TargetPath = "%PYTHON_PATH%" >> "%VBS%"
echo oLink.Arguments = """%APP_DIR%main.py""" >> "%VBS%"
echo oLink.WorkingDirectory = "%APP_DIR%" >> "%VBS%"
echo oLink.Description = "PranshulOS" >> "%VBS%"
echo oLink.WindowStyle = 0 >> "%VBS%"
echo oLink.IconLocation = "%APP_DIR%main.py" >> "%VBS%"
echo oLink.Save >> "%VBS%"

cscript //nologo "%VBS%"
if %errorlevel% equ 0 (
    del "%VBS%"
    echo.
    echo Success! PranshulOS shortcut created on your Desktop.
    echo You can now launch the app from anywhere by double-clicking it.
) else (
    echo.
    echo Error creating shortcut. Make sure you run this as Administrator.
    del "%VBS%"
)
pause
