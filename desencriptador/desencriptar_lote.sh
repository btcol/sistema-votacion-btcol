#!/usr/bin/env bash
# =============================================================================
# Sistema de Votación BTCOL - Módulo de Auditoría y Desencriptación
# Script: desencriptar_lote.sh
# Descripción: Script ejecutable para desencriptar las cédulas cifradas (.enc)
#              de una, varias o todas las mesas electorales desplegadas.
# =============================================================================

set -e

# Obtener directorio absoluto donde se encuentra este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "================================================================="
echo "🔓 DESENCRIPTACIÓN EN LOTE MULTI-MESA DE CÉDULAS ELECTORALES BTCOL"
echo "================================================================="
echo "🚀 Iniciando orquestador Python..."
echo "================================================================="
echo ""

# Si se pasaron argumentos, se reenvían directamente a desencriptar_lote_cedulas.py
if [ $# -gt 0 ]; then
  python3 "$SCRIPT_DIR/desencriptar_lote_cedulas.py" "$@"
else
  # Si no hay argumentos, se ejecuta en modo automático buscando en todas las mesas
  python3 "$SCRIPT_DIR/desencriptar_lote_cedulas.py"
fi
