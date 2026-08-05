#!/usr/bin/env python3
"""
test_seguridad_medias.py - Pruebas unitarias para las remediaciones de Fase 3 (Vulnerabilidades Medias y Hardening)

Valida:
  MED-01: SQLite WAL Mode, Synchronous Normal y Busy Timeout
  MED-02: Hardening de plantilla Docker Compose (eliminación de password por defecto)
  MED-03 & LOW-02: Security Headers (CSP, X-Content-Type-Options, X-Frame-Options, MAX_CONTENT_LENGTH)

Ejecución:
  cd sistema-votacion-btcol/
  python3 -m unittest tests.test_seguridad_medias -v
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Ruta raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
MESA_DIR = ROOT_DIR / "mesa_code"
sys.path.insert(0, str(MESA_DIR))
sys.path.insert(0, str(ROOT_DIR))


class TestMED01_SQLiteWAL(unittest.TestCase):
    """MED-01: Validar configuración de persistencia y concurrencia SQLite (WAL mode)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_votos.db"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_wal_mode_habilitado(self):
        """La conexión debe ejecutar journal_mode=WAL y synchronous=NORMAL."""
        from gestor_bd_local import GestorBDLocal
        gestor = GestorBDLocal(ruta_db=self.db_path)
        
        with gestor._get_conexion() as conn:
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            sync_mode = conn.execute("PRAGMA synchronous;").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]

            self.assertEqual(journal_mode.lower(), "wal")
            # synchronous=NORMAL es 1 en SQLite
            self.assertIn(sync_mode, [1, "1", "NORMAL", "normal"])
            self.assertGreaterEqual(busy_timeout, 1000)

    def test_insercion_voto_en_wal(self):
        """Verificar que un voto se guarda y lee correctamente en modo WAL."""
        from gestor_bd_local import GestorBDLocal
        from scripts.modelos import Voto
        gestor = GestorBDLocal(ruta_db=self.db_path)
        
        voto = Voto(
            voto_id="test_wal_001",
            candidato_id="cand_1",
            candidato_nombre="Candidato Test",
            mesa_id="MESA-01",
            huella_votante="fingerprint_test_wal",
            estado="confirmado"
        )
        guardado = gestor.guardar_voto(voto)
        self.assertTrue(guardado)
        
        votos = gestor.obtener_votos_sin_sincronizar()
        self.assertEqual(len(votos), 1)
        self.assertEqual(votos[0].voto_id, "test_wal_001")
        self.assertEqual(votos[0].candidato_nombre, "Candidato Test")


class TestMED02_DockerHardening(unittest.TestCase):
    """MED-02: Verificar eliminación de contraseñas por defecto en plantillas Docker."""

    def test_docker_compose_sin_password_hardcodeado(self):
        """setup_inicial.py no debe contener changeme_production como password."""
        setup_path = MESA_DIR / "scripts" / "setup_inicial.py"
        content = setup_path.read_text(encoding="utf-8")
        self.assertNotIn("POSTGRES_PASSWORD: changeme_production", content)
        self.assertIn("${POSTGRES_PASSWORD", content)


class TestMED03_SecurityHeaders(unittest.TestCase):
    """MED-03 & LOW-02: Verificar cabeceras de seguridad y límites de payload en Flask."""

    def test_security_headers_presentes(self):
        """Las respuestas HTTP deben incluir CSP, X-Content-Type-Options y X-Frame-Options."""
        from app_web_mesa import app
        client = app.test_client()
        
        # Probar endpoint público /api/candidatos o raíz
        resp = client.get("/api/candidatos")
        headers = resp.headers
        
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy"))

    def test_max_content_length_configurado(self):
        """MAX_CONTENT_LENGTH debe estar fijado a 16MB para mitigar saturación de memoria."""
        from app_web_mesa import app
        self.assertEqual(app.config.get("MAX_CONTENT_LENGTH"), 16 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
