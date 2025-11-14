@echo off
chcp 65001 >nul
title ДУРОВ БОТ - Запуск
echo ===============================
echo    ЗАПУСК ДУРОВ БОТ
echo ===============================
echo.

cd /d "C:\Users\user\Desktop\ДУРОВ БОТ"

echo Проверка наличия Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не установлен или не добавлен в PATH
    echo Установите Python с официального сайта: https://python.org
    pause
    exit
)

echo Проверка зависимостей...
pip install python-telegram-bot >nul 2>&1

echo.
echo Запуск бота...
echo ===============================
python bot.py

if errorlevel 1 (
    echo.
    echo ОШИБКА: Не удалось запустить бота
    echo Проверьте:
    echo 1. Наличие файла bot.py в папке
    echo 2. Правильность токена бота
    echo 3. Установлены ли зависимости
    echo.
    pause
)