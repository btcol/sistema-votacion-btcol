#!/bin/bash
# Setup Script - LNBits Dashboard v3.0
# Ejecutar: bash setup.sh

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  LNBits Wallet Dashboard v3.0 - Setup Inicial               ║"
echo "║  Sistema de Votación Escalable                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar Python
echo "🐍 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    echo "   Instala Python 3.8+ desde https://www.python.org"
    exit 1
fi
echo "✅ Python $(python3 --version | cut -d' ' -f2) encontrado"
echo ""

# Verificar pip
echo "📦 Verificando pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 no está instalado"
    exit 1
fi
echo "✅ pip encontrado"
echo ""

# Instalar dependencias
echo "📥 Instalando dependencias..."
if pip3 install -r requirements.txt; then
    echo "✅ Dependencias instaladas"
else
    echo "❌ Error al instalar dependencias"
    exit 1
fi
echo ""

# Crear .env en data/ si no existe
DATA_DIR="${BASH_SOURCE%/*}/data"
mkdir -p "$DATA_DIR"

if [ ! -f "$DATA_DIR/.env" ]; then
    echo "📝 Creando .env..."
    cp .env.example "$DATA_DIR/.env"
    echo "✅ .env creado (editar con tus valores)"
else
    echo "✅ .env ya existe"
fi
echo ""

# Crear wallets.json en data/ si no existe
if [ ! -f "$DATA_DIR/wallets.json" ]; then
    echo "📋 Creando wallets.json..."
    cp wallets.example.json "$DATA_DIR/wallets.json"
    echo "✅ wallets.json creado (editar con tus Invoice Keys)"
else
    echo "✅ wallets.json ya existe"
fi
echo ""

# Mostrar próximos pasos
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  PRÓXIMOS PASOS                                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Editar .env:"
echo "   nano data/.env"
echo "   - Revisar/actualizar LNBITS_ENDPOINT si es necesario"
echo "   - Revisar/actualizar SATS_PER_VOTE si lo necesitas"
echo ""
echo "2️⃣  Editar wallets.json:"
echo "   nano data/wallets.json"
echo "   - Obtener Invoice Keys de LNBits para cada wallet"
echo "   - Reemplazar 'your_invoice_key_here' con tus keys reales"
echo "   - Actualizar 'display_name' si lo deseas"
echo ""
echo "3️⃣  Ejecutar dashboard:"
echo "   python3 lnbits_dashboard.py"
echo ""
echo "4️⃣  Acceder al dashboard:"
echo "   http://localhost:5000"
echo ""
echo "✅ Setup completado!"
echo ""
