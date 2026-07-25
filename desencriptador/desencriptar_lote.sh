#!/usr/bin/env bash
# =============================================================================
# Sistema de Votación BTCOL - Módulo de Auditoría y Desencriptación
# Script: desencriptar_lote.sh
# Descripción: Script ejecutable que toma el directorio con todas las cédulas
#              encriptadas (.enc) y las desencripta UNA A UNA usando la clave
#              simétrica proporcionada como primer argumento.
# =============================================================================

set -e

# Obtener directorio absoluto donde se encuentra este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CLAVE="${1:-AUTO}"
DIR_ENTRADA="${2:-$ROOT_DIR/mesa_code/impresora/capturas_cedula}"
DIR_SALIDA="${3:-$SCRIPT_DIR/cedulas_desencriptadas}"


echo ""
echo "================================================================="
echo "🔓 DESENCRIPTACIÓN EN LOTE DE CÉDULAS ELECTORALES BTCOL"
echo "================================================================="
echo "🔑 Clave proporcionada: ****************"
echo "📂 Directorio Entrada:  $DIR_ENTRADA"
echo "📁 Directorio Salida:   $DIR_SALIDA"
echo "================================================================="
echo ""

# Ejecutar el script Python de lote
python3 "$SCRIPT_DIR/desencriptar_lote_cedulas.py" \
  --key "$CLAVE" \
  --dir "$DIR_ENTRADA" \
  --outdir "$DIR_SALIDA"
