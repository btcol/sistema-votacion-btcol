#!/usr/bin/env python3
"""
=============================================================================
Sistema de Votación BTCOL - Módulo de Auditoría y Desencriptación
Script: desencriptar_lote_cedulas.py
Descripción: Recorre el directorio o los directorios de capturas encriptadas (.enc)
             de una o múltiples mesas (mesa_code1, mesa_code2, etc.) y desencripta
             CÉDULA POR CÉDULA una a una utilizando la clave simétrica.
             Reconstruye las imágenes originales organizadas por subcarpeta de mesa
             e imprime un reporte completo con metadatos.
=============================================================================
"""

import argparse
import glob
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

# Importar funciones de seguridad
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(root_dir, "mesa_code"))
from scripts.seguridad_logs import enmascarar_hash, sanitizar_texto

# Importar la función de desencriptación individual
from desencriptar_imagen import desencriptar_imagen


def calcular_checksum_sha256(ruta_archivo: str) -> str:
    """Calcula el hash SHA-256 binario de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def resolver_directorios_mesas(entradas: list = None) -> list:
    """
    Resuelve una lista de especificaciones de mesas/directorios a sus rutas absolutas
    de 'impresora/capturas_cedula'.
    
    Si entradas es None o está vacío, busca automáticamente en:
    1. generador_configuracion_lote/mesas_desplegadas/mesa_code*
    2. mesa_code/
    """
    base_root = Path(root_dir)
    mesas_resueltas = []
    
    def buscar_capturas_dir(d_path: Path) -> tuple:
        """Intenta localizar la carpeta de capturas de cédula a partir de un path dado."""
        if not d_path.exists():
            return None, None
            
        # Caso 1: El path ya apunta directamente a 'capturas_cedula'
        if d_path.name == "capturas_cedula" and d_path.is_dir():
            nombre_mesa = d_path.parent.parent.name if d_path.parent.name == "impresora" else d_path.parent.name
            return nombre_mesa, d_path
            
        # Caso 2: El path apunta a la raíz de una mesa (ej: mesa_code1 o mesas_desplegadas/mesa_code1)
        sub_capturas = d_path / "impresora" / "capturas_cedula"
        if sub_capturas.exists() and sub_capturas.is_dir():
            return d_path.name, sub_capturas
            
        # Caso 3: Es un directorio cualquiera con archivos .enc
        if d_path.is_dir():
            return d_path.name, d_path
            
        return None, None

    if not entradas:
        # Auto-descubrimiento de mesas
        # 1. Buscar en mesas desplegadas por lote
        desplegadas_dir = base_root / "generador_configuracion_lote" / "mesas_desplegadas"
        if desplegadas_dir.exists():
            for m_dir in sorted(desplegadas_dir.glob("mesa_code*")):
                nombre, cap_dir = buscar_capturas_dir(m_dir)
                if cap_dir and cap_dir.exists():
                    mesas_resueltas.append((nombre, cap_dir))
                    
        # 2. Buscar en la mesa base
        mesa_base = base_root / "mesa_code"
        if mesa_base.exists():
            nombre, cap_dir = buscar_capturas_dir(mesa_base)
            if cap_dir and cap_dir.exists():
                # Evitar duplicados si mesa_code ya estaba
                if not any(cd == cap_dir for _, cd in mesas_resueltas):
                    mesas_resueltas.append((nombre, cap_dir))
    else:
        for ent in entradas:
            ent_path = Path(ent).resolve() if os.path.isabs(ent) else (base_root / ent).resolve()
            
            # Si no existe directamente, probar dentro de mesas_desplegadas
            if not ent_path.exists():
                ent_desplegada = base_root / "generador_configuracion_lote" / "mesas_desplegadas" / ent
                if ent_desplegada.exists():
                    ent_path = ent_desplegada.resolve()
            
            # Si es un patrón o comodín glob
            if "*" in ent or "?" in ent:
                for match in sorted(glob.glob(ent)):
                    nombre, cap_dir = buscar_capturas_dir(Path(match).resolve())
                    if cap_dir:
                        mesas_resueltas.append((nombre, cap_dir))
                continue
                
            nombre, cap_dir = buscar_capturas_dir(ent_path)
            if cap_dir:
                mesas_resueltas.append((nombre, cap_dir))
            else:
                print(f"⚠️ Advertencia: No se encontró un directorio de capturas válido en '{ent}'")

    return mesas_resueltas


def desencriptar_lote_cedulas(clave_secreta: str = "AUTO", entradas: list = None, dir_salida: str = None) -> dict:
    """
    Obtiene la lista de todos los archivos .enc en las mesas/directorios especificados o descubiertos,
    los desencripta uno a uno y guarda las imágenes restauradas en 'dir_salida/<nombre_mesa>'.
    Si 'clave_secreta' es 'AUTO' o None, usa el hash de la factura LNbits como clave simétrica.
    """
    script_path = os.path.dirname(os.path.abspath(__file__))
    
    if not dir_salida:
        dir_salida = os.path.join(script_path, "cedulas_desencriptadas")

    mesas_a_procesar = resolver_directorios_mesas(entradas)

    if not mesas_a_procesar:
        print("\n" + "=" * 70)
        print("🔍 DESENCRIPTACIÓN EN LOTE DE CÉDULAS DE ELECTORES BTCOL")
        print("=" * 70)
        print("⚠️ No se encontraron directorios de capturas (.enc) para procesar.")
        print("=" * 70 + "\n")
        return {"total": 0, "exitosos": 0, "fallidos": 0, "mesas_procesadas": 0}

    usar_modo_auto = (not clave_secreta or clave_secreta.upper() == "AUTO")

    print("\n" + "=" * 70)
    print("🔓 DESENCRIPTACIÓN EN LOTE DE CÉDULAS DE ELECTORES BTCOL")
    print("=" * 70)
    print(f"🏛️  Mesas Encontradas:  {len(mesas_a_procesar)}")
    print(f"📁 Directorio Destino: {dir_salida}")
    if usar_modo_auto:
        print(f"🔑 Modo de Clave:      AUTOMÁTICO (Clave = Hash LNbits / ID del archivo .enc)")
    else:
        print(f"🔑 Modo de Clave:      MANUAL ({'*' * len(clave_secreta)})")
    print("=" * 70)

    total_general = 0
    exitosos_general = 0
    fallidos_general = 0
    reporte_mesas = []

    for idx_m, (nombre_mesa, dir_entrada) in enumerate(mesas_a_procesar, start=1):
        patron_enc = os.path.join(str(dir_entrada), "*.enc")
        archivos_enc = sorted(glob.glob(patron_enc))
        
        print(f"\n📌 [{idx_m}/{len(mesas_a_procesar)}] Procesando Mesa: '{nombre_mesa}' ({len(archivos_enc)} archivos .enc)")
        print(f"   📂 Ruta Origen: {dir_entrada}")

        if not archivos_enc:
            print("   ⚠️ No hay archivos .enc en esta mesa.")
            continue

        # Crear subcarpeta para organizar la salida por mesa
        salida_mesa_dir = os.path.join(dir_salida, nombre_mesa)
        os.makedirs(salida_mesa_dir, exist_ok=True)

        exitosos_mesa = 0
        fallidos_mesa = 0

        for idx, ruta_enc in enumerate(archivos_enc, start=1):
            nombre_enc = os.path.basename(ruta_enc)
            memo_hash_id = os.path.splitext(nombre_enc)[0]
            checksum_actual = calcular_checksum_sha256(ruta_enc)

            clave_efectiva = memo_hash_id if usar_modo_auto else clave_secreta

            print(f"   [{idx}/{len(archivos_enc)}] 📦 {nombre_enc}")
            print(f"          🔑 Clave (Hash LNbits): {enmascarar_hash(clave_efectiva)}")
            print(f"          🛡️ Checksum SHA-256:     {enmascarar_hash(checksum_actual)}")

            nombre_salida = f"restaurada_{memo_hash_id}.jpg"
            ruta_salida_img = os.path.join(salida_mesa_dir, nombre_salida)

            ruta_restaurada, metadatos = desencriptar_imagen(
                ruta_encriptada=ruta_enc,
                clave_secreta=clave_efectiva,
                ruta_salida=ruta_salida_img,
                silencioso=True
            )

            if ruta_restaurada and metadatos:
                exitosos_mesa += 1
                w = metadatos.get('ancho_px', 0)
                h = metadatos.get('alto_px', 0)
                nombre_orig = metadatos.get('nombre_archivo_original', 'N/A')
                print(f"          ✅ RESTAURADA: {nombre_salida} ({w}x{h} px) [Orig: {nombre_orig}]")
            else:
                fallidos_mesa += 1
                print(f"          ❌ ERROR: Clave incorrecta o archivo corrupto.")
            print("   " + "-" * 65)

        total_general += len(archivos_enc)
        exitosos_general += exitosos_mesa
        fallidos_general += fallidos_mesa

        reporte_mesas.append({
            "mesa": nombre_mesa,
            "total": len(archivos_enc),
            "exitosos": exitosos_mesa,
            "fallidos": fallidos_mesa,
            "dir_salida": salida_mesa_dir
        })

    # Reporte final consolidado
    print("\n" + "=" * 70)
    print("📊 RESUMEN CONSOLIDADO FINAL DE DESENCRIPTACIÓN MULTI-MESA")
    print("=" * 70)
    print(f"🏛️ Total de Mesas Procesadas:       {len(mesas_a_procesar)}")
    print(f"📦 Total Cédulas .enc Procesadas:    {total_general}")
    print(f"✅ Desencriptadas con Éxito:         {exitosos_general}")
    print(f"❌ Fallidas (Clave Incorrecta):      {fallidos_general}")
    print(f"📁 Las imágenes están organizadas en: {os.path.abspath(dir_salida)}")
    print("=" * 70 + "\n")

    return {
        "total": total_general,
        "exitosos": exitosos_general,
        "fallidos": fallidos_general,
        "mesas": reporte_mesas
    }


def main():
    script_path = os.path.dirname(os.path.abspath(__file__))
    default_dir_salida = os.path.join(script_path, "cedulas_desencriptadas")

    parser = argparse.ArgumentParser(
        description="Script para desencriptar en lote las cédulas .enc de una o múltiples mesas electorales."
    )
    parser.add_argument(
        "-k", "--key", type=str, default="AUTO",
        help="Clave simétrica para desencriptar (por defecto: AUTO, resuelve automáticamente la clave desde el Hash LNbits de cada archivo)"
    )
    parser.add_argument(
        "-d", "--dir", type=str, nargs="*", default=None,
        help="Directorios o nombres de mesa (ej: mesa_code1, mesa_code2 o rutas completas). Si se omite, busca en todas las mesas desplegadas automáticamente."
    )
    parser.add_argument(
        "-o", "--outdir", type=str, default=default_dir_salida,
        help=f"Directorio base donde guardar las imágenes desencriptadas organizadas por subcarpeta (por defecto: {default_dir_salida})"
    )

    args = parser.parse_args()

    desencriptar_lote_cedulas(
        clave_secreta=args.key,
        entradas=args.dir,
        dir_salida=args.outdir
    )


if __name__ == "__main__":
    main()
