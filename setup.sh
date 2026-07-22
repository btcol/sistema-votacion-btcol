#!/bin/bash
# Setup Script - Sistema de Votación BTCOL (LNbits + Tor) v3.0
# Ejecutar: bash setup.sh

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Sistema de Votación BTCOL (LNbits + Tor) - Setup Inicial    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Determinar el directorio raíz del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
if pip3 install -r "$SCRIPT_DIR/requirements.txt"; then
    echo "✅ Dependencias instaladas"
else
    echo "❌ Error al instalar dependencias"
    exit 1
fi
echo ""

# Crear directorio data/ si no existe
DATA_DIR="$SCRIPT_DIR/data"
mkdir -p "$DATA_DIR"

# Crear wallets.json en data/ desde plantilla demo si no existe
if [ ! -f "$DATA_DIR/wallets.json" ]; then
    echo "📋 Creando data/wallets.json desde wallets.example.json..."
    cp "$SCRIPT_DIR/wallets.example.json" "$DATA_DIR/wallets.json"
    echo "✅ data/wallets.json creado (editar con tus Invoice Keys reales)"
else
    echo "✅ data/wallets.json ya existe"
fi
echo ""

# Verificar directorios de mesa y crear archivos de config desde demos
MESA_DATA_DIR="$SCRIPT_DIR/mesa_code/data_mesa"
mkdir -p "$MESA_DATA_DIR"

if [ ! -f "$MESA_DATA_DIR/mesa_config.json" ]; then
    echo "📋 Creando mesa_code/data_mesa/mesa_config.json desde mesa_config.example.json..."
    cp "$MESA_DATA_DIR/mesa_config.example.json" "$MESA_DATA_DIR/mesa_config.json"
    echo "✅ mesa_code/data_mesa/mesa_config.json creado (editar con tu Admin Key real)"
else
    echo "✅ mesa_code/data_mesa/mesa_config.json ya existe"
fi

if [ ! -f "$MESA_DATA_DIR/candidatos.json" ]; then
    echo "📋 Creando mesa_code/data_mesa/candidatos.json desde candidatos.example.json..."
    cp "$MESA_DATA_DIR/candidatos.example.json" "$MESA_DATA_DIR/candidatos.json"
    echo "✅ mesa_code/data_mesa/candidatos.json creado (editar con tus candidatos reales)"
else
    echo "✅ mesa_code/data_mesa/candidatos.json ya existe"
fi
echo ""

# Mostrar próximos pasos
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  PRÓXIMOS PASOS                                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "1️⃣  Configurar Wallets de Candidatos y Mesas:"
echo "   nano data/wallets.json"
echo "   - Reemplazar 'tu_invoice_key_...' con las Invoice Keys reales de LNbits."
echo ""
echo "2️⃣  Configurar Mesa Electoral:"
echo "   nano mesa_code/data_mesa/mesa_config.json"
echo "   - Reemplazar 'tu_admin_key_...' con la Admin Key real de la Mesa Electoral."
echo "   nano mesa_code/data_mesa/candidatos.json"
echo "   - Reemplazar credenciales de los candidatos elegibles en la mesa."
echo ""
echo "3️⃣  Ejecutar Componentes:"
echo ""
echo "   🖥️  Urna Electoral Web (Mesa):"
echo "      python3 mesa_code/app_web_mesa.py        -> http://localhost:2007"
echo ""
echo "   🌐 Dashboard Web de Monitoreo (Tiempo Real):"
echo "      python3 frontend/votos_dashboard.py      -> http://localhost:5050"
echo ""
echo "   ⚖️  Dashboard Web de Auditoría Electoral:"
echo "      python3 audit/auditoria_ln_votos.py      -> http://localhost:7070"
echo ""
echo "✅ Setup completado con éxito!"
echo ""
