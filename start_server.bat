@echo off
echo ==========================================
echo       Phishing Detection Server
echo ==========================================

echo [1/2] Checking dependencies...
pip install -r requirements.txt

echo.
echo [2/2] Starting Server...
echo Service will listen on http://127.0.0.1:5000
echo.

python server.py

pause
