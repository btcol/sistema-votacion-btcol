#!/usr/bin/env python3
"""
generar_configs.py - Generador masivo, cifrador Fernet, clonador de mesa_code y ofuscador PyArmor.

Procesa el CSV de wallets y config_global.md para:
1. Generar y cifrar los archivos .json.enc (candidatos.json.enc, wallets.json.enc, mesa_config.json.enc).
2. Clonar y personalizar la carpeta mesa_code para cada mesa en mesas_desplegadas/mesa_code<N>/.
3. Inyectar dinámicamente la CLAVE_FERNET centralizada en scripts/config.py de cada mesa antes de ofuscar.
4. Ofuscar el código Python de cada mesa desplegada usando PyArmor para blindar CLAVE_FERNET.

🔑 Generar una nueva Clave Fernet aleatoria y segura en la terminal:
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Uso recomendado:
    python3 generar_configs.py --fernet-key "TU_CLAVE_FERNET_BASE64="
"""

import os
import sys
import csv
import json
import re
import shutil
import subprocess
import argparse
from pathlib import Path
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "mesa_code"))
from scripts.seguridad_logs import enmascarar_url, enmascarar_key, sanitizar_texto, resolver_clave_fernet, extraer_clave_fernet_md

def encriptar_bytes(raw_bytes: bytes, clave_bytes: bytes) -> bytes:
    """Encripta los bytes usando la clave Fernet proporcionada."""
    fernet = Fernet(clave_bytes)
    return fernet.encrypt(raw_bytes)

def inyectar_clave_fernet_en_mesa(config_py_path: Path, clave_bytes: bytes):
    """Inyecta la CLAVE_FERNET centralizada directamente en el archivo scripts/config.py de la mesa clonada."""
    if not config_py_path.exists():
        print(f"⚠️ No se encontró {config_py_path} para inyectar CLAVE_FERNET.")
        return

    content = config_py_path.read_text(encoding='utf-8')
    # Reemplazar la asignación CLAVE_FERNET = ...
    patron = r'CLAVE_FERNET\s*=\s*(?:b"[^"]*"|b\'[^\']*\')'
    nueva_linea = f'CLAVE_FERNET = {clave_bytes!r}'
    
    nuevo_contenido, reemplazos = re.subn(patron, nueva_linea, content)
    if reemplazos > 0:
        config_py_path.write_text(nuevo_contenido, encoding='utf-8')
        print(f" └─ 🔑 CLAVE_FERNET inyectada exitosamente en {config_py_path.relative_to(config_py_path.parent.parent.parent)}")
    else:
        print(f" ⚠️ No se pudo localizar el patrón CLAVE_FERNET en {config_py_path.name}")

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
    
    m_url = re.search(r'url_lnbits(?:\*\*)?\s*[:=]\s*([^\s\n]+)', content, re.IGNORECASE)
    if m_url:
        val_url = m_url.group(1).strip('`*"\':<>')
        config_defecto["url_lnbits"] = val_url
        
    m_sats = re.search(r'sats_per_vote(?:\*\*)?\s*[:=]\s*(\d+)', content, re.IGNORECASE)
    if m_sats:
        config_defecto["sats_per_vote"] = int(m_sats.group(1))
        
    clave_md = extraer_clave_fernet_md(md_path)
    if clave_md:
        config_defecto["clave_fernet"] = clave_md

    print(f"   • url_lnbits:    {enmascarar_url(config_defecto['url_lnbits'])}")
    print(f"   • sats_per_vote: {config_defecto['sats_per_vote']}")
    if "clave_fernet" in config_defecto:
        print(f"   • clave_fernet:  {enmascarar_key(config_defecto['clave_fernet'])}")
    
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

def guardar_json_y_enc(ruta_json: Path, datos_dict: dict, clave_bytes: bytes, encriptar: bool = True, borrar_json_plano: bool = True):
    """Guarda el archivo .json y crea su versión encriptada .json.enc. Borra .json plano por defecto."""
    json_bytes = json.dumps(datos_dict, indent=2, ensure_ascii=False).encode('utf-8')
    
    ruta_enc = Path(str(ruta_json) + ".enc")
    if encriptar:
        bytes_cifrados = encriptar_bytes(json_bytes, clave_bytes=clave_bytes)
        ruta_enc.write_bytes(bytes_cifrados)
        print(f" └─ 🔒 Encriptado exitoso: {ruta_enc.name} ({len(bytes_cifrados)} bytes)")
        
    if not borrar_json_plano:
        ruta_json.write_bytes(json_bytes)
        print(f"📄 Archivo texto plano conservado: {ruta_json.name}")
    elif ruta_json.exists():
        ruta_json.unlink()

def ofuscar_directorio_mesa(mesa_dir: Path):
    """Ofusca los archivos Python de una mesa desplegada usando PyArmor para proteger CLAVE_FERNET."""
    print(f" 🛡️  Ofuscando código Python con PyArmor en: {mesa_dir.name}...")
    
    tmp_out = mesa_dir / "_pyarmor_dist"
    if tmp_out.exists():
        shutil.rmtree(tmp_out)
        
    cmd = [
        sys.executable, "-m", "pyarmor.cli", "gen",
        "-O", str(tmp_out),
        "-r",
        str(mesa_dir / "app_web_mesa.py"),
        str(mesa_dir / "app_desktop.py"),
        str(mesa_dir / "scripts"),
        str(mesa_dir / "impresora")
    ]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        for src_item in tmp_out.glob("*"):
            if src_item.is_dir() and src_item.name.startswith("pyarmor_runtime"):
                dest_item = mesa_dir / src_item.name
                if dest_item.exists():
                    shutil.rmtree(dest_item)
                shutil.copytree(src_item, dest_item)
            elif src_item.is_file():
                shutil.copy2(src_item, mesa_dir / src_item.name)
                
        for folder_name in ["scripts", "impresora"]:
            folder_obf = tmp_out / folder_name
            if folder_obf.exists():
                for item in folder_obf.rglob("*.py"):
                    rel_p = item.relative_to(folder_obf)
                    dest_p = mesa_dir / folder_name / rel_p
                    dest_p.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_p)

        shutil.rmtree(tmp_out)
        print(f"   ✅ Código de {mesa_dir.name} (scripts e impresora) ofuscado correctamente con PyArmor.")
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error ejecutando PyArmor en {mesa_dir.name}: {e.stderr}")
    except Exception as e:
        print(f"⚠️ Error en ofuscación de {mesa_dir.name}: {e}")

def procesar_csv(csv_path: Path, output_dir: Path, global_params: dict, clave_bytes: bytes, keep_json: bool = False, skip_obfuscate: bool = False):
    """Lee el CSV, genera/encripta JSONs, clona mesa_code por cada mesa, inyecta CLAVE_FERNET y ofusca con PyArmor."""
    print(f"📖 Leyendo CSV de entrada: {csv_path}")
    print(f"🔑 Clave Fernet activa: {enmascarar_key(clave_bytes.decode('utf-8'))}")
    
    if not csv_path.exists():
        print(f"❌ Error: El archivo '{csv_path}' no existe.")
        sys.exit(1)
        
    candidatos_list = []
    mesas_list = []
    
    url_lnbits = global_params.get("url_lnbits", "http://localhost:5000")
    sats_per_vote = global_params.get("sats_per_vote", 100)
    borrar_json_plano = not keep_json
    
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
    
    # Crear carpetas de salida
    output_dir.mkdir(parents=True, exist_ok=True)
    mesas_desplegadas_dir = output_dir / "mesas_desplegadas"
    mesas_desplegadas_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generar candidatos.json & candidatos.json.enc
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
    guardar_json_y_enc(candidatos_file, candidatos_json_data, clave_bytes=clave_bytes, encriptar=True, borrar_json_plano=borrar_json_plano)
    
    # 2. Generar wallets.json & wallets.json.enc
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
    guardar_json_y_enc(wallets_file, wallets_json_data, clave_bytes=clave_bytes, encriptar=True, borrar_json_plano=borrar_json_plano)
    
    # Ruta raíz del repositorio
    project_root = Path(__file__).resolve().parent.parent
    
    # 2b. Guardar copia de wallets.json.enc en data/ para el Dashboard
    data_dir_root = project_root / "data"
    data_dir_root.mkdir(parents=True, exist_ok=True)
    guardar_json_y_enc(data_dir_root / "wallets.json", wallets_json_data, clave_bytes=clave_bytes, encriptar=True, borrar_json_plano=borrar_json_plano)
    print(f" └─ 📊 Configuración de monitoreo guardada en: data/wallets.json.enc")
    
    # Ruta de la plantilla mesa_code en la raíz del repositorio
    template_mesa_dir = project_root / "mesa_code"
    
    if not template_mesa_dir.exists():
        print(f"❌ Error: La carpeta plantilla '{template_mesa_dir}' no existe.")
        sys.exit(1)
        
    print(f"\n📦 Clonando, inyectando CLAVE_FERNET y personalizando {len(mesas_list)} paquete(s) de Mesa Electoral...")
    
    # 3. Clonar mesa_code por cada mesa, inyectar CLAVE_FERNET y sus archivos cifrados
    for m in mesas_list:
        dest_mesa_dir = mesas_desplegadas_dir / m["dir_name"]
        
        if dest_mesa_dir.exists():
            shutil.rmtree(dest_mesa_dir)
            
        print(f"\n🖥️  Configurando {m['dir_name']} ({m['nombre']})...")
        
        # Copiar plantilla mesa_code
        shutil.copytree(
            template_mesa_dir,
            dest_mesa_dir,
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.db', '*.sqlite3', 'logs', 'votos_local.db', '.git', '*.enc')
        )
        
        # Inyectar CLAVE_FERNET centralizada en scripts/config.py antes de cualquier cifrado/ofuscación
        inyectar_clave_fernet_en_mesa(dest_mesa_dir / "scripts" / "config.py", clave_bytes)
        
        # Preparar data_mesa de la mesa clonada
        data_mesa_target = dest_mesa_dir / "data_mesa"
        data_mesa_target.mkdir(parents=True, exist_ok=True)
        
        # Inyectar candidatos.json.enc
        candidatos_bytes = json.dumps(candidatos_json_data, indent=2, ensure_ascii=False).encode('utf-8')
        (data_mesa_target / "candidatos.json.enc").write_bytes(encriptar_bytes(candidatos_bytes, clave_bytes=clave_bytes))
        
        # Inyectar mesa_config.json.enc de la mesa
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
        mesa_config_bytes = json.dumps(mesa_config_data, indent=2, ensure_ascii=False).encode('utf-8')
        (data_mesa_target / "mesa_config.json.enc").write_bytes(encriptar_bytes(mesa_config_bytes, clave_bytes=clave_bytes))
        
        if borrar_json_plano:
            for raw_j in data_mesa_target.glob("*.json"):
                raw_j.unlink()
            print(f"   └─ 🧹 Archivos .json planos eliminados en {m['dir_name']}/data_mesa/")
            
        # 4. Ofuscar con PyArmor con la clave ya inyectada
        if not skip_obfuscate:
            ofuscar_directorio_mesa(dest_mesa_dir)
            
    print("\n🎉 Proceso completado con éxito. Todas las mesas están listas en:")
    print(f"   👉 {mesas_desplegadas_dir.resolve()}/")

def main():
    script_dir = Path(__file__).resolve().parent
    
    csv_defecto = None
    for item in script_dir.glob("*.csv"):
        csv_defecto = item
        break
        
    if not csv_defecto:
        csv_defecto = script_dir / "wallets.csv"
        
    config_md_defecto = script_dir / "config_global.md"
    
    parser = argparse.ArgumentParser(description="Generador masivo, cifrador Fernet, clonador de mesas y ofuscador PyArmor.")
    parser.add_argument("--csv", type=str, default=str(csv_defecto), help="Ruta al archivo CSV de entrada")
    parser.add_argument("--config-md", type=str, default=str(config_md_defecto), help="Ruta al archivo .md con parámetros globales")
    parser.add_argument("--output-dir", type=str, default=str(script_dir), help="Directorio donde se generarán los desplegables")
    parser.add_argument("--fernet-key", type=str, default=None, help="Clave Fernet personalizada en Base64 (sobrescribe la lectura de config_global.md)")
    parser.add_argument("--keep-json", action="store_true", help="Conserva los archivos .json planos (por defecto se eliminan dejándolos solo .json.enc)")
    parser.add_argument("--skip-obfuscate", action="store_true", help="Omite la ofuscación con PyArmor")
    
    args = parser.parse_args()
    
    params_globales = cargar_config_md(Path(args.config_md))
    
    try:
        clave_activa = resolver_clave_fernet(
            clave_custom=args.fernet_key,
            md_path=Path(args.config_md)
        )
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    
    procesar_csv(
        csv_path=Path(args.csv),
        output_dir=Path(args.output_dir),
        global_params=params_globales,
        clave_bytes=clave_activa,
        keep_json=args.keep_json,
        skip_obfuscate=args.skip_obfuscate
    )

if __name__ == "__main__":
    main()
