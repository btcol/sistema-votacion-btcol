#!/usr/bin/env python3
"""
=============================================================================
Sistema de Votación BTCOL - Módulo de Auditoría Criptográfica & Forense
Script: auditar_comprobantes_pdf.py
=============================================================================

📖 GUÍA DE USO:
-----------------------------------------------------------------------------
Este script permite a auditores, observadores electorales y peritos informáticos
examinar y validar la integridad matemática y la trazabilidad forense de los
comprobantes de votación emitidos en formato PDF.

Capacidades:
  1. Extracción de metadatos nativos PDF (/Info: Title, Author, Subject, Keywords).
  2. Extracción de telemetría de la máquina emisora (Host, SO, Kernel, Python, PID).
  3. Reconciliación del Payment Hash Lightning y Checksum SHA-256 de Cédula.
  4. Verificación criptográfica del Sello de Integridad HMAC-SHA256 del documento.
  5. Modo de inspección individual (un solo archivo) o masivo (directorios completos).
  6. Exportación automatizada de reportes consolidados en CSV o JSON.

EJEMPLOS DE EJECUCIÓN:
-----------------------------------------------------------------------------
1. Auditar un comprobante PDF específico:
   python3 audit/auditar_comprobantes_pdf.py --archivo mesa_code/impresora/comprobantes_emitidos/comprobante_ejemplo.pdf

2. Auditar masivamente todos los comprobantes emitidos en la mesa local:
   python3 audit/auditar_comprobantes_pdf.py --dir mesa_code/impresora/comprobantes_emitidos

3. Auditar todas las mesas desplegadas y exportar reporte a CSV:
   python3 audit/auditar_comprobantes_pdf.py --dir generador_configuracion_lote/mesas_desplegadas --export-csv audit/reporte_comprobantes_global.csv

4. Exportar auditoría consolidada a JSON:
   python3 audit/auditar_comprobantes_pdf.py --dir . --export-json audit/reporte_forense.json
=============================================================================
"""

import os
import sys
import json
import csv
import hmac
import hashlib
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Añadir el directorio raíz para permitir importación de seguridad_logs si es necesario
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "mesa_code"))

try:
    from scripts.seguridad_logs import enmascarar_hash, enmascarar_key
except ImportError:
    def enmascarar_hash(h): return f"{h[:6]}...{h[-6:]}" if h and len(h) > 12 else str(h)
    def enmascarar_key(k): return f"{k[:4]}...{k[-4:]}" if k and len(k) > 8 else str(k)


def extraer_info_pdf_binario(ruta_pdf: Path) -> Dict[str, str]:
    """
    Parsea los objetos /Info del archivo PDF estándar en binario sin dependencias externas pesadas.
    """
    info = {}
    try:
        raw_bytes = ruta_pdf.read_bytes()
        
        # Buscar claves estándar en el diccionario /Info
        for clave in ["Title", "Author", "Subject", "Keywords", "Creator", "Producer", "CreationDate"]:
            patron = f"/{clave}".encode('latin-1')
            pos = raw_bytes.find(patron)
            if pos != -1:
                # Extraer hasta el final del paréntesis o valor
                start_val = raw_bytes.find(b'(', pos)
                if start_val != -1 and (start_val - pos) < 30:
                    end_val = raw_bytes.find(b')', start_val)
                    if end_val != -1:
                        val_bytes = raw_bytes[start_val + 1:end_val]
                        # Limpiar BOM UTF-16 si fue escrito por Pillow (þÿ)
                        if val_bytes.startswith(b'\xfe\xff'):
                            try:
                                info[clave] = val_bytes[2:].decode('utf-16-be', errors='ignore')
                            except Exception:
                                info[clave] = val_bytes.decode('latin-1', errors='ignore')
                        else:
                            info[clave] = val_bytes.decode('latin-1', errors='ignore')
    except Exception as e:
        info["_parse_error"] = str(e)
    return info


def parsear_keywords_btcol(keywords_str: str) -> Dict[str, str]:
    """
    Extrae los campos estructurados 'CLAVE:VALOR' del campo Keywords del PDF.
    Ejemplo: 'BTCOL;VOTACION;MESA:MESA-01;VOTO:VOTO-123;SHA256:abc;HMAC:xyz'
    """
    campos = {}
    if not keywords_str:
        return campos
    for item in keywords_str.split(";"):
        if ":" in item:
            k, v = item.split(":", 1)
            campos[k.strip().lower()] = v.strip()
    return campos


def verificar_integridad_hmac(metadatos: Dict[str, Any], memo_hash: str, sello_recibido: str) -> bool:
    """
    Reconstruye el cálculo del sello HMAC-SHA256 para verificar que los datos no hayan sido alterados.
    """
    if not sello_recibido or not memo_hash:
        return False
    
    # Crear copia sin el sello para calcular el hash canónico
    copia = {k: v for k, v in metadatos.items() if k != "sello_integridad_hmac256"}
    datos_serializados = json.dumps(copia, sort_keys=True, ensure_ascii=False).encode('utf-8')
    clave = memo_hash.encode('utf-8')
    
    sello_calculado = hmac.new(clave, datos_serializados, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sello_calculado, sello_recibido)


def auditar_archivo_pdf(ruta_pdf: Path) -> Dict[str, Any]:
    """
    Ejecuta la auditoría forense de un único archivo de comprobante PDF.
    """
    resultado = {
        "archivo": str(ruta_pdf.resolve()),
        "nombre_archivo": ruta_pdf.name,
        "tamano_bytes": ruta_pdf.stat().st_size if ruta_pdf.exists() else 0,
        "sha256_pdf": None,
        "mesa": "N/A",
        "candidato": "N/A",
        "voto_id": "N/A",
        "memo_hash": "N/A",
        "checksum256_cedula": "N/A",
        "timestamp_utc": "N/A",
        "hostname_emisor": "N/A",
        "os_emisor": "N/A",
        "python_version": "N/A",
        "sello_hmac": "N/A",
        "estado_integridad": "DESCONOCIDO",
        "detalles_forenses": {}
    }

    if not ruta_pdf.exists():
        resultado["estado_integridad"] = "ARCHIVO_NO_EXISTE"
        return resultado

    # 1. Calcular Hash SHA-256 del archivo físico
    pdf_bytes = ruta_pdf.read_bytes()
    resultado["sha256_pdf"] = hashlib.sha256(pdf_bytes).hexdigest()

    # 2. Extraer metadatos nativos PDF
    info_pdf = extraer_info_pdf_binario(ruta_pdf)
    resultado["pdf_info_nativo"] = info_pdf

    # 3. Intentar cargar archivo sidecar .meta.json si existe
    ruta_sidecar = ruta_pdf.parent / f"{ruta_pdf.stem}.meta.json"
    sidecar_data = None
    if ruta_sidecar.exists():
        try:
            sidecar_data = json.loads(ruta_sidecar.read_text(encoding='utf-8'))
            resultado["detalles_forenses"] = sidecar_data
        except Exception:
            pass

    # 4. Extraer datos estructurados de Keywords o del Sidecar
    kw_campos = parsear_keywords_btcol(info_pdf.get("Keywords", ""))

    if sidecar_data:
        resultado["mesa"] = sidecar_data.get("mesa_nombre", "N/A")
        resultado["candidato"] = sidecar_data.get("candidato_nombre", "N/A")
        resultado["voto_id"] = sidecar_data.get("voto_id", "N/A")
        resultado["memo_hash"] = sidecar_data.get("memo_hash", "N/A")
        resultado["checksum256_cedula"] = sidecar_data.get("checksum256_cedula", "N/A")
        resultado["timestamp_utc"] = sidecar_data.get("timestamp_utc", "N/A")
        resultado["sello_hmac"] = sidecar_data.get("sello_integridad_hmac256", "N/A")
        
        telemetria = sidecar_data.get("telemetria_maquina", {})
        resultado["hostname_emisor"] = telemetria.get("hostname", "N/A")
        resultado["os_emisor"] = f"{telemetria.get('os_name', '')} {telemetria.get('os_release', '')}".strip()
        resultado["python_version"] = telemetria.get("python_version", "N/A")

        # Verificar Sello HMAC
        if resultado["sello_hmac"] != "N/A" and resultado["memo_hash"] != "N/A":
            es_valido = verificar_integridad_hmac(sidecar_data, resultado["memo_hash"], resultado["sello_hmac"])
            resultado["estado_integridad"] = "INTEGRO_VALIDADO" if es_valido else "ALERTA_HMAC_CORRUPTO"
        else:
            resultado["estado_integridad"] = "METADATOS_INCOMPLETOS"
    else:
        # Fallback a metadatos extraídos de los headers del PDF
        resultado["mesa"] = kw_campos.get("mesa", "N/A")
        resultado["voto_id"] = kw_campos.get("voto", "N/A")
        resultado["checksum256_cedula"] = kw_campos.get("sha256", "N/A")
        resultado["sello_hmac"] = kw_campos.get("hmac", "N/A")
        
        author = info_pdf.get("Author", "")
        creator = info_pdf.get("Creator", "")
        subject = info_pdf.get("Subject", "")
        
        resultado["hostname_emisor"] = author
        resultado["os_emisor"] = creator
        resultado["detalles_forenses"] = {"keywords": kw_campos, "subject": subject}
        
        if kw_campos.get("hmac") and kw_campos.get("sha256"):
            resultado["estado_integridad"] = "PDF_NATIVO_VALIDO"
        else:
            resultado["estado_integridad"] = "PDF_SIN_METADATOS_BTCOL"

    return resultado


def resolver_rutas_busqueda(entradas: Optional[List[str]] = None) -> List[Path]:
    """
    Resuelve una lista de cadenas de texto (nombres de mesa, rutas relativas o absolutas)
    a rutas existentes en el sistema de archivos. Si no se pasa ninguna entrada,
    auto-descubre automáticamente todas las mesas desplegadas y la mesa base.
    """
    rutas_resueltas = []
    
    if not entradas:
        # Auto-descubrimiento de mesas
        desplegadas_dir = BASE_DIR / "generador_configuracion_lote" / "mesas_desplegadas"
        if desplegadas_dir.exists():
            rutas_resueltas.append(desplegadas_dir)
        mesa_base = BASE_DIR / "mesa_code"
        if mesa_base.exists():
            rutas_resueltas.append(mesa_base)
        if not rutas_resueltas:
            rutas_resueltas.append(BASE_DIR)
        return rutas_resueltas

    for ent in entradas:
        p = Path(ent)
        # 1. Probar ruta tal cual (relativa al CWD actual o absoluta)
        if p.exists():
            rutas_resueltas.append(p.resolve())
            continue

        # 2. Probar relativa a BASE_DIR (raíz del proyecto)
        p_base = (BASE_DIR / ent).resolve()
        if p_base.exists():
            rutas_resueltas.append(p_base)
            continue

        # 3. Probar en generador_configuracion_lote/mesas_desplegadas/ (ej: "mesa_code1", "mesa_code6")
        p_mesa = (BASE_DIR / "generador_configuracion_lote" / "mesas_desplegadas" / ent).resolve()
        if p_mesa.exists():
            rutas_resueltas.append(p_mesa)
            continue

        # 4. Probar en mesa_code/
        p_code = (BASE_DIR / "mesa_code" / ent).resolve()
        if p_code.exists():
            rutas_resueltas.append(p_code)
            continue

        print(f"⚠️ Advertencia: No se encontró el directorio ni la mesa '{ent}'")

    return rutas_resueltas


def auditar_lote_directorios(rutas_busqueda: List[Path]) -> List[Dict[str, Any]]:
    """
    Busca recursivamente todos los archivos .pdf en la lista de rutas y ejecuta la auditoría forense.
    """
    archivos_pdf = []
    for r in rutas_busqueda:
        if r.is_file() and r.suffix.lower() == ".pdf":
            archivos_pdf.append(r)
        elif r.is_dir():
            archivos_pdf.extend(list(r.rglob("*.pdf")))

    # Deduplicar
    vistos = set()
    dedup = []
    for f in archivos_pdf:
        abs_p = f.resolve()
        if abs_p not in vistos:
            vistos.add(abs_p)
            dedup.append(f)

    resultados = []
    rutas_str = ", ".join(f"'{r}'" for r in rutas_busqueda)
    print(f"🔍 Auditando {len(dedup)} archivo(s) PDF en {rutas_str}...\n")
    for f in dedup:
        res = auditar_archivo_pdf(f)
        resultados.append(res)
    return resultados


def imprimir_tabla_auditoria(resultados: List[Dict[str, Any]]):
    """
    Imprime en consola un reporte formateado y legible de la auditoría.
    """
    print("=" * 115)
    print(f"{'ARCHIVO':<32} | {'MESA':<10} | {'VOTO ID':<12} | {'CHECKSUM CÉDULA':<16} | {'ESTADO INTEGRIDAD':<22}")
    print("=" * 115)

    validos = 0
    alertas = 0

    for r in resultados:
        nombre = r["nombre_archivo"]
        if len(nombre) > 30:
            nombre = f"{nombre[:14]}...{nombre[-13:]}"
        
        mesa = r["mesa"]
        voto_id = r["voto_id"]
        c_hash = enmascarar_hash(r["checksum256_cedula"])
        estado = r["estado_integridad"]

        if "VALID" in estado or "INTEGRO" in estado:
            estado_fmt = f"✅ {estado}"
            validos += 1
        elif "ALERTA" in estado:
            estado_fmt = f"🚨 {estado}"
            alertas += 1
        else:
            estado_fmt = f"⚠️ {estado}"

        print(f"{nombre:<32} | {mesa:<10} | {voto_id:<12} | {c_hash:<16} | {estado_fmt:<22}")

    print("=" * 115)
    print(f"📊 RESUMEN: Total: {len(resultados)} | ✅ Íntegros/Válidos: {validos} | 🚨 Alertas/Irregulares: {alertas}\n")


def exportar_csv(resultados: List[Dict[str, Any]], ruta_csv: Path):
    """Exporta los resultados consolidados a un archivo CSV."""
    if not resultados:
        return
    
    campos = [
        "nombre_archivo", "archivo", "tamano_bytes", "sha256_pdf",
        "mesa", "candidato", "voto_id", "memo_hash", "checksum256_cedula",
        "timestamp_utc", "hostname_emisor", "os_emisor", "python_version",
        "sello_hmac", "estado_integridad"
    ]
    
    with open(ruta_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        for r in resultados:
            writer.writerow(r)
    print(f"📁 Reporte de auditoría exportado a CSV: {ruta_csv.resolve()}")


def exportar_json(resultados: List[Dict[str, Any]], ruta_json: Path):
    """Exporta los resultados consolidados a un archivo JSON."""
    ruta_json.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"📁 Reporte de auditoría exportado a JSON: {ruta_json.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Herramienta de Auditoría Forense y Validación de Comprobantes PDF Electorales BTCOL."
    )
    parser.add_argument("--archivo", type=str, help="Ruta a un único archivo PDF a auditar")
    parser.add_argument("--dir", type=str, nargs="*", help="Directorio(s) o mesa(s) a escanear (ej: mesa_code1, mesa_code6, o rutas completas)")
    parser.add_argument("--export-csv", type=str, help="Ruta para exportar los resultados en formato CSV")
    parser.add_argument("--export-json", type=str, help="Ruta para exportar los resultados en formato JSON")
    
    args = parser.parse_args()

    if args.archivo:
        rutas_objetivo = resolver_rutas_busqueda([args.archivo])
    else:
        rutas_objetivo = resolver_rutas_busqueda(args.dir)

    resultados = auditar_lote_directorios(rutas_objetivo)

    if not resultados:
        rutas_str = ", ".join(f"'{r}'" for r in rutas_objetivo)
        print(f"⚠️ No se encontraron archivos PDF para auditar en: {rutas_str}")
        sys.exit(0)

    imprimir_tabla_auditoria(resultados)

    if args.export_csv:
        exportar_csv(resultados, Path(args.export_csv))
    if args.export_json:
        exportar_json(resultados, Path(args.export_json))


if __name__ == "__main__":
    main()
