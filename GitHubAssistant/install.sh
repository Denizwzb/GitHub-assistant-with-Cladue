#!/bin/bash

# Renkli çıktılar için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

clear

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          GitHub PR MCP Server - Otomatik Kurulum             ║"
echo "║                    Claude için GitHub PR Aracı                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo

# İşletim sistemi tespiti
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
else
    OS="Linux"
    CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
fi

echo "İşletim Sistemi: $OS"
echo

# Python kontrolü
echo "[1/7] Python kontrol ediliyor..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d" " -f2)
    echo -e "${GREEN}✅ Python $PYTHON_VERSION bulundu${NC}"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | cut -d" " -f2)
    echo -e "${GREEN}✅ Python $PYTHON_VERSION bulundu${NC}"
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python bulunamadı!${NC}"
    echo
    echo "Python'u kurmak için:"
    if [[ "$OS" == "macOS" ]]; then
        echo "  brew install python3"
    else
        echo "  sudo apt-get install python3 python3-pip"
    fi
    exit 1
fi

# pip kontrolü
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${RED}❌ pip bulunamadı!${NC}"
    exit 1
fi

# Claude Desktop kontrolü
echo
echo "[2/7] Claude Desktop kontrol ediliyor..."
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${RED}❌ Claude Desktop bulunamadı!${NC}"
    echo
    echo "Claude Desktop'ı şuradan indirin: https://claude.ai/download"
    echo "Kurduktan sonra bu scripti tekrar çalıştırın."
    exit 1
fi
echo -e "${GREEN}✅ Claude Desktop bulundu${NC}"

# Proje klasörü oluşturma
echo
echo "[3/7] Proje klasörü oluşturuluyor..."
INSTALL_DIR="$HOME/github-pr-mcp"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo -e "${GREEN}✅ Klasör: $INSTALL_DIR${NC}"

# Virtual environment oluşturma
echo
echo "[4/7] Python sanal ortamı oluşturuluyor..."
$PYTHON_CMD -m venv venv
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Virtual environment oluşturulamadı!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Virtual environment oluşturuldu${NC}"

# Virtual environment'ı aktifle
source venv/bin/activate

# Bağımlılıkları yükleme
echo
echo "[5/7] Gerekli paketler yükleniyor..."

# requirements.txt oluştur
cat > requirements.txt << EOF
mcp==0.9.1
httpx==0.27.0
pydantic==2.5.0
EOF

pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Paket yüklemesi başarısız!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Paketler yüklendi${NC}"

# GitHub Token alma
echo
echo "[6/7] GitHub Token Ayarları"
echo "════════════════════════════════════════════════════════════════"
echo
echo "GitHub Personal Access Token oluşturmak için:"
echo "1. https://github.com/settings/tokens adresine gidin"
echo "2. \"Generate new token (classic)\" tıklayın"
echo "3. Şu izinleri seçin:"
echo "   ✓ repo (Full control)"
echo "   ✓ write:discussion"
echo "4. Token'ı kopyalayın"
echo
echo "════════════════════════════════════════════════════════════════"
echo
read -p "GitHub Token'ınızı yapıştırın (ghp_ ile başlayan): " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ Token girilmedi!${NC}"
    exit 1
fi

# Claude config dosyası oluşturma
echo
echo "[7/7] Claude yapılandırması ayarlanıyor..."

# Config dizini yoksa oluştur
mkdir -p "$CLAUDE_CONFIG_DIR"

# Mevcut config'i yedekle
if [ -f "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" ]; then
    cp "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" "$CLAUDE_CONFIG_DIR/claude_desktop_config.backup.json"
    echo "📁 Mevcut config yedeklendi"
fi

# Yeni config oluştur
cat > "$CLAUDE_CONFIG_DIR/claude_desktop_config.json" << EOF
{
  "mcpServers": {
    "github-pr": {
      "command": "$INSTALL_DIR/venv/bin/python",
      "args": ["$INSTALL_DIR/github_pr_server.py"],
      "env": {
        "GITHUB_TOKEN": "$GITHUB_TOKEN"
      }
    }
  }
}
EOF

echo -e "${GREEN}✅ Claude yapılandırması tamamlandı${NC}"

# Ana Python dosyasının varlığını kontrol et
if [ ! -f "$INSTALL_DIR/github_pr_server.py" ]; then
    echo
    echo -e "${YELLOW}⚠️  UYARI: github_pr_server.py dosyası bulunamadı!${NC}"
    echo "📁 Dosyayı şu konuma kopyalayın: $INSTALL_DIR/github_pr_server.py"
    echo
fi

# Başarı mesajı
echo
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 KURULUM TAMAMLANDI! 🎉                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo
echo -e "${GREEN}✅ Yapılması gerekenler:${NC}"
echo
echo "1. github_pr_server.py dosyasını şu konuma kopyalayın:"
echo "   $INSTALL_DIR/"
echo
echo "2. Claude Desktop'ı tamamen kapatın"
echo
echo "3. Claude'u yeniden açın"
echo
echo "4. Test edin: \"GitHub'daki PR'ları listele\""
echo
echo "📁 Kurulum konumu: $INSTALL_DIR"
echo "📝 Config yedek: $CLAUDE_CONFIG_DIR/claude_desktop_config.backup.json"
echo

# Script'i çalıştırılabilir yap
chmod +x "$0"