@echo off
title Blood Bank Management System - Public Live Server
cls
echo ========================================================
echo   Starting Blood Bank Management System (Docker Compose)
echo ========================================================
echo.
docker compose up -d
echo.
echo ========================================================
echo   Launching Public Secure Tunnel with QR Code
echo ========================================================
echo.
python tunnel_launcher.py
pause
