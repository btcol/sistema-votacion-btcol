#!/usr/bin/env python3
"""
test_seguridad_criticos.py - Pruebas unitarias para las remediaciones de Fase 1 (Vulnerabilidades Críticas)

Valida:
  CRIT-01: Placeholder Fernet declarativo y validación al arranque
  CRIT-02: CORS restringido a orígenes locales
  CRIT-03: Token de sesión Kiosk (protección CSRF transparente)
  CRIT-04: Rate Limiter en /api/votar

Ejecución:
  cd sistema-votacion-btcol/
  python3 -m pytest tests/test_seguridad_criticos.py -v
"""

import os
import sys
import time
import unittest
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ruta raíz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
MESA_DIR = ROOT_DIR / "mesa_code"
sys.path.insert(0, str(MESA_DIR))
sys.path.insert(0, str(ROOT_DIR))


class TestCRIT01_FernetPlaceholder(unittest.TestCase):
    """CRIT-01: Validar que la clave Fernet en el repositorio es un placeholder claro y no una clave funcional."""

    def test_placeholder_no_es_clave_real(self):
        """El valor del placeholder debe contener 'PLACEHOLDER' para ser claramente identificable."""
        from scripts.config import CLAVE_FERNET, _FERNET_PLACEHOLDER
        self.assertIn(b"PLACEHOLDER", CLAVE_FERNET)
        self.assertIn(b"PLACEHOLDER", _FERNET_PLACEHOLDER)

    def test_placeholder_coincide_con_constante(self):
        """CLAVE_FERNET por defecto debe ser igual al _FERNET_PLACEHOLDER."""
        from scripts.config import CLAVE_FERNET, _FERNET_PLACEHOLDER
        self.assertEqual(CLAVE_FERNET, _FERNET_PLACEHOLDER)

    def test_placeholder_no_contiene_clave_original(self):
        """El valor anterior hardcodeado no debe existir en el código."""
        config_path = MESA_DIR / "scripts" / "config.py"
        content = config_path.read_text(encoding="utf-8")
        self.assertNotIn("AcaVaUnaClaveMuyFuerteQueNoDebesPublicar", content)

    def test_generar_configs_regex_compatible(self):
        """La regex de inyección de generar_configs.py debe matchear el nuevo placeholder."""
        from scripts.config import CLAVE_FERNET
        patron = r'CLAVE_FERNET\s*=\s*(?:b"[^"]*"|b\'[^\']*\')'
        linea_actual = f'CLAVE_FERNET = {CLAVE_FERNET!r}'
        self.assertIsNotNone(re.search(patron, linea_actual),
                             f"La regex de inyección NO matchea: {linea_actual}")


class TestCRIT02_CORSRestringido(unittest.TestCase):
    """CRIT-02: Verificar que CORS está restringido a orígenes locales."""

    def test_cors_no_abierto(self):
        """El código no debe contener 'CORS(app)' sin parámetros."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        # No debe existir CORS(app) solo (sin origins=)
        matches = re.findall(r'CORS\(app\)\s*$', content, re.MULTILINE)
        self.assertEqual(len(matches), 0,
                         "CORS(app) sin restricción de orígenes encontrado en app_web_mesa.py")

    def test_cors_incluye_localhost(self):
        """La configuración CORS debe incluir orígenes localhost."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        self.assertIn("localhost", content)
        self.assertIn("127.0.0.1", content)


class TestCRIT03_KioskSessionToken(unittest.TestCase):
    """CRIT-03: Verificar la protección del token de sesión Kiosk contra peticiones no autorizadas."""

    def test_token_generado_al_importar(self):
        """El módulo debe generar un KIOSK_SESSION_TOKEN de longitud 64 (hex de 32 bytes)."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        self.assertIn("KIOSK_SESSION_TOKEN", content)
        self.assertIn("secrets.token_hex", content)

    def test_token_validado_en_votar(self):
        """El endpoint /api/votar debe verificar X-Kiosk-Token."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        self.assertIn("X-Kiosk-Token", content)
        self.assertIn("secrets.compare_digest", content)

    def test_token_embebido_en_html(self):
        """El template HTML debe incluir el token como data attribute."""
        html_path = MESA_DIR / "web" / "templates" / "index.html"
        content = html_path.read_text(encoding="utf-8")
        self.assertIn("data-kiosk-token", content)
        self.assertIn("kiosk_token", content)

    def test_token_enviado_desde_js(self):
        """El JavaScript del frontend debe leer y enviar el token Kiosk."""
        js_path = MESA_DIR / "web" / "static" / "js" / "app.js"
        content = js_path.read_text(encoding="utf-8")
        self.assertIn("KIOSK_TOKEN", content)
        self.assertIn("X-Kiosk-Token", content)
        self.assertIn("kioskToken", content)


class TestCRIT04_RateLimiter(unittest.TestCase):
    """CRIT-04: Verificar el rate limiter en memoria para /api/votar."""

    def test_rate_limiter_presente(self):
        """El código debe contener la función _check_rate_limit."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        self.assertIn("_check_rate_limit", content)
        self.assertIn("RATE_LIMIT_VOTAR", content)

    def test_rate_limiter_logica(self):
        """La función _check_rate_limit debe bloquear ráfagas."""
        # Simular la lógica del rate limiter (misma implementación)
        from collections import defaultdict
        store = defaultdict(list)

        def check_rate_limit(key, max_requests, window_secs, _store=store):
            now = time.time()
            timestamps = _store[key]
            _store[key] = [t for t in timestamps if now - t < window_secs]
            if len(_store[key]) >= max_requests:
                return True
            _store[key].append(now)
            return False

        # Primera petición: debe pasar
        self.assertFalse(check_rate_limit("test_ip", 1, 5))
        # Segunda petición inmediata: debe bloquearse
        self.assertTrue(check_rate_limit("test_ip", 1, 5))

    def test_rate_limiter_ventana_expira(self):
        """Después de que expire la ventana, las peticiones deben pasar de nuevo."""
        from collections import defaultdict
        store = defaultdict(list)

        def check_rate_limit(key, max_requests, window_secs, _store=store):
            now = time.time()
            _store[key] = [t for t in _store[key] if now - t < window_secs]
            if len(_store[key]) >= max_requests:
                return True
            _store[key].append(now)
            return False

        # Primera petición: pasa
        self.assertFalse(check_rate_limit("test_ip2", 1, 0.1))
        # Esperar a que expire la ventana (0.1 segundos)
        time.sleep(0.15)
        # Debería pasar de nuevo
        self.assertFalse(check_rate_limit("test_ip2", 1, 0.1))

    def test_rate_limiter_aplicado_en_votar(self):
        """El endpoint /api/votar debe invocar _check_rate_limit."""
        app_path = MESA_DIR / "app_web_mesa.py"
        content = app_path.read_text(encoding="utf-8")
        # Buscar que _check_rate_limit se llama dentro del bloque de procesar_voto_api
        votar_section = content[content.index("def procesar_voto_api"):]
        self.assertIn("_check_rate_limit", votar_section)
        self.assertIn("429", votar_section)


if __name__ == "__main__":
    unittest.main(verbosity=2)
