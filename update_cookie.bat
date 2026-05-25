@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo --- 量科网 Cookie 更新工具 ---
echo 1. 确保已在 Edge 中登录量科网 www.qtc.com.cn
echo 2. 按任意键继续...
pause >nul
python core/extract_cookie.py
copy /Y "data\cookies\qtc_cookies.pkl" "D:\Claude_code\liangke_historical\qtc_cookies.pkl" >nul 2>&1
echo Cookie 已更新到每日抓取和历史抓取两个项目
pause
