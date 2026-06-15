@echo off
chcp 65001 >nul
title تشغيل موقع مركز اي تي
cd /d "%~dp0"
echo ====================================
echo   جاري تشغيل الموقع... لا تغلق هذه النافذة
echo   العنوان: http://127.0.0.1:8000/
echo ====================================
start "" http://127.0.0.1:8000/
"C:\ProgramData\anaconda3\envs\database\python.exe" manage.py runserver
pause
