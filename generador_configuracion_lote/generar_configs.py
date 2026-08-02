#!/usr/bin/env python3
"""
generar_configs.py - Generador masivo de configuraciones JSON y encriptación en lote para el Sistema de Votación BTCOL.

Lee un archivo CSV de wallets y opcionalmente un archivo .md de parámetros globales (config_global.md)
para generar y encriptar automáticamente todos los JSONs requeridos por la plataforma:
- wallets.json & wallets.json.enc (Monitoreo global)
- candidatos.json & candidatos.json.enc (Urnas de mesas)
- mesas_config/mesa_code<N>/mesa_config.json & mesa_config.json.enc (Configuración individual por mesa)

Uso:
    python generar_configs.py [--csv ARCHIVO.csv] [--config-md CONFIG.md] [--output-dir DIR] [--clean-json] [--skip-encrypt]
"""

import os
import sys
import csv
import json
import re
import argparse
from pathlib import Path
from cryptography.fernet import Fernet

# 🔑 Clave Fernet empotrada (quemada en el script)
CLAVE_FERNET = b"rY7b4_x8K2vP9mN3qL0wJ5zT1uX8iO4aS7dF2gH5jK8="

def encriptar_bytes(raw_bytes: bytes) -> bytes:
    """Encripta los bytes usando la clave Fernet empotrada."""
    fernet = Fernet(CLAVE_FERNET)
    return fernet.encrypt(raw_bytes)

def cargar_config_md(md_path: Path) -> dict:
    """Extrae parámetros como url_lnbits y sats_per_vote desde un archivo Markdown."""
    config_defecto = {
        "url_lnbits": "http://localhost:5000",
        "sats_per_vote": 100
    }
    
    if not md_path.exists():
        print(f"ℹ️ Archivo Markdown '{md_path.name}' no encontrado. Se usarán valores por defecto.")
        return config_defecto
        
    print(f"📖 Cargando parámetros globales desde: {md_path}")
    content = md_path.read_text(encoding='utf-8')
    
    # Buscar url_lnbits
    m_url = re.search(r'url_lnbits(?:\*\*)?\s*[:=]\s*([^\s\n]+)', content, re.IGNORECASE)
    if m_url:
        val_url = m_url.group(1).strip('`*"\':<>')
        config_defecto["url_lnbits"] = val_url
        
    # Buscar sats_per_vote
    m_sats = re.search(r'sats_per_vote(?:\*\*)?\s*[:=]\s*(\d+)', content, re.IGNORECASE)
    if m_sats:
        config_defecto["sats_per_vote"] = int(m_sats.group(1))
        
    print(f"   • url_lnbits:    {config_defecto['url_lnbits']}")
    print(f"   • sats_per_vote: {config_defecto['sats_per_vote']}")
    
    return config_defecto

def formatear_nombre(wallet_name: str) -> str:
    """Convierte wallet_name tipo 'candidato1' o 'voto_en_blanco' o 'mesa1' a un nombre legible."""
    if not wallet_name:
        return ""
    
    n_lower = wallet_name.lower().strip()
    if n_lower == 'voto_en_blanco' or n_lower == 'votoenblanco':
        return 'Voto en Blanco'
    
    if n_lower.startswith('candidato'):
        num = n_lower.replace('candidato', '').strip('_- ')
        if num.isdigit():
            return f"Candidato {num}"
        return f"Candidato {num.capitalize()}" if num else "Candidato"
    
    if n_lower.startswith('mesa'):
        num = n_lower.replace('mesa', '').strip('_- ')
        if num.isdigit():
            return f"Mesa Electoral {num}"
        return f"Mesa Electoral {num.capitalize()}" if num else "Mesa Electoral"
    
    return wallet_name.replace('_', ' ').replace('-', ' ').title()

def obtener_nombre_directorio_mesa(wallet_name: str) -> str:
    """Genera el nombre del directorio para la mesa, ej: mesa1 -> mesa_code1."""
    n_lower = wallet_name.lower().strip()
    if n_lower.startswith('mesa'):
        num = n_lower.replace('mesa', '').strip('_- ')
        if num:
            return f"mesa_code{num}"
    return f"mesa_code_{wallet_name}"

def guardar_json_y_enc(ruta_json: Path, datos_dict: dict, encriptar: bool = True, borrar_json_plano: bool = False):
    """Guarda el archivo .json y opcionalmente crea su versión encriptada .json.enc."""
    json_bytes = json.dumps(datos_dict, indent=2, ensure_ascii=False).encode('utf-8')
    
    # 1. Guardar archivo .json plano si no se solicitó borrar directo
    if not borrar_json_plano:
        ruta_json.write_bytes(json_bytes)
        print(f"📄 Archivo generado: {ruta_json.name}")
        
    # 2. Guardar versión encriptada .json.enc
    if encriptar:
        ruta_enc = Path(str(ruta_json) + ".enc")
        bytes_cifrados = encriptar_bytes(json_bytes)
        ruta_enc.write_bytes(bytes_cifrados)
        print(f" └─ 🔒 Encriptado exitoso: {ruta_enc.name} ({len(bytes_cifrados)} bytes)")
        
    # 3. Eliminar json plano si se pasó --clean-json
    if borrar_json_plano and ruta_json.exists():
        ruta_json.unlink()
        print(f" └─ 🧹 Texto plano eliminado por --clean-json: {ruta_json.name}")

def procesar_csv(csv_path: Path, output_dir: Path, global_params: dict, encriptar: bool = True, borrar_json_plano: bool = False):
    """Lee el CSV y genera/encripta todos los archivos de configuración."""
    print(f"📖 Leyendo CSV de entrada: {csv_path}")
    
    if not csv_path.exists():
        print(f"❌ Error: El archivo '{csv_path}' no existe.")
        sys.exit(1)
        
    candidatos_list = []
    mesas_list = []
    
    url_lnbits = global_params.get("url_lnbits", "http://localhost:5000")
    sats_per_vote = global_params.get("sats_per_vote", 100)
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        columnas = reader.fieldnames or []
        columnas_requeridas = ['wallet_name', 'wallet_id', 'admin_key', 'invoice_key']
        for col in columnas_requeridas:
            if col not in columnas:
                print(f"❌ Error en CSV: Falta la columna requerida '{col}'. Columnas detectadas: {columnas}")
                sys.exit(1)
                
        mesa_count = 0
        for i, row in enumerate(reader, start=2):
            w_name = (row.get('wallet_name') or '').strip()
            w_id = (row.get('wallet_id') or '').strip()
            admin_key = (row.get('admin_key') or '').strip()
            invoice_key = (row.get('invoice_key') or '').strip()
            
            if not w_name or not w_id:
                print(f"⚠️ Línea {i}: Omitida por carecer de wallet_name o wallet_id válidos.")
                continue
                
            nombre_legible = formatear_nombre(w_name)
            
            # Si admin_key NO está vacía -> Es una Mesa Electoral
            if admin_key:
                mesa_count += 1
                puerto = 2006 + mesa_count
                dir_mesa = obtener_nombre_directorio_mesa(w_name)
                
                mesa_info = {
                    "id": w_name,
                    "nombre": nombre_legible,
                    "wallet_id": w_id,
                    "admin_key": admin_key,
                    "invoice_key": invoice_key,
                    "puerto_web": puerto,
                    "dir_name": dir_mesa
                }
                mesas_list.append(mesa_info)
            else:
                # Si admin_key está vacía -> Es un Candidato
                foto = f"fotos/{w_name}.png"
                if w_name.lower() == 'voto_en_blanco':
                    foto = "fotos/blanco.png"
                    
                candidato_info = {
                    "id": w_name,
                    "nombre": nombre_legible,
                    "wallet_id": w_id,
                    "invoice_key": invoice_key,
                    "foto_local": foto
                }
                candidatos_list.append(candidato_info)

    print(f"✅ CSV Procesado exitosamente:")
    print(f"   • Candidatos detectados: {len(candidatos_list)}")
    print(f"   • Mesas detectadas:      {len(mesas_list)}")
    
    # Crear carpeta de salida
    output_dir.mkdir(parents=True, exist_ok=True)
    mesas_output_dir = output_dir / "mesas_config"
    mesas_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generar y encriptar candidatos.json
    candidatos_json_data = {
        "candidatos": [
            {
                "id": c["id"],
                "nombre": c["nombre"],
                "wallet_id": c["wallet_id"],
                "api_key": c["invoice_key"],
                "url_lnbits": url_lnbits,
                "foto_local": c["foto_local"],
                "estado": "activo"
            }
            for c in candidatos_list
        ]
    }
    candidatos_file = output_dir / "candidatos.json"
    guardar_json_y_enc(candidatos_file, candidatos_json_data, encriptar=encriptar, borrar_json_plano=borrar_json_plano)
    
    # 2. Generar y encriptar wallets.json
    wallets_json_data = {
        "settings": {
            "url_lnbits": url_lnbits,
            "sats_per_vote": sats_per_vote,
            "show_sats_and_votes": True,
            "puerto_web": 5050
        },
        "candidatos": [
            {
                "id": c["id"],
                "nombre": c["nombre"],
                "wallet_id": c["wallet_id"],
                "api_key": c["invoice_key"],
                "url_lnbits": url_lnbits,
                "foto_local": c["foto_local"],
                "estado": "activo"
            }
            for c in candidatos_list
        ],
        "mesas": [
            {
                "id": m["id"],
                "nombre": m["nombre"],
                "wallet_id": m["wallet_id"],
                "api_key": m["invoice_key"],
                "url_lnbits": url_lnbits
            }
            for m in mesas_list
        ]
    }
    wallets_file = output_dir / "wallets.json"
    guardar_json_y_enc(wallets_file, wallets_json_data, encriptar=encriptar, borrar_json_plano=borrar_json_plano)
    
    # 3. Generar y encriptar <dir_mesa>/mesa_config.json para cada mesa
    for m in mesas_list:
        folder_mesa = mesas_output_dir / m["dir_name"]
        folder_mesa.mkdir(parents=True, exist_ok=True)
        
        mesa_config_data = {
            "mesa": {
                "id": m["id"],
                "nombre": m["nombre"],
                "api_key": m["admin_key"],
                "wallet_id": m["wallet_id"],
                "url_lnbits": url_lnbits,
                "sats_per_vote": sats_per_vote,
                "margen_fee_sats": 5,
                "puerto_web": m["puerto_web"],
                "host_web": "0.0.0.0",
                "timeout_segundos": 15,
                "estado": "activo"
            }
        }
        mesa_file = folder_mesa / "mesa_config.json"
        guardar_json_y_enc(mesa_file, mesa_config_data, encriptar=encriptar, borrar_json_plano=borrar_json_plano)
        
    print("\n🎉 Proceso completado con éxito. Archivos listos en:")
    print(f"   👉 {output_dir.resolve()}/")

def main():
    script_dir = Path(__file__).resolve().parent
    
    csv_defecto = None
    for item in script_dir.glob("*.csv"):
        csv_defecto = item
        break
        
    if not csv_defecto:
        csv_defecto = script_dir / "wallets.csv"
        
    config_md_defecto = script_dir / "config_global.md"
    
    parser = argparse.ArgumentParser(description="Generador en lote de configuraciones JSON y encriptación Fernet.")
    parser.add_argument("--csv", type=str, default=str(csv_defecto), help="Ruta al archivo CSV de entrada")
    parser.add_argument("--config-md", type=str, default=str(config_md_defecto), help="Ruta al archivo .md con parámetros globales")
    parser.add_argument("--output-dir", type=str, default=str(script_dir), help="Directorio de salida para los JSONs")
    parser.add_argument("--clean-json", action="store_true", help="Elimina los archivos .json en texto plano tras generar las versiones .json.enc")
    parser.add_argument("--skip-encrypt", action="store_true", help="Genera únicamente los archivos .json sin crear las versiones .json.enc")
    
    args = parser.parse_args()
    
    params_globales = cargar_config_md(Path(args.config_md))
    
    procesar_csv(
        csv_path=Path(args.csv),
        output_dir=Path(args.output_dir),
        global_params=params_globales,
        encriptar=not args.skip_encrypt,
        borrar_json_plano=args.clean_json
    )

if __name__ == "__main__":
    main()
