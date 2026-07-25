#!/usr/bin/env python3
"""
=============================================================================
Sistema de Votación BTCOL - Módulo de Auditoría y Desencriptación
Script: desencriptar_lote_cedulas.py
Descripción: Recorre el directorio de capturas encriptadas (.enc) y desencripta
             CÉDULA POR CÉDULA una a una utilizando la clave simétrica. Reconstruye
             las imágenes originales e imprime un reporte completo con metadatos.
=============================================================================
"""

import argparse
import glob
import hashlib
import os
import sys
from datetime import datetime

# Importar la función de desencriptación individual
from desencriptar_imagen import desencriptar_imagen


def calcular_checksum_sha256(ruta_archivo: str) -> str:
    """Calcula el hash SHA-256 binario de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def desencriptar_lote_cedulas(clave_secreta: str, dir_entrada: str, dir_salida: str) -> dict:
    """
    Obtiene la lista de todos los archivos .enc en 'dir_entrada',
    los desencripta uno a uno y guarda las imágenes restauradas en 'dir_salida'.
    """
    if not os.path.exists(dir_entrada):
        print(f"❌ Error: El directorio de entrada '{dir_entrada}' no existe.")
        return {"total": 0, "exitosos": 0, "fallidos": 0}

    # Buscar todos los archivos .enc en la carpeta especificada
    patron_enc = os.path.join(dir_entrada, "*.enc")
    archivos_enc = sorted(glob.glob(patron_enc))

    if not archivos_enc:
        print("\n" + "=" * 70)
        print("🔍 DESENCRIPTACIÓN EN LOTE DE CÉDULAS DE ELECTORES BTCOL")
        print("=" * 70)
        print(f"📂 Directorio inspeccionado: {dir_entrada}")
        print("⚠️ No se encontraron archivos de cédulas encriptadas (.enc).")
        print("=" * 70 + "\n")
        return {"total": 0, "exitosos": 0, "fallidos": 0}

    os.makedirs(dir_salida, exist_ok=True)

    print("\n" + "=" * 70)
    print("🔓 DESENCRIPTACIÓN EN LOTE DE CÉDULAS DE ELECTORES BTCOL")
    print("=" * 70)
    print(f"📂 Directorio Origen:   {dir_entrada}")
    print(f"📁 Directorio Destino:  {dir_salida}")
    print(f"📦 Total Archivos .enc: {len(archivos_enc)}")
    print(f"🔑 Clave configurada:   {'*' * len(clave_secreta)}")
    print("=" * 70 + "\n")

    exitosos = 0
    fallidos = 0
    detalles = []

    # Recorrer las cédulas encriptadas una a una
    for idx, ruta_enc in enumerate(archivos_enc, start=1):
        nombre_enc = os.path.basename(ruta_enc)
        memo_hash_id = os.path.splitext(nombre_enc)[0]
        checksum_actual = calcular_checksum_sha256(ruta_enc)

        print(f"[{idx}/{len(archivos_enc)}] 📦 Procesando: {nombre_enc}")
        print(f"       🔑 Checksum SHA-256: {checksum_actual[:32]}...")

        # Nombre para la imagen restaurada individual
        nombre_salida = f"restaurada_{memo_hash_id}.jpg"
        ruta_salida_img = os.path.join(dir_salida, nombre_salida)

        # Llamar al desencriptador individual
        ruta_restaurada, metadatos = desencriptar_imagen(
            ruta_encriptada=ruta_enc,
            clave_secreta=clave_secreta,
            ruta_salida=ruta_salida_img,
            silencioso=True
        )

        if ruta_restaurada and metadatos:
            exitosos += 1
            w = metadatos.get('ancho_px', 0)
            h = metadatos.get('alto_px', 0)
            nombre_orig = metadatos.get('nombre_archivo_original', 'N/A')
            print(f"       ✅ RESTAURADA EXITOSAMENTE: {nombre_salida} ({w}x{h} px)")
            print(f"       📄 Nombre original: {nombre_orig}")
            detalles.append({
                "memo_hash": memo_hash_id,
                "archivo_enc": nombre_enc,
                "checksum256": checksum_actual,
                "imagen_restaurada": nombre_salida,
                "dimensiones": f"{w}x{h}",
                "estado": "ÉXITO"
            })
        else:
            fallidos += 1
            print(f"       ❌ ERROR: Clave incorrecta o archivo corrupto.")
            detalles.append({
                "memo_hash": memo_hash_id,
                "archivo_enc": nombre_enc,
                "checksum256": checksum_actual,
                "imagen_restaurada": None,
                "estado": "FALLIDO"
            })
        print("-" * 70)

    # Reporte final
    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL DE DESENCRIPTACIÓN EN LOTE")
    print("=" * 70)
    print(f"📦 Total de Cédulas .enc procesadas: {len(archivos_enc)}")
    print(f"✅ Desencriptadas con Éxito:        {exitosos}")
    print(f"❌ Fallidas (Clave Incorrecta):     {fallidos}")
    print(f"📁 Las imágenes restauradas están en: {os.path.abspath(dir_salida)}")
    print("=" * 70 + "\n")

    return {
        "total": len(archivos_enc),
        "exitosos": exitosos,
        "fallidos": fallidos,
        "detalles": detalles
    }


def main():
    # Determinar rutas por defecto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    default_dir_entrada = os.path.join(root_dir, "mesa_code", "impresora", "capturas_cedula")
    default_dir_salida = os.path.join(script_dir, "cedulas_desencriptadas")

    parser = argparse.ArgumentParser(
        description="Script para desencriptar en lote todas las cédulas .enc una a una."
    )
    parser.add_argument(
        "-k", "--key", type=str, required=True,
        help="Clave secreta simétrica para desencriptar todas las cédulas"
    )
    parser.add_argument(
        "-d", "--dir", type=str, default=default_dir_entrada,
        help=f"Directorio donde se encuentran los archivos .enc (por defecto: {default_dir_entrada})"
    )
    parser.add_argument(
        "-o", "--outdir", type=str, default=default_dir_salida,
        help=f"Directorio donde guardar las imágenes desencriptadas (por defecto: {default_dir_salida})"
    )

    args = parser.parse_args()

    desencriptar_lote_cedulas(
        clave_secreta=args.key,
        dir_entrada=args.dir,
        dir_salida=args.outdir
    )


if __name__ == "__main__":
    main()
