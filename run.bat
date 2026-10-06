@echo off
title Webcast Transcriber

cd /d C:\Transcriber

echo ========================================
echo      WEBCAST TRANSCRIBER
echo ========================================
echo.

echo [1/3] Verification de Python...
python --version
if errorlevel 1 (
    echo.
    echo ERREUR : Python n'est pas accessible.
    echo Verifiez que Python est installe et dans le PATH.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] Verification des modules...
echo.

python -c "import numpy; print('OK - numpy')"
if errorlevel 1 (
    echo.
    echo Installation de numpy...
    python -m pip install numpy
)

python -c "import soundcard; print('OK - soundcard')"
if errorlevel 1 (
    echo.
    echo Installation de soundcard...
    python -m pip install soundcard
)

python -c "import faster_whisper; print('OK - faster-whisper')"
if errorlevel 1 (
    echo.
    echo Installation de faster-whisper...
    python -m pip install faster-whisper
)

echo.
echo ========================================
echo [3/3] Lancement du transcripteur...
echo ========================================
echo.

python webcast_transcriber.py

echo.
echo ========================================
echo      LE PROGRAMME EST TERMINE
echo ========================================
echo.
pause