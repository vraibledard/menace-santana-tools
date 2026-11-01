:: Copyright (c) MENACE SANTANA by vraibledard
:: Licensed under the MIT License.
@echo off
title MENACE SANTANA
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [!] Python est introuvable.
    echo     Installe-le depuis https://www.python.org/downloads/
    echo     et coche "Add Python to PATH" pendant l'installation.
    pause
    exit /b 1
)

%PY% install_deps.py
if errorlevel 1 (
    echo [!] Impossible d'installer les dependances.
    pause
    exit /b 1
)

%PY% main.py %*
if errorlevel 1 pause
