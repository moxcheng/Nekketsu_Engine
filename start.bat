@echo off
:: 切換到 .bat 檔案所在的資料夾
cd /d "%~dp0"

:: 啟動 PowerShell 並執行 Python 指令
powershell -NoExit -Command "python .\main.py"