#!/usr/bin/env python3
"""
=============================================================================
Sistema de Votación BTCOL - Módulo de Auditoría y Desencriptación
Script: desencriptar_imagen.py
Descripción: Desencripta un archivo cifrado simétricamente (.enc), recupera
             los metadatos (dimensiones, formato, fecha) y restaura la imagen
             original bit por bit.
=============================================================================
"""

import argparse
import base64
import json
import os
import sys

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    print("❌ Error: La librería 'cryptography' no está instalada.")
    print("💡 Puedes instalarla ejecutando: pip install cryptography")
    sys.exit(1)


def derivar_clave_simetrica(password: str, salt: bytes) -> Fernet:
    """
    Deriva la clave simétrica de 256 bits mediante PBKDF2 (HMAC-SHA256)
    usando la contraseña en texto plano y el Salt leído del archivo cifrado.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key_b64 = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return Fernet(key_b64)


def desencriptar_imagen(ruta_encriptada: str, clave_secreta: str, ruta_salida: str = None, silencioso: bool = False) -> tuple:
    """
    Desencripta un archivo .enc, valida la clave simétrica, recupera los metadatos
    y guarda la imagen original recuperada.

    Retorna:
      - (ruta_imagen_restaurada, diccionario_metadatos)
    """
    if not os.path.exists(ruta_encriptada):
        if not silencioso:
            print(f"❌ Error: El archivo encriptado '{ruta_encriptada}' no existe.")
        return None, None

    if not silencioso:
        print("\n" + "=" * 65)
        print("🔓 DESENCRIPTADOR SIMÉTRICO DE IMÁGENES & RECONSTRUCTOR DE METADATOS")
        print("=" * 65)
        print(f"📦 Archivo cifrado origen: {ruta_encriptada}")

    # 1. Leer el archivo binario completo
    with open(ruta_encriptada, "rb") as f:
        contenido_archivo = f.read()

    if len(contenido_archivo) < 16:
        if not silencioso:
            print("❌ Error: El archivo cifrado es demasiado pequeño o está corrupto.")
        return None, None

    # 2. Extraer el Salt (primeros 16 bytes) y el cuerpo cifrado
    salt = contenido_archivo[:16]
    cuerpo_cifrado = contenido_archivo[16:]

    # 3. Derivar la clave simétrica y desencriptar
    try:
        fernet = derivar_clave_simetrica(clave_secreta, salt)
        contenedor_plano = fernet.decrypt(cuerpo_cifrado)
    except InvalidToken:
        if not silencioso:
            print("\n" + "❌" * 35)
            print("❌ ERROR DE DESENCRIPTACIÓN: La clave ingresada ES INCORRECTA.")
            print("🔑 La encriptación simétrica requiere EXACTAMENTE la misma clave con la que fue cifrado.")
            print("❌" * 35 + "\n")
        return None, None
    except Exception as e:
        if not silencioso:
            print(f"❌ Error inesperado al desencriptar: {e}")
        return None, None

    # 4. Desempaquetar contenedor: [4 bytes tamaño JSON] + [JSON metadatos] + [Bytes imagen]
    tamanio_json = int.from_bytes(contenedor_plano[:4], byteorder="big")
    json_bytes = contenedor_plano[4 : 4 + tamanio_json]
    bytes_imagen_recuperada = contenedor_plano[4 + tamanio_json :]

    # 5. Parsear metadatos JSON recuperados
    metadatos = json.loads(json_bytes.decode("utf-8"))

    if not silencioso:
        print("\n📊 METADATOS RECUPERADOS DEL ARCHIVO ENCRIPTADO:")
        print(f"   • Nombre Original:     {metadatos.get('nombre_archivo_original', 'N/A')}")
        print(f"   • Dimensiones Imagen:  {metadatos.get('ancho_px', 0)} x {metadatos.get('alto_px', 0)} px")
        print(f"   • Canales / Tipo:      {metadatos.get('canales', 1)} canales ({metadatos.get('dtype', 'uint8')})")
        print(f"   • Tamaño Original:     {metadatos.get('tamanio_bytes_original', len(bytes_imagen_recuperada))} bytes")
        print(f"   • Fecha Encriptación:  {metadatos.get('timestamp_encriptacion', 'N/A')}")

    # 6. Determinar ruta de salida
    if not ruta_salida:
        nombre_orig = metadatos.get("nombre_archivo_original", "imagen_restaurada.jpg")
        directorio_recuperadas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cedulas_desencriptadas")
        os.makedirs(directorio_recuperadas, exist_ok=True)
        ruta_salida = os.path.join(directorio_recuperadas, f"restaurada_{nombre_orig}")

    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)

    # 7. Escribir los bytes de la imagen original recuperada
    with open(ruta_salida, "wb") as f:
        f.write(bytes_imagen_recuperada)

    if not silencioso:
        verificacion_bytes = (len(bytes_imagen_recuperada) == metadatos.get("tamanio_bytes_original", len(bytes_imagen_recuperada)))
        print("\n" + "✅" * 30)
        print("🎉 ¡Imagen desencriptada y recuperada exitosamente!")
        print(f"🖼️ Imagen restaurada en: {ruta_salida}")
        print(f"🔍 Integridad comprobada bit por bit: {'✅ CORRECTA' if verificacion_bytes else '⚠️ VARIACIÓN DE TAMAÑO'}")
        print("✅" * 30 + "\n")

    return ruta_salida, metadatos


def main():
    parser = argparse.ArgumentParser(
        description="Script para desencriptar un archivo cifrado y recuperar la imagen original y sus metadatos."
    )
    parser.add_argument(
        "-i", "--input", type=str, required=True,
        help="Ruta del archivo encriptado (.enc)"
    )
    parser.add_argument(
        "-k", "--key", type=str, required=True,
        help="Clave secreta simétrica utilizada al encriptar"
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Ruta donde guardar la imagen restaurada (opcional)"
    )

    args = parser.parse_args()

    desencriptar_imagen(
        ruta_encriptada=args.input,
        clave_secreta=args.key,
        ruta_salida=args.output
    )


if __name__ == "__main__":
    main()
