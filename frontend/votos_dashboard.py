"""
votos_dashboard.py - Dashboard Web de Monitoreo Electoral en Tiempo Real (Soporta Tor .onion)

Servidor web Flask read-only para visualizar los votos, saldos de candidato y mesas electorales
en tiempo real a través de transacciones Bitcoin Lightning Network.

Uso por Administradores Autorizados:
    python3 frontend/votos_dashboard.py --fernet-key "TU_CLAVE_FERNET_CUSTOM_BASE64="

⚠️ ADVERTENCIA DE SEGURIDAD PARA ADMINISTRADORES:
La clave criptográfica Fernet permite descifrar en memoria la configuración de monitoreo (wallets.json.enc).
Las claves Fernet contienen información delicada y deben ser custodiadas y manejadas estrictamente por
los administradores autorizados del proceso electoral.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import os
import argparse
from pathlib import Path
import time
import threading
from typing import Dict, List, Optional
from cryptography.fernet import Fernet, InvalidToken

import sys
from flask import Flask, render_template_string, jsonify, request, send_file
from flask_cors import CORS
import requests

# Directorio raíz del proyecto (2 niveles arriba desde frontend/)
BASE_DIR = Path(__file__).resolve().parent.parent  # frontend/ -> raíz
DATA_DIR = BASE_DIR / "data"
GEN_DIR = BASE_DIR / "generador_configuracion_lote"

sys.path.insert(0, str(BASE_DIR / "mesa_code"))
from scripts.monitor_ws import MonitorWebSocket
from scripts.seguridad_logs import (
    enmascarar_url,
    enmascarar_key,
    enmascarar_hash,
    sanitizar_texto,
    resolver_clave_fernet,
    extraer_clave_fernet_md
)


def obtener_clave_fernet_activa(clave_custom: Optional[str] = None) -> bytes:
    """
    Resuelve la clave Fernet dando prioridad a:
    1. --fernet-key (Argumento CLI)
    2. FERNET_KEY (Variable de Entorno)
    3. generador_configuracion_lote/config_global.md
    """
    return resolver_clave_fernet(clave_custom=clave_custom, md_path=GEN_DIR / "config_global.md")


def normalize_wallets_dict(raw_data) -> Dict[str, Dict]:
    """
    Convierte cualquier sección (sea lista u objeto) en un diccionario unificado
    donde la clave es el ID de la wallet. Soporta el formato idéntico de candidatos.json.
    """
    normalized = {}
    if isinstance(raw_data, list):
        for item in raw_data:
            w_id = item.get("id") or item.get("wallet_id")
            if w_id:
                disp_name = item.get("nombre") or item.get("display_name") or w_id
                inv_key = item.get("api_key") or item.get("invoice_key") or ""
                normalized[w_id] = {
                    "id": w_id,
                    "wallet_id": item.get("wallet_id", w_id),
                    "invoice_key": inv_key,
                    "api_key": inv_key,
                    "display_name": disp_name,
                    "nombre": disp_name,
                    "url_lnbits": item.get("url_lnbits", ""),
                    "foto_local": item.get("foto_local", "")
                }
    elif isinstance(raw_data, dict):
        for k, v in raw_data.items():
            disp_name = v.get("display_name") or v.get("nombre") or k
            inv_key = v.get("invoice_key") or v.get("api_key") or ""
            normalized[k] = {
                "id": k,
                "wallet_id": v.get("wallet_id", k),
                "invoice_key": inv_key,
                "api_key": inv_key,
                "display_name": disp_name,
                "nombre": disp_name,
                "url_lnbits": v.get("url_lnbits", ""),
                "foto_local": v.get("foto_local", "")
            }
    return normalized


def load_wallets_config(clave_custom: Optional[str] = None) -> Dict:
    """
    Carga y descifra la configuración de wallets desde wallets.json.enc (o wallets.json como fallback).
    Prioriza data/wallets.json.enc y generador_configuracion_lote/wallets.json.enc.
    """
    clave_bytes = obtener_clave_fernet_activa(clave_custom)
    
    rutas_enc = [
        DATA_DIR / "wallets.json.enc",
        GEN_DIR / "wallets.json.enc"
    ]
    rutas_json = [
        DATA_DIR / "wallets.json",
        GEN_DIR / "wallets.json"
    ]
    
    data = None
    
    for enc_p in rutas_enc:
        if enc_p.exists():
            try:
                fernet = Fernet(clave_bytes)
                bytes_cifrados = enc_p.read_bytes()
                texto_descifrado = fernet.decrypt(bytes_cifrados).decode('utf-8')
                data = json.loads(texto_descifrado)
                print(f"🔓 Dashboard descifró exitosamente: {enc_p.relative_to(BASE_DIR)}")
                break
            except InvalidToken:
                print(f"❌ Error de descifrado en {enc_p.name}: Clave Fernet inválida.")
                raise ValueError(f"Clave Fernet no válida para descifrar {enc_p.name}")
            except Exception as e:
                print(f"⚠️ Error leyendo {enc_p.name}: {e}")

    if data is None:
        for json_p in rutas_json:
            if json_p.exists():
                try:
                    with open(json_p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        print(f"📄 Dashboard cargó config en texto plano desde: {json_p.relative_to(BASE_DIR)}")
                        break
                except Exception as e:
                    print(f"⚠️ Error leyendo {json_p.name}: {e}")

    if data is None:
        raise FileNotFoundError(
            f"No se encontró wallets.json.enc ni wallets.json en {DATA_DIR} ni en {GEN_DIR}"
        )

    return {
        "settings": data.get("settings", {}),
        "candidatos": normalize_wallets_dict(data.get("candidatos", [])),
        "mesas": normalize_wallets_dict(data.get("mesas", []))
    }


# Cargar configuración unificada desde JSON o JSON.ENC
try:
    WALLETS_CONFIG = load_wallets_config()
except (FileNotFoundError, ValueError) as e:
    print(f"❌ Error al cargar configuración en el Dashboard: {e}")
    WALLETS_CONFIG = {"settings": {}, "candidatos": {}, "mesas": {}}

SETTINGS = WALLETS_CONFIG.get("settings", {})

# Parámetros Globales (Single Source of Truth: data/wallets.json)
LNBITS_ENDPOINT = (os.getenv("LNBITS_ENDPOINT") or SETTINGS.get("url_lnbits") or "http://localhost:5050").rstrip("/")
SATS_PER_VOTE = int(os.getenv("SATS_PER_VOTE") or SETTINGS.get("sats_per_vote", 100))
SHOW_SATS_AND_VOTES = SETTINGS.get("show_sats_and_votes", True)
FLASK_PORT = int(os.getenv("FLASK_PORT") or SETTINGS.get("puerto_web", 5050))
REQUEST_TIMEOUT = 15  # Timeout adaptado para respuestas por la red Tor


# ============================================================================
# MODELOS DE DATOS
# ============================================================================


class WalletType(str, Enum):
    """Tipo de wallet"""
    CANDIDATO = "candidato"
    MESA = "mesa"


@dataclass
class VoteInfo:
    """Información de votos y sats"""
    votos: int
    sats: int
    sats_remainder: int

    def __post_init__(self):
        if self.sats < 0 or self.votos < 0:
            raise ValueError("Votos y sats deben ser >= 0")


@dataclass
class WalletDetails:
    """Información de una wallet"""
    name: str
    display_name: str
    wallet_type: WalletType
    balance: int  # en satoshis
    vote_info: VoteInfo
    invoice_key: str
    last_update: str
    is_available: bool
    foto_url: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class Payment:
    """Información de un pago/invoice"""
    payment_hash: str
    amount: int
    memo: Optional[str]
    paid: bool
    date: str


# ============================================================================
# CLIENTE API DE LNBITS (SOPORTE TOR NATIVO)
# ============================================================================


class LNBitsClient:
    """Cliente read-only para interactuar con la API de LNBits (Soporta Tor .onion)"""

    def __init__(self, endpoint: str, invoice_key: str, timeout: int = 15):
        self.endpoint = endpoint.rstrip("/")
        self.invoice_key = invoice_key
        self.timeout = timeout

    def _get_proxies(self, url: str) -> Optional[Dict[str, str]]:
        """Retorna proxies SOCKS5h si la URL es un dominio .onion de Tor"""
        if ".onion" in url:
            return {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050"
            }
        return None

    def _make_request(self, method: str, path: str, **kwargs) -> Optional[Dict]:
        """Realiza una request a la API de LNBits (con soporte Tor)"""
        url = f"{self.endpoint}{path}"
        headers = {"X-Api-Key": self.invoice_key, "Content-Type": "application/json"}
        proxies = self._get_proxies(url)

        try:
            if method.upper() == "GET":
                response = requests.get(
                    url, headers=headers, proxies=proxies, timeout=self.timeout, **kwargs
                )
            else:
                raise ValueError(f"Método HTTP no soportado en modo read-only: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout en {path} ({enmascarar_url(url)})")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Error de conexión a {enmascarar_url(url)}: {sanitizar_texto(str(e))}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error HTTP {e.response.status_code} en {path}: {sanitizar_texto(str(e))}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en request: {sanitizar_texto(str(e))}")
            return None
        except json.JSONDecodeError:
            print(f"❌ Respuesta no es JSON válido")
            return None

    def get_wallet_details(self) -> Optional[Dict]:
        return self._make_request("GET", "/api/v1/wallet")

    def get_payments(self, limit: int = 50) -> Optional[Dict]:
        return self._make_request("GET", f"/api/v1/payments?limit={limit}")


# ============================================================================
# LÓGICA DE NEGOCIO Y MONITOR
# ============================================================================


class VoteConverter:
    """Convertidor de sats a votos"""
    def __init__(self, sats_per_vote: int):
        self.sats_per_vote = sats_per_vote

    def convert(self, sats: int) -> VoteInfo:
        votos = sats // self.sats_per_vote
        sats_remainder = sats % self.sats_per_vote
        return VoteInfo(votos=votos, sats=sats, sats_remainder=sats_remainder)


class WalletMonitor:
    """Monitor de wallets de LNBits"""

    def __init__(self, endpoint: str, wallets_config: Dict):
        self.endpoint = endpoint
        self.wallets_config = {
            "candidatos": wallets_config.get("candidatos", {}),
            "mesas": wallets_config.get("mesas", {})
        }
        self.clients: Dict[str, LNBitsClient] = {}
        self.ws_monitors: Dict[str, MonitorWebSocket] = {}
        self.vote_converter = VoteConverter(SATS_PER_VOTE)
        self._init_clients()
        self._start_background_sync()

    def _start_background_sync(self):
        """
        Inicia un hilo en segundo plano que fuerza la actualización de todas las wallets
        cada 15 segundos. Esto es necesario porque:
        1. LNbits no envía eventos WS para pagos salientes (así que las mesas no se actualizan solas).
        2. Sirve de fallback robusto por si la conexión WS de algún candidato se retrasa o cae.
        """
        def _sync_loop():
            while True:
                time.sleep(15)
                for name, monitor in self.ws_monitors.items():
                    try:
                        monitor.forzar_actualizacion_saldo()
                    except Exception as e:
                        print(f"Error forzando actualización de {name}: {sanitizar_texto(str(e))}")

        threading.Thread(target=_sync_loop, daemon=True, name="DashboardSync").start()

    def _init_clients(self):
        for wallet_type in ["candidatos", "mesas"]:
            if wallet_type not in self.wallets_config:
                continue

            for wallet_name, wallet_info in self.wallets_config[wallet_type].items():
                invoice_key = wallet_info.get("invoice_key") or wallet_info.get("api_key")
                wallet_id = wallet_info.get("wallet_id") or wallet_info.get("id")
                
                if invoice_key:
                    # Cliente HTTP para historial de pagos
                    self.clients[wallet_name] = LNBitsClient(
                        self.endpoint, invoice_key, timeout=REQUEST_TIMEOUT
                    )
                
                if invoice_key and wallet_id:
                    # Monitor WebSocket en hilo de fondo (RAM + Cero Tor Requests en polling)
                    monitor = MonitorWebSocket(
                        endpoint=self.endpoint,
                        wallet_id=wallet_id,
                        admin_key=invoice_key, # Se usa como key para el request inicial
                    )
                    monitor.iniciar()
                    self.ws_monitors[wallet_name] = monitor

    def _get_wallet_type(self, wallet_name: str) -> Optional[WalletType]:
        if wallet_name in self.wallets_config.get("candidatos", {}):
            return WalletType.CANDIDATO
        elif wallet_name in self.wallets_config.get("mesas", {}):
            return WalletType.MESA
        return None

    def get_wallet_status(self, wallet_name: str) -> Optional[WalletDetails]:
        if wallet_name not in self.ws_monitors:
            return None

        wallet_type = self._get_wallet_type(wallet_name)
        if wallet_type == WalletType.CANDIDATO:
            wallet_info = self.wallets_config["candidatos"].get(wallet_name, {})
        else:
            wallet_info = self.wallets_config["mesas"].get(wallet_name, {})

        display_name = wallet_info.get("display_name", wallet_name)
        foto_url = f"/api/candidato_foto/{wallet_name}" if wallet_type == WalletType.CANDIDATO else None

        # Lectura instantánea desde memoria RAM (Cero uso de Tor)
        estado_ws = self.ws_monitors[wallet_name].obtener_estado()
        balance = estado_ws.get("saldo_sats", 0)
        lnbits_ok = estado_ws.get("lnbits_ok", False)
        ultimo_evento = estado_ws.get("ultimo_evento") or datetime.now().isoformat()
        
        vote_info = self.vote_converter.convert(balance)

        return WalletDetails(
            name=wallet_name,
            display_name=display_name,
            wallet_type=wallet_type,
            balance=balance,
            vote_info=vote_info,
            invoice_key=wallet_info.get("invoice_key", "")[:10] + "...",
            last_update=ultimo_evento,
            is_available=lnbits_ok,
            foto_url=foto_url,
            error_message=None if lnbits_ok else "Sincronizando...",
        )

    def get_all_wallets_status(self) -> List[WalletDetails]:
        statuses = []
        for wallet_type in ["candidatos", "mesas"]:
            if wallet_type in self.wallets_config:
                for wallet_name in self.wallets_config[wallet_type].keys():
                    status = self.get_wallet_status(wallet_name)
                    if status:
                        statuses.append(status)
        return statuses

    def get_candidatos_status(self) -> List[WalletDetails]:
        statuses = []
        if "candidatos" in self.wallets_config:
            for wallet_name in self.wallets_config["candidatos"].keys():
                status = self.get_wallet_status(wallet_name)
                if status:
                    statuses.append(status)
        return statuses

    def get_mesas_status(self) -> List[WalletDetails]:
        statuses = []
        if "mesas" in self.wallets_config:
            for wallet_name in self.wallets_config["mesas"].keys():
                status = self.get_wallet_status(wallet_name)
                if status:
                    statuses.append(status)
        return statuses

    def get_wallet_payments(self, wallet_name: str, limit: int = 20) -> List[Dict]:
        if wallet_name not in self.clients:
            return []

        client = self.clients[wallet_name]
        response = client.get_payments(limit=limit)

        if response and isinstance(response, list):
            payments = []
            for item in response:
                amount_msat = item.get("amount", 0)
                try:
                    amount_sats = int(amount_msat) // 1000 if amount_msat else 0
                except (ValueError, TypeError):
                    amount_sats = 0

                time_val = item.get("time", 0)
                date_str = ""
                if time_val:
                    try:
                        if isinstance(time_val, (int, float)):
                            date_str = datetime.fromtimestamp(time_val).strftime("%H:%M:%S")
                        elif isinstance(time_val, str):
                            if time_val.isdigit():
                                date_str = datetime.fromtimestamp(int(time_val)).strftime("%H:%M:%S")
                            else:
                                date_str = str(time_val)[:19]
                    except Exception:
                        date_str = ""

                payments.append(
                    {
                        "payment_hash": item.get("payment_hash", ""),
                        "amount": amount_sats,
                        "memo": item.get("memo", ""),
                        "paid": not item.get("pending", False),
                        "date": date_str,
                    }
                )
            return payments
        return []


# ============================================================================
# APLICACIÓN FLASK Y TEMPLATE WEB MODERNO
# ============================================================================

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5050",
    "http://127.0.0.1:5050",
    *[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
])

monitor = WalletMonitor(LNBITS_ENDPOINT, WALLETS_CONFIG)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard Electoral Bitcoin Lightning - Tiempo Real</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0B0F19;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-card-hover: rgba(30, 41, 59, 0.85);
      --accent-gold: #F7931A;
      --accent-gold-glow: rgba(247, 147, 26, 0.35);
      --text-main: #F9FAFB;
      --text-muted: #9CA3AF;
      --success-green: #10B981;
      --danger-red: #EF4444;
      --border-card: rgba(255, 255, 255, 0.08);
      --radius-lg: 20px;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(247, 147, 26, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(99, 102, 241, 0.08) 0%, transparent 40%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 30px 20px;
    }

    .container {
      max-width: 1300px;
      margin: 0 auto;
    }

    /* Encabezado Principal */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 35px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border-card);
      flex-wrap: wrap;
      gap: 20px;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-icon {
      font-size: 2.8rem;
      background: rgba(247, 147, 26, 0.15);
      padding: 12px 18px;
      border-radius: var(--radius-lg);
      border: 1px solid var(--accent-gold-glow);
    }

    .brand-title {
      font-family: 'Outfit', sans-serif;
      font-size: 2.2rem;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #FFF 0%, #F7931A 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-subtitle {
      font-size: 0.95rem;
      color: var(--text-muted);
    }

    .live-status-badge {
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--success-green);
      padding: 10px 20px;
      border-radius: 30px;
      font-weight: 600;
      font-size: 0.95rem;
    }

    .pulse-dot {
      width: 10px;
      height: 10px;
      background: var(--success-green);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--success-green);
      animation: pulse 1.8s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(0.95); opacity: 0.8; }
      50% { transform: scale(1.3); opacity: 1; }
      100% { transform: scale(0.95); opacity: 0.8; }
    }

    /* Pestañas de Filtro */
    .tabs-bar {
      display: flex;
      gap: 12px;
      margin-bottom: 30px;
      justify-content: flex-start;
    }

    .tab-btn {
      padding: 12px 24px;
      border: 1px solid var(--border-card);
      background: rgba(31, 41, 55, 0.5);
      color: var(--text-muted);
      border-radius: 30px;
      cursor: pointer;
      font-family: 'Outfit', sans-serif;
      font-weight: 600;
      font-size: 1rem;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      backdrop-filter: blur(10px);
    }

    .tab-btn:hover {
      background: rgba(247, 147, 26, 0.15);
      color: var(--accent-gold);
      border-color: var(--accent-gold-glow);
    }

    .tab-btn.active {
      background: linear-gradient(135deg, #F7931A 0%, #E07A00 100%);
      color: #000;
      border-color: var(--accent-gold);
      font-weight: 800;
      box-shadow: 0 4px 20px var(--accent-gold-glow);
    }

    /* Grid de Tarjetas */
    .dashboard-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
      gap: 24px;
      margin-bottom: 40px;
    }

    .wallet-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      padding: 24px;
      backdrop-filter: blur(16px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      align-items: center;
    }

    .wallet-card:hover {
      transform: translateY(-6px);
      background: var(--bg-card-hover);
      border-color: rgba(247, 147, 26, 0.3);
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), 0 0 20px var(--accent-gold-glow);
    }

    /* Columna Izquierda: Foto Grande + Nombre Abajo */
    .card-left-col {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding-right: 15px;
      border-right: 1px solid var(--border-card);
    }

    .large-avatar-frame {
      width: 120px;
      height: 120px;
      border-radius: 50%;
      border: 4px solid var(--accent-gold);
      box-shadow: 0 0 20px var(--accent-gold-glow);
      object-fit: cover;
      background: #1F2937;
      margin-bottom: 12px;
    }

    .candidate-name-below {
      font-family: 'Outfit', sans-serif;
      font-size: 1.45rem;
      font-weight: 800;
      color: #FFF;
      line-height: 1.25;
      margin-bottom: 6px;
    }

    .candidate-role-badge {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--accent-gold);
      background: rgba(247, 147, 26, 0.12);
      padding: 4px 10px;
      border-radius: 12px;
    }

    /* Columna Derecha: Votos Confirmados + Hora de Actualización */
    .card-right-col {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      width: 100%;
    }

    .vote-count-big {
      font-family: 'Outfit', sans-serif;
      font-size: 3.2rem;
      font-weight: 800;
      color: var(--accent-gold);
      text-shadow: 0 0 20px var(--accent-gold-glow);
      line-height: 1;
    }

    .vote-count-label {
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-muted);
      margin-top: 6px;
    }

    .sats-subtitle {
      font-size: 0.88rem;
      color: #D1D5DB;
      margin-top: 4px;
      font-family: monospace;
    }

    .progress-bar-wrap {
      width: 100%;
      height: 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      overflow: hidden;
      margin-top: 10px;
    }

    .progress-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #F7931A 0%, #FFB443 100%);
      border-radius: 10px;
      transition: width 0.6s ease;
    }

    .last-update-tag {
      margin-top: 14px;
      font-size: 0.78rem;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.04);
      padding: 6px 12px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.08);
    }

    @media (max-width: 580px) {
      .dashboard-grid {
        grid-template-columns: 1fr;
      }
      .wallet-card {
        grid-template-columns: 1fr;
      }
      .card-left-col {
        border-right: none;
        border-bottom: 1px solid var(--border-card);
        padding-right: 0;
        padding-bottom: 18px;
      }
    }

    /* Footer */
    footer {
      text-align: center;
      color: var(--text-muted);
      font-size: 0.9rem;
      padding-top: 20px;
      border-top: 1px solid var(--border-card);
    }

    .hidden { display: none !important; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand-group">
        <div class="brand-icon">📝</div>
        <div>
          <h1 class="brand-title">Sistema de Votación BTCOL</h1>
          <p class="brand-subtitle">Conteo de Votos e Inspección de Mesas en Tiempo Real</p>
        </div>
      </div>
      <div class="live-status-badge">
        <span class="pulse-dot"></span>
        <span>🟢 Monitoreo en Vivo</span>
      </div>
    </header>

    <!-- Filtros por Pestaña -->
    <div class="tabs-bar">
      <button class="tab-btn active" onclick="filterView('all', this)">📊 Todos</button>
      <button class="tab-btn" onclick="filterView('candidatos', this)">👥 Candidatos</button>
      <button class="tab-btn" onclick="filterView('mesas', this)">🏛️ Mesas Electorales</button>
    </div>

    <!-- Grid de Tarjetas -->
    <div id="walletContainer" class="dashboard-grid">
      <div style="grid-column: 1/-1; text-align: center; padding: 60px;">
        <p style="font-size: 1.2rem; color: var(--text-muted);">🔄 Consultando estado de conteo de votos...</p>
      </div>
    </div>

    <footer>
      <p>🔐 Conteo de Votos en Tiempo Real | Última actualización global: <span id="lastUpdate">—</span></p>
    </footer>
  </div>

  <script>
    const SATS_PER_VOTE = {{ sats_per_vote }};
    let currentFilter = 'all';

    async function loadWalletStatus() {
      try {
        const response = await fetch("/api/wallets/status");
        const data = await response.json();

        if (data.success && data.wallets) {
          renderWallets(data.wallets);
          document.getElementById("lastUpdate").textContent = new Date().toLocaleTimeString('es-ES');
        }
      } catch (err) {
        console.error("Error cargando estado:", err);
      }
    }

    function renderWallets(wallets) {
      const container = document.getElementById("walletContainer");
      
      // Calcular total de votos entre candidatos para la barra de progreso
      let totalVotosCandidatos = 0;
      wallets.forEach(w => {
        if (w.wallet_type === 'candidato') {
          totalVotosCandidatos += w.vote_info.votos;
        }
      });

      container.innerHTML = wallets.map(wallet => {
        const isCand = (wallet.wallet_type === 'candidato');
        const filterType = isCand ? 'candidatos' : 'mesas';
        const fotoUrl = wallet.foto_url || `/api/candidato_foto/${wallet.name}`;
        
        const votos = wallet.vote_info.votos;
        const pct = totalVotosCandidatos > 0 ? Math.round((votos / totalVotosCandidatos) * 100) : 0;
        const horaActualizacion = wallet.last_update ? new Date(wallet.last_update).toLocaleTimeString('es-ES') : new Date().toLocaleTimeString('es-ES');

        return `
          <div class="wallet-card ${filterType} ${currentFilter !== 'all' && currentFilter !== filterType ? 'hidden' : ''}" data-type="${filterType}">
            
            <!-- Mitad Izquierda: Foto Grande + Nombre Abajo -->
            <div class="card-left-col">
              ${isCand ? `
                <img src="${fotoUrl}" alt="${wallet.display_name}" class="large-avatar-frame" onerror="this.src='/api/candidato_foto/placeholder'">
              ` : `
                <div class="large-avatar-frame" style="display:flex; align-items:center; justify-content:center; font-size:3rem;">🏛️</div>
              `}
              <h3 class="candidate-name-below">${wallet.display_name}</h3>
              <span class="candidate-role-badge">${isCand ? 'Candidato Oficial' : 'Mesa Electoral'}</span>
            </div>

            <!-- Mitad Derecha: Votos Confirmados + Hora de Actualización -->
            <div class="card-right-col">
              ${isCand ? `
                <div class="vote-count-big">📝 ${votos}</div>
                <div class="vote-count-label">Votos Confirmados</div>
                <div class="progress-bar-wrap">
                  <div class="progress-bar-fill" style="width: ${pct}%;"></div>
                </div>
              ` : `
                <div class="vote-count-big" style="color: #60A5FA;">🗳️ ${votos}</div>
                <div class="vote-count-label">Votos Remanentes</div>
              `}
              
              <div class="last-update-tag">
                🕒 Actualizado: <strong>${horaActualizacion}</strong>
              </div>
            </div>

          </div>
        `;
      }).join("");
    }

    function filterView(filter, btn) {
      currentFilter = filter;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.wallet-card').forEach(card => {
        if (filter === 'all' || card.getAttribute('data-type') === filter) {
          card.classList.remove('hidden');
        } else {
          card.classList.add('hidden');
        }
      });
    }

    // Inicializar y refrescar cada 2 segundos
    loadWalletStatus();
    // El backend ahora sirve los datos desde RAM gracias a WebSockets.
    // Coste de red: 0. Podemos consultar tan rápido como queramos.
    setInterval(loadWalletStatus, 2000);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        sats_per_vote=SATS_PER_VOTE,
        show_both_lower="true" if SHOW_SATS_AND_VOTES else "false",
    )


@app.route("/api/candidato_foto/<candidato_id>")
def obtener_foto_candidato_dashboard(candidato_id):
    """Retorna la foto del candidato según su ID o avatar_placeholder.svg"""
    foto_paths = []
    
    # Intentar resolver desde foto_local configurado en wallets.json
    candidato = monitor.wallets_config["candidatos"].get(candidato_id)
    if candidato and candidato.get("foto_local"):
        foto_paths.append(BASE_DIR / "mesa_code" / "data_mesa" / candidato["foto_local"])
        foto_paths.append(BASE_DIR / "mesa_code" / candidato["foto_local"])

    foto_paths.extend([
        BASE_DIR / "mesa_code" / "data_mesa" / "fotos" / f"{candidato_id}.png",
        BASE_DIR / "mesa_code" / "data_mesa" / "fotos" / f"{candidato_id}.jpg",
        BASE_DIR / "mesa_code" / "data_mesa" / "fotos" / f"{candidato_id}.jpeg",
        BASE_DIR / "mesa_code" / "web" / "templates" / "avatar_placeholder.svg"
    ])
    for p in foto_paths:
        if p and p.exists():
            return send_file(p)
    return "", 404


@app.route("/api/wallets/status")
def get_wallets_status():
    try:
        wallets_status = monitor.get_all_wallets_status()
        return jsonify(
            {
                "success": True,
                "wallets": [asdict(w) for w in wallets_status],
            }
        )
    except Exception as e:
        print(f"Error en /api/wallets/status: {sanitizar_texto(str(e))}")
        return jsonify({"success": False, "error": sanitizar_texto(str(e))}), 500


@app.route("/api/candidatos/status")
def get_candidatos_status():
    try:
        wallets_status = monitor.get_candidatos_status()
        return jsonify(
            {
                "success": True,
                "wallets": [asdict(w) for w in wallets_status],
            }
        )
    except Exception as e:
        print(f"Error en /api/candidatos/status: {sanitizar_texto(str(e))}")
        return jsonify({"success": False, "error": sanitizar_texto(str(e))}), 500


@app.route("/api/mesas/status")
def get_mesas_status():
    try:
        wallets_status = monitor.get_mesas_status()
        return jsonify(
            {
                "success": True,
                "wallets": [asdict(w) for w in wallets_status],
            }
        )
    except Exception as e:
        print(f"Error en /api/mesas/status: {sanitizar_texto(str(e))}")
        return jsonify({"success": False, "error": sanitizar_texto(str(e))}), 500


@app.route("/api/wallets/<wallet_name>/status")
def get_wallet_status(wallet_name: str):
    try:
        status = monitor.get_wallet_status(wallet_name)
        if status is None:
            return jsonify({"success": False, "error": "Wallet no encontrada"}), 404

        return jsonify({"success": True, "wallet": asdict(status)})
    except Exception as e:
        print(f"Error en /api/wallets/{wallet_name}/status: {sanitizar_texto(str(e))}")
        return jsonify({"success": False, "error": sanitizar_texto(str(e))}), 500


@app.route("/api/wallets/<wallet_name>/payments")
def get_wallet_payments(wallet_name: str):
    try:
        limit = request.args.get("limit", 20, type=int)
        payments = monitor.get_wallet_payments(wallet_name, limit)
        return jsonify({"success": True, "payments": payments})
    except Exception as e:
        print(f"⚠️ Error obteniendo historial para {wallet_name}: {sanitizar_texto(str(e))}")
        return jsonify({"success": True, "payments": [], "warning": sanitizar_texto(str(e))})


@app.route("/api/config")
def get_config():
    return jsonify(
        {
            "success": True,
            "sats_per_vote": SATS_PER_VOTE,
            "show_both": SHOW_SATS_AND_VOTES,
        }
    )


@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "mode": "read-only"})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dashboard Web de Monitoreo Electoral en Tiempo Real (BTCOL)")
    parser.add_argument("--fernet-key", type=str, default=None, help="Clave Fernet en Base64 para descifrar wallets.json.enc (Solo administradores autorizados)")
    parser.add_argument("--host", type=str, default=os.getenv("DASHBOARD_HOST", "127.0.0.1"), help="Host del servidor Flask (por defecto: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5050, help="Puerto del servidor Flask (por defecto: 5050)")
    parser.add_argument("--debug", action="store_true", help="Activa el modo debug de Flask")
    
    args = parser.parse_args()
    
    if args.fernet_key:
        try:
            WALLETS_CONFIG = load_wallets_config(clave_custom=args.fernet_key)
        except Exception as e:
            print(f"❌ Error al recargar configuración con --fernet-key: {e}")
            sys.exit(1)

    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║  Dashboard de Votos Bitcoin Lightning - Red Tor - v3.0       ║
╚═══════════════════════════════════════════════════════════════╝
    """
    )

    print(f"📍 LNbits Endpoint: {enmascarar_url(LNBITS_ENDPOINT)}")
    print(f"🗳️ Tasa de conversión: 1 voto = {SATS_PER_VOTE} sats")
    print(f"🔒 Modo: Solo lectura (Invoice Keys)")
    print("")
    print("📊 WALLETS CARGADAS:")
    print(f"   👥 Candidatos: {len(WALLETS_CONFIG.get('candidatos', {}))}")
    for name, info in WALLETS_CONFIG.get("candidatos", {}).items():
        print(f"      - {info.get('display_name', name)}")
    print(f"   🏛️ Mesas: {len(WALLETS_CONFIG.get('mesas', {}))}")
    for name, info in WALLETS_CONFIG.get("mesas", {}).items():
        print(f"      - {info.get('display_name', name)}")
    print("")
    print(f"🚀 Dashboard disponible en: http://localhost:{args.port}")
    print("")

    debug_val = args.debug or (os.getenv("FLASK_DEBUG", "False").lower() == "true")

    app.run(
        host=args.host,
        port=args.port,
        debug=debug_val,
        use_reloader=debug_val,
    )
