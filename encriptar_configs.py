#!/usr/bin/env python3
"""
encriptar_configs.py - Script independiente para encriptar candidatos.json, mesa_config.json y wallets.json usando Fernet con clave empotrada.

Uso:
    python3 encriptar_configs.py [--archivo RUTA_JSON] [--dir DIRECTORIO]
"""

import sys
import json
import argparse
from pathlib import Path
from cryptography.fernet import Fernet

# 🔑 Clave Fernet empotrada (quemada en el script)
CLAVE_FERNET = b"rY7b4_x8K2vP9mN3qL0wJ5zT1uX8iO4aS7dF2gH5jK8="

def encriptar_contenido(datos_bytes: bytes) -> bytes:
    """Encripta los bytes usando la clave Fernet empotrada."""
    fernet = Fernet(CLAVE_FERNET)
    return fernet.encrypt(datos_bytes)

def encriptar_archivo(ruta_json: Path) -> Path:
    """Lee un archivo JSON, lo encripta y guarda el resultado con extensión .enc."""
    if not ruta_json.exists():
        print(f"❌ Error: El archivo '{ruta_json}' no existe.")
        return None
        
    try:
        raw_bytes = ruta_json.read_bytes()
        json.loads(raw_bytes.decode('utf-8'))
    except Exception as e:
        print(f"❌ Error: '{ruta_json}' no es un archivo JSON válido ({e}).")
        return None

    # Encriptar contenido
    datos_cifrados = encriptar_contenido(raw_bytes)
    
    # Ruta de salida .enc (ejemplo: candidatos.json.enc)
    if not str(ruta_json).endswith(".enc"):
        ruta_salida = Path(str(ruta_json) + ".enc")
    else:
        ruta_salida = ruta_json
        
    ruta_salida.write_bytes(datos_cifrados)
    print(f"🔒 Encriptado exitoso: {ruta_json.name} ➔ {ruta_salida.name} ({len(datos_cifrados)} bytes)")
    return ruta_salida

def main():
    parser = argparse.ArgumentParser(description="Encriptador de archivos candidatos.json, mesa_config.json y wallets.json con clave Fernet empotrada.")
    parser.add_argument("--archivo", type=str, help="Ruta a un archivo .json específico para encriptar (ej: candidatos.json)")
    parser.add_argument("--dir", type=str, help="Directorio a buscar recursivamente archivos candidatos.json, mesa_config.json y otros .json")
    
    args = parser.parse_args()
    
    archivos_a_encriptar = []
    
    if args.archivo:
        archivos_a_encriptar.append(Path(args.archivo))
    elif args.dir:
        dir_target = Path(args.dir)
        archivos_a_encriptar.extend(list(dir_target.rglob("*.json")))
    else:
        # Por defecto buscar archivos candidatos.json, mesa_config.json y wallets.json en el proyecto
        root_dir = Path(__file__).resolve().parent
        
        # 1. generador_configuracion_lote/
        gen_dir = root_dir / "generador_configuracion_lote"
        if (gen_dir / "candidatos.json").exists():
            archivos_a_encriptar.append(gen_dir / "candidatos.json")
        if (gen_dir / "wallets.json").exists():
            archivos_a_encriptar.append(gen_dir / "wallets.json")
            
        mesas_dir = gen_dir / "mesas_config"
        if mesas_dir.exists():
            archivos_a_encriptar.extend(list(mesas_dir.rglob("mesa_config.json")))
            
        # 2. mesa_code/data_mesa/
        mesa_data_dir = root_dir / "mesa_code" / "data_mesa"
        if (mesa_data_dir / "candidatos.json").exists():
            archivos_a_encriptar.append(mesa_data_dir / "candidatos.json")
        if (mesa_data_dir / "mesa_config.json").exists():
            archivos_a_encriptar.append(mesa_data_dir / "mesa_config.json")
            
    # Eliminar duplicados preservando el orden
    vistos = set()
    dedup = []
    for f in archivos_a_encriptar:
        abs_p = f.resolve()
        if abs_p not in vistos:
            vistos.add(abs_p)
            dedup.append(f)
    archivos_a_encriptar = dedup

    if not archivos_a_encriptar:
        print("⚠️ No se encontraron archivos candidatos.json o de configuración para encriptar.")
        sys.exit(1)
        
    print(f"🚀 Iniciando encriptación de {len(archivos_a_encriptar)} archivo(s)...")
    for f in archivos_a_encriptar:
        encriptar_archivo(f)

if __name__ == "__main__":
    main()
