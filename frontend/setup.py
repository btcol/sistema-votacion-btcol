#!/usr/bin/env python3
"""
setup.py - Asistente de Configuración del Dashboard (v3.0)
Script interactivo para verificar dependencias y preparar el archivo data/wallets.json
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WALLETS_FILE = DATA_DIR / "wallets.json"
EXAMPLE_FILE = BASE_DIR / "wallets.example.json"


def main():
    print("==========================================================")
    print("  Sistema de Votación BTCOL - Setup del Dashboard Web  ")
    print("==========================================================")
    print()

    # Verificar directorio data
    DATA_DIR.mkdir(exist_ok=True)

    # Copiar plantilla si no existe
    if not WALLETS_FILE.exists():
        if EXAMPLE_FILE.exists():
            print(f"📋 Creando {WALLETS_FILE} desde plantilla...")
            with open(EXAMPLE_FILE, "r", encoding="utf-8") as src, open(WALLETS_FILE, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            print("✅ Archivo data/wallets.json creado.")
        else:
            print("❌ No se encontró wallets.example.json.")
            sys.exit(1)
    else:
        print("✅ data/wallets.json ya existe.")

    print()
    print("📌 Para ejecutar los servicios:")
    print("   1. Urna Electoral:   python3 mesa_code/app_web_mesa.py  (Puerto 2007)")
    print("   2. Dashboard Votos:  python3 frontend/votos_dashboard.py (Puerto 5050)")
    print("   3. Auditoría:        python3 audit/auditoria_ln_votos.py (Puerto 7070)")
    print()


if __name__ == "__main__":
    main()
