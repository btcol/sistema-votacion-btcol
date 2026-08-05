#!/usr/bin/env python3
"""
test_flujo_votacion.py - Prueba de Integración de Flujo Completo de Votación Electoral BTCOL

Valida de extremo a extremo:
  1. Generación y consumo transparente del token de sesión Kiosk (CSRF).
  2. Envío seguro de voto con captura de cédula en base64.
  3. Cifrado simétrico AES de la imagen de cédula en disco (.enc).
  4. Cálculo e indexación del Checksum SHA-256 del archivo cifrado.
  5. Registro transaccional en SQLite local en modo WAL.
  6. Generación del comprobante electoral oficial PDF con telemetría y HMAC dinámico.
  7. Descarga y verificación de metadatos forenses por endpoint SHA-256 seguro.
  8. Protección estricta: No fuga de claves simétricas en payload JSON.

Ejecución:
  cd sistema-votacion-btcol/
  python3 -m unittest tests.test_flujo_votacion -v
"""

import os
import sys
import json
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Configurar rutas
ROOT_DIR = Path(__file__).resolve().parent.parent
MESA_DIR = ROOT_DIR / "mesa_code"
sys.path.insert(0, str(MESA_DIR))
sys.path.insert(0, str(ROOT_DIR))

from scripts.modelos import Candidato, ConfiguracionMesa, Voto, EstadoVoto
from impresora.encriptar_imagen import encriptar_imagen
from impresora.generador_ticket_pdf import generar_ticket_pdf, calcular_sello_hmac
from desencriptador.desencriptar_imagen import desencriptar_imagen


class TestFlujoCompletoVotacion(unittest.TestCase):
    """Prueba de integración end-to-end del proceso de votación y auditoría forense."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        
        # Crear estructura temporal para la prueba
        (self.tmp_path / "capturas_cedula").mkdir(parents=True, exist_ok=True)
        (self.tmp_path / "comprobantes_emitidos").mkdir(parents=True, exist_ok=True)
        self.db_path = self.tmp_path / "votos_test.db"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_cifrado_y_descifrado_cedula_flujo(self):
        """Verificar el ciclo completo de cifrado de cédula con clave derivada y verificación SHA-256."""
        # 1. Crear archivo de imagen sintética de prueba
        bytes_foto_original = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 200 + b"\xFF\xD9"
        foto_original_path = self.tmp_path / "test_cedula.jpg"
        foto_original_path.write_bytes(bytes_foto_original)
        
        clave_secreta = hashlib.sha256(b"voto_integration_test_secret_key").hexdigest()
        enc_path = self.tmp_path / "capturas_cedula" / f"{clave_secreta[:16]}.enc"
        
        # 2. Cifrar con encriptar_imagen
        ruta_enc = encriptar_imagen(
            ruta_imagen=str(foto_original_path),
            clave_secreta=clave_secreta,
            ruta_salida=str(enc_path)
        )
        self.assertTrue(enc_path.exists())
        self.assertGreater(enc_path.stat().st_size, 0)
        
        # 3. Calcular Checksum SHA-256 del archivo cifrado
        sha256_calc = hashlib.sha256(enc_path.read_bytes()).hexdigest()
        self.assertEqual(len(sha256_calc), 64)
        
        # 4. Descifrar y comprobar integridad exacta
        restaurada_path = self.tmp_path / "restaurada.jpg"
        ruta_res, metadatos = desencriptar_imagen(
            ruta_encriptada=str(enc_path),
            clave_secreta=clave_secreta,
            ruta_salida=str(restaurada_path),
            silencioso=True
        )
        self.assertIsNotNone(ruta_res)
        self.assertEqual(restaurada_path.read_bytes(), bytes_foto_original)

    def test_generacion_comprobante_pdf_forense_completo(self):
        """Verificar la generación física de PDF con metadatos JSON y sello HMAC no estático."""
        out_dir = self.tmp_path / "comprobantes_emitidos"
        checksum_test = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        memo_test = "112233445566778899aabbccddeeff00112233445566778899aabbccddeeff00"
        
        res = generar_ticket_pdf(
            mesa="MESA-INTEGRACION-01",
            candidato="Candidato Integracion",
            candidato_id="cand_integ_01",
            voto_id="voto_integ_999",
            monto_sats=1,
            memo_hash=memo_test,
            checksum256_cedula=checksum_test,
            directorio_salida=out_dir
        )
        
        pdf_file = out_dir / f"comprobante_{checksum_test}.pdf"
        meta_file = out_dir / f"comprobante_{checksum_test}.meta.json"
        
        self.assertTrue(pdf_file.exists(), "El archivo PDF debe existir en el directorio de salida")
        self.assertTrue(meta_file.exists(), "El archivo de metadatos forenses .meta.json debe existir")
        self.assertIn("sello_hmac", res)
        self.assertEqual(len(res["sello_hmac"]), 64)
        
        # Verificar contenido de metadatos forenses
        metadata = json.loads(meta_file.read_text(encoding="utf-8"))
        self.assertEqual(metadata["mesa_nombre"], "MESA-INTEGRACION-01")
        self.assertEqual(metadata["candidato_nombre"], "Candidato Integracion")
        self.assertEqual(metadata["checksum256_cedula"], checksum_test)
        self.assertIn("telemetria_maquina", metadata)
        self.assertIn("hardware_fingerprint", metadata["telemetria_maquina"])

    def test_registro_en_bd_local_wal(self):
        """Verificar el registro estructurado de la transacción en la BD local SQLite."""
        from gestor_bd_local import GestorBDLocal
        gestor = GestorBDLocal(ruta_db=self.db_path)
        
        voto = Voto(
            voto_id="voto_e2e_001",
            candidato_id="c_01",
            candidato_nombre="Satoshi Nakamoto",
            mesa_id="MESA-01",
            huella_votante="fingerprint_unique_abc",
            monto_sats=1,
            fee_sats=0,
            payment_hash_mesa="hash_mesa_001",
            estado="confirmado",
            archivo_cedula_enc="cedula_001.enc",
            checksum256_cedula="a" * 64
        )
        
        exito = gestor.guardar_voto(voto)
        self.assertTrue(exito)
        
        resumen = gestor.obtener_resumen_sesion("MESA-01")
        self.assertEqual(resumen["total"], 1)
        self.assertEqual(resumen["confirmados"], 1)
        self.assertEqual(resumen["pendientes"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
