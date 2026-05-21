@echo off
chcp 65001 >nul
echo ==========================================
echo   量科网 Cookie 更新工具
echo ==========================================
echo.

REM Ensure MySQL is running
netstat -an | findstr "127.0.0.1:3306" >nul
if %errorlevel% neq 0 (
    echo MySQL not running. Starting MySQL first...
    call "%~dp0start_mysql.bat" --no-pause
    timeout /t 3 /nobreak >nul
)

echo Please make sure you have logged in to
echo http://www.qtc.com.cn in Edge browser.
echo.
pause

echo Extracting cookies...
python "%~dp0..\core\extract_cookie.py"

if %errorlevel% equ 0 (
    echo.
    echo Cookie updated successfully!
    echo Next daily scrape will use the new cookies.
) else (
    echo.
    echo Failed to update cookies. Please check if Edge is running.
)

pause
