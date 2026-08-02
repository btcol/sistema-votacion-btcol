#!/usr/bin/env python3
"""
desencriptar_configs.py - Script independiente para desencriptar archivos .enc (candidatos.json.enc, mesa_config.json.enc, wallets.json.enc) usando Fernet con clave empotrada.

Uso:
    python3 desencriptar_configs.py [--archivo RUTA_ENC] [--salida RUTA_JSON] [--restaurar]
"""

import sys
import json
import argparse
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

# 🔑 Clave Fernet empotrada (IDÉNTICA a encriptar_configs.py)
CLAVE_FERNET = b"rY7b4_x8K2vP9mN3qL0wJ5zT1uX8iO4aS7dF2gH5jK8="

def desencriptar_contenido(bytes_cifrados: bytes) -> str:
    """Desencripta los bytes cifrados usando la clave Fernet empotrada y retorna el string UTF-8."""
    fernet = Fernet(CLAVE_FERNET)
    bytes_descifrados = fernet.decrypt(bytes_cifrados)
    return bytes_descifrados.decode('utf-8')

def desencriptar_archivo(ruta_enc: Path, ruta_salida: Path = None, restaurar: bool = False) -> dict:
    """Lee un archivo .enc, lo desencripta y valida que sea JSON válido."""
    if not ruta_enc.exists():
        print(f"❌ Error: El archivo cifrado '{ruta_enc}' no existe.")
        return None
        
    try:
        bytes_cifrados = ruta_enc.read_bytes()
        texto_descifrado = desencriptar_contenido(bytes_cifrados)
        datos_json = json.loads(texto_descifrado)
        
        print(f"🔓 Descifrado exitoso: {ruta_enc.name}")
        
        # Determinar ruta de salida si se solicita restaurar
        target_out = ruta_salida
        if not target_out and restaurar:
            if ruta_enc.name.endswith(".enc"):
                target_out = Path(str(ruta_enc)[:-4])  # Quitar .enc
                
        if target_out:
            target_out.write_text(json.dumps(datos_json, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"   └─ Archivo restaurado guardado en: {target_out}")
            
        return datos_json

    except InvalidToken:
        print(f"❌ Error de descifrado en '{ruta_enc.name}': Token Fernet inválido o clave incorrecta.")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON en '{ruta_enc.name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Error procesando '{ruta_enc.name}': {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Desencriptador de archivos candidatos.json.enc, mesa_config.json.enc y otros .enc con clave Fernet empotrada.")
    parser.add_argument("--archivo", type=str, help="Ruta a un archivo .enc específico para descifrar (ej: candidatos.json.enc)")
    parser.add_argument("--salida", type=str, help="Ruta opcional para guardar el JSON descifrado")
    parser.add_argument("--dir", type=str, help="Directorio a buscar recursivamente archivos .enc")
    parser.add_argument("--restaurar", action="store_true", help="Si se especifica, restaura en disco el archivo .json original a partir del .enc")
    
    args = parser.parse_args()
    
    archivos_a_desencriptar = []
    
    if args.archivo:
        archivos_a_desencriptar.append(Path(args.archivo))
    elif args.dir:
        dir_target = Path(args.dir)
        archivos_a_desencriptar.extend(list(dir_target.rglob("*.enc")))
    else:
        root_dir = Path(__file__).resolve().parent
        gen_dir = root_dir / "generador_configuracion_lote"
        if gen_dir.exists():
            archivos_a_desencriptar.extend(list(gen_dir.rglob("*.enc")))
        mesa_data_dir = root_dir / "mesa_code" / "data_mesa"
        if mesa_data_dir.exists():
            archivos_a_desencriptar.extend(list(mesa_data_dir.rglob("*.enc")))
            
    vistos = set()
    dedup = []
    for f in archivos_a_desencriptar:
        abs_p = f.resolve()
        if abs_p not in vistos:
            vistos.add(abs_p)
            dedup.append(f)
    archivos_a_desencriptar = dedup

    if not archivos_a_desencriptar:
        print("⚠️ No se encontraron archivos .enc para desencriptar.")
        sys.exit(1)
        
    print(f"🚀 Iniciando desencriptación de {len(archivos_a_desencriptar)} archivo(s)...")
    for f in archivos_a_desencriptar:
        out_p = Path(args.salida) if args.salida and len(archivos_a_desencriptar) == 1 else None
        resultado = desencriptar_archivo(f, ruta_salida=out_p, restaurar=args.restaurar)
        if resultado:
            keys = list(resultado.keys())
            print(f"   └─ Llaves detectadas en JSON: {keys}")

if __name__ == "__main__":
    main()
