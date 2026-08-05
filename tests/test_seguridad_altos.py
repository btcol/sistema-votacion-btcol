#!/usr/bin/env python3
"""
test_seguridad_altos.py - Pruebas unitarias para las remediaciones de Fase 2 (Vulnerabilidades Altas)

Valida:
  HIGH-01: Validación regex estricta de SHA-256 en /api/comprobante (previene path traversal)
  HIGH-02: Host binding por defecto seguro a localhost (127.0.0.1)
  HIGH-03: Semilla HMAC dinámica (eliminación de secreto estático)
  HIGH-04: Sanitización XSS en frontend
  HIGH-05: Truncamiento / enmascaramiento de payment_hash en respuesta JSON

Ejecución:
  cd sistema-votacion-btcol/
  python3 -m unittest tests.test_seguridad_altos -v
"""

import os
import sys
import unittest
import re
from pathlib import Path

# Ruta raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
MESA_DIR = ROOT_DIR / "mesa_code"
sys.path.insert(0, str(MESA_DIR))
sys.path.insert(0, str(ROOT_DIR))


class TestHIGH01_PathTraversal(unittest.TestCase):
    """HIGH-01: Validación regex estricta de SHA-256 para prevenir path traversal en comprobantes."""

    def test_regex_sha256_definido(self):
        """REGEX_SHA256 debe estar definido y validar exactamente 64 caracteres hexadecimales."""
        from app_web_mesa import REGEX_SHA256
        self.assertIsNotNone(REGEX_SHA256)
        # Hash válido de 64 hex
        valido = "a" * 64
        self.assertTrue(bool(REGEX_SHA256.match(valido)))
        
        # Inyecciones y path traversal deben fallar
        self.assertFalse(bool(REGEX_SHA256.match("../../etc/passwd")))
        self.assertFalse(bool(REGEX_SHA256.match("..\\..\\windows\\win.ini")))
        self.assertFalse(bool(REGEX_SHA256.match("a" * 63)))  # Demasiado corto
        self.assertFalse(bool(REGEX_SHA256.match("a" * 65)))  # Demasiado largo
        self.assertFalse(bool(REGEX_SHA256.match("g" * 64)))  # Caracter no hexadecimal
        self.assertFalse(bool(REGEX_SHA256.match("")))

    def test_endpoints_comprobante_usan_regex(self):
        """Los endpoints de comprobantes deben validar el parámetro con REGEX_SHA256."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        
        self.assertIn("REGEX_SHA256", content)
        self.assertIn("Checksum SHA-256 inválido", content)


class TestHIGH02_HostBinding(unittest.TestCase):
    """HIGH-02: Verificar que el host por defecto en los servidores Flask es localhost (127.0.0.1)."""

    def test_app_web_mesa_host_default(self):
        """app_web_mesa.py debe usar 127.0.0.1 por defecto."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        self.assertIn('HOST = os.getenv("MESA_WEB_HOST") or "127.0.0.1"', content)

    def test_votos_dashboard_host_default(self):
        """votos_dashboard.py debe usar 127.0.0.1 por defecto en argparse."""
        dash_path = ROOT_DIR / "frontend" / "votos_dashboard.py"
        content = dash_path.read_text(encoding="utf-8")
        self.assertIn('default=os.getenv("DASHBOARD_HOST", "127.0.0.1")', content)

    def test_auditoria_host_default(self):
        """auditoria_ln_votos.py debe usar 127.0.0.1 por defecto en argparse."""
        audit_path = ROOT_DIR / "audit" / "auditoria_ln_votos.py"
        content = audit_path.read_text(encoding="utf-8")
        self.assertIn('default=os.getenv("AUDIT_HOST", "127.0.0.1")', content)


class TestHIGH03_HMACDinamico(unittest.TestCase):
    """HIGH-03: Verificar que el cálculo de HMAC forense usa semilla dinámica sin secreto estático."""

    def test_sin_secreto_estatico(self):
        """El generador de PDF no debe contener 'btcol-forensic-secret'."""
        pdf_path = MESA_DIR / "impresora" / "generador_ticket_pdf.py"
        content = pdf_path.read_text(encoding="utf-8")
        self.assertNotIn("btcol-forensic-secret", content)

    def test_sello_hmac_es_unico_por_voto(self):
        """calcular_sello_hmac debe generar sellos distintos para diferentes votos o timestamps."""
        from impresora.generador_ticket_pdf import calcular_sello_hmac
        
        datos1 = {"voto_id": "voto_001", "timestamp_iso_utc": "2026-08-05T12:00:00Z", "mesa": "MESA-1"}
        datos2 = {"voto_id": "voto_002", "timestamp_iso_utc": "2026-08-05T12:00:01Z", "mesa": "MESA-1"}
        
        sello1 = calcular_sello_hmac(datos1)
        sello2 = calcular_sello_hmac(datos2)
        
        self.assertNotEqual(sello1, sello2)
        self.assertEqual(len(sello1), 64)  # SHA-256 hex length
        self.assertEqual(len(sello2), 64)


class TestHIGH04_XSSSanitization(unittest.TestCase):
    """HIGH-04: Verificar funciones de sanitización XSS en el frontend."""

    def test_escape_html_definido_en_app_js(self):
        """app.js debe definir la función escapeHtml."""
        js_path = MESA_DIR / "web" / "static" / "js" / "app.js"
        content = js_path.read_text(encoding="utf-8")
        self.assertIn("function escapeHtml", content)
        self.assertIn(".replace(/&/g, \"&amp;\")", content)
        self.assertIn(".replace(/</g, \"&lt;\")", content)

    def test_render_candidates_usa_escape(self):
        """renderCandidates en app.js debe usar escapeHtml para nombres de candidatos."""
        js_path = MESA_DIR / "web" / "static" / "js" / "app.js"
        content = js_path.read_text(encoding="utf-8")
        self.assertIn("escapeHtml(c.nombre)", content)


class TestHIGH05_PaymentHashTruncated(unittest.TestCase):
    """HIGH-05: Verificar que payment_hash no se expone completo en el JSON de respuesta."""

    def test_payment_hash_preview_en_api(self):
        """app_web_mesa.py debe enviar payment_hash truncado/enmascarado en la respuesta JSON."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        self.assertIn("payment_hash_preview", content)
        self.assertIn("f\"{payment_hash[:16]}...\"", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
