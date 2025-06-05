@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
cls

echo ╔══════════════════════════════════════════════════════════════╗
echo ║          GitHub PR MCP Server - Otomatik Kurulum             ║
echo ║                    Claude için GitHub PR Aracı                ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Python kontrolü
echo [1/7] Python kontrol ediliyor...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python bulunamadı!
    echo.
    echo Python'u şuradan indirin: https://www.python.org/downloads/
    echo Kurulum sırasında "Add Python to PATH" seçeneğini işaretleyin!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% bulundu

:: Claude Desktop kontrolü
echo.
echo [2/7] Claude Desktop kontrol ediliyor...
if not exist "%APPDATA%\Claude" (
    echo ❌ Claude Desktop bulunamadı!
    echo.
    echo Claude Desktop'ı şuradan indirin: https://claude.ai/download
    echo Kurduktan sonra bu scripti tekrar çalıştırın.
    echo.
    pause
    exit /b 1
)
echo ✅ Claude Desktop bulundu

:: Proje klasörü oluşturma
echo.
echo [3/7] Proje klasörü oluşturuluyor...
set INSTALL_DIR=%USERPROFILE%\github-pr-mcp
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"
echo ✅ Klasör: %INSTALL_DIR%

:: Virtual environment oluşturma
echo.
echo [4/7] Python sanal ortamı oluşturuluyor...
py -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Virtual environment oluşturulamadı!
    pause
    exit /b 1
)
echo ✅ Virtual environment oluşturuldu

:: Bağımlılıkları yükleme
echo.
echo [5/7] Gerekli paketler yükleniyor...
call venv\Scripts\activate.bat

:: requirements.txt oluştur
echo mcp==0.9.1 > requirements.txt
echo httpx==0.27.0 >> requirements.txt
echo pydantic==2.5.0 >> requirements.txt

pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ❌ Paket yüklemesi başarısız!
    pause
    exit /b 1
)
echo ✅ Paketler yüklendi

:: GitHub Token alma
echo.
echo [6/7] GitHub Token Ayarları
echo ════════════════════════════════════════════════════════════════
echo.
echo GitHub Personal Access Token oluşturmak için:
echo 1. https://github.com/settings/tokens adresine gidin
echo 2. "Generate new token (classic)" tıklayın
echo 3. Şu izinleri seçin:
echo    ✓ repo (Full control)
echo    ✓ write:discussion
echo 4. Token'ı kopyalayın
echo.
echo ════════════════════════════════════════════════════════════════
echo.
set /p GITHUB_TOKEN="GitHub Token'ınızı yapıştırın (ghp_ ile başlayan): "

if "%GITHUB_TOKEN%"=="" (
    echo ❌ Token girilmedi!
    pause
    exit /b 1
)

:: Claude config dosyası oluşturma
echo.
echo [7/7] Claude yapılandırması ayarlanıyor...

:: Config dizini yoksa oluştur
if not exist "%APPDATA%\Claude" mkdir "%APPDATA%\Claude"

:: Mevcut config'i yedekle
if exist "%APPDATA%\Claude\claude_desktop_config.json" (
    copy "%APPDATA%\Claude\claude_desktop_config.json" "%APPDATA%\Claude\claude_desktop_config.backup.json" >nul
    echo 📁 Mevcut config yedeklendi
)

:: Yeni config oluştur
echo { > "%APPDATA%\Claude\claude_desktop_config.json"
echo   "mcpServers": { >> "%APPDATA%\Claude\claude_desktop_config.json"
echo     "github-pr": { >> "%APPDATA%\Claude\claude_desktop_config.json"
echo       "command": "%INSTALL_DIR:\=\\%\\venv\\Scripts\\python.exe", >> "%APPDATA%\Claude\claude_desktop_config.json"
echo       "args": ["%INSTALL_DIR:\=\\%\\github_pr_server.py"], >> "%APPDATA%\Claude\claude_desktop_config.json"
echo       "env": { >> "%APPDATA%\Claude\claude_desktop_config.json"
echo         "GITHUB_TOKEN": "%GITHUB_TOKEN%" >> "%APPDATA%\Claude\claude_desktop_config.json"
echo       } >> "%APPDATA%\Claude\claude_desktop_config.json"
echo     } >> "%APPDATA%\Claude\claude_desktop_config.json"
echo   } >> "%APPDATA%\Claude\claude_desktop_config.json"
echo } >> "%APPDATA%\Claude\claude_desktop_config.json"

echo ✅ Claude yapılandırması tamamlandı

:: Ana Python dosyasının varlığını kontrol et
if not exist "%INSTALL_DIR%\github_pr_server.py" (
    echo.
    echo ⚠️  UYARI: github_pr_server.py dosyası bulunamadı!
    echo 📁 Dosyayı şu konuma kopyalayın: %INSTALL_DIR%\github_pr_server.py
    echo.
)

:: Başarı mesajı
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🎉 KURULUM TAMAMLANDI! 🎉                  ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo ✅ Yapılması gerekenler:
echo.
echo 1. github_pr_server.py dosyasını şu konuma kopyalayın:
echo    %INSTALL_DIR%\
echo.
echo 2. Claude Desktop'ı tamamen kapatın (sistem tepsisinden de)
echo.
echo 3. Claude'u yeniden açın
echo.
echo 4. Test edin: "GitHub'daki PR'ları listele"
echo.
echo 📁 Kurulum konumu: %INSTALL_DIR%
echo 📝 Config yedek: %APPDATA%\Claude\claude_desktop_config.backup.json
echo.
pause