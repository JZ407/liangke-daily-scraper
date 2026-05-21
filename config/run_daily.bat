@echo off
chcp 65001 >nul
echo ==========================================
echo   量科网每日新闻抓取工具
echo ==========================================
echo.

REM Step 1: Ensure MySQL is running
echo [1/3] Checking MySQL...
netstat -an | findstr "127.0.0.1:3306" >nul
if %errorlevel% neq 0 (
    echo MySQL not running. Starting MySQL first...
    call "%~dp0start_mysql.bat" --no-pause
    timeout /t 3 /nobreak >nul
)

REM Step 2: Extract latest cookies from Edge (if logged in)
echo.
echo [2/3] Extracting cookies from Edge...
python "%~dp0..\core\extract_cookie.py"
if %errorlevel% neq 0 (
    echo WARNING: Cookie extraction failed. Will try using existing cookies.
)

REM Step 3: Run daily scrape
echo.
echo [3/3] Scraping today's news...
python "%~dp0..\core\scrape_daily.py"

echo.
echo ==========================================
echo Done! Press any key to exit.
pause >nul
