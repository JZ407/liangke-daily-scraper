@echo off
chcp 65001 >nul
echo ==========================================
echo   MySQL 8.4 Server Launcher
echo ==========================================
echo.

set "SCRIPT_DIR=%~dp0"

REM Check if MySQL is already running
netstat -an | findstr "127.0.0.1:3306" >nul
if %errorlevel% equ 0 (
    echo MySQL is already running on port 3306.
    goto :done
)

REM Auto-detect MySQL installation
set "MYSQLD="
if exist "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" (
    set "MYSQLD=C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
) else if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" (
    set "MYSQLD=C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe"
)

if "%MYSQLD%"=="" (
    echo ERROR: MySQL not found. Please install MySQL 8.x first.
    pause
    exit /b 1
)

echo Starting MySQL server...
start "" "%MYSQLD%" --defaults-file="%SCRIPT_DIR%my.ini" --console

echo Waiting for MySQL to start...
:wait_loop
timeout /t 2 /nobreak >nul
netstat -an | findstr "127.0.0.1:3306" >nul
if %errorlevel% neq 0 goto :wait_loop

echo MySQL started successfully on port 3306.

:done
echo.
echo You can now run run_daily.bat to scrape news.
pause
