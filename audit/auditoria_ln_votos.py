"""
auditoria_ln_votos.py - Herramienta y Dashboard Interactivo de Auditoría Electoral LNbits

Este script audita en tiempo real las transacciones de las wallets de LNbits (vía red Tor .onion)
y/o la base de datos de pagos. Reconcilia los votos 1:1 entre Mesas y Candidatos, detecta votos
irregulares (provenientes de wallets o mesas no autorizadas fuera de wallets.json) y despliega
un Dashboard Web Interactivo de Auditoría en el puerto 7070.

Uso:
    python audit/auditoria_ln_votos.py
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Dict, List, Optional, Tuple, Set

from flask import Flask, render_template_string, jsonify, request, send_file
from flask_cors import CORS
import requests

# Directorio raíz del proyecto (1 nivel arriba desde audit/)
BASE_DIR = Path(__file__).resolve().parent.parent  # audit/ -> raíz
DATA_DIR = BASE_DIR / "data"

# Archivo de configuración unificado de wallets
WALLETS_CONFIG_FILE = DATA_DIR / "wallets.json"
DATABASE_FILE = DATA_DIR / "database.sqlite3"


# ============================================================================
# NORMALIZACIÓN Y CARGA DE CONFIGURACIÓN
# ============================================================================


def normalize_wallets_dict(raw_data) -> Dict[str, Dict]:
    """
    Convierte cualquier sección (sea lista u objeto) en un diccionario unificado
    donde la clave es el ID de la wallet.
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


def load_wallets_config() -> Dict:
    """Carga y normaliza wallets.json"""
    if not WALLETS_CONFIG_FILE.exists():
        raise FileNotFoundError(f"Archivo {WALLETS_CONFIG_FILE} no encontrado.")

    try:
        with open(WALLETS_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "settings": data.get("settings", {}),
                "candidatos": normalize_wallets_dict(data.get("candidatos", [])),
                "mesas": normalize_wallets_dict(data.get("mesas", []))
            }
    except Exception as e:
        raise ValueError(f"Error cargando {WALLETS_CONFIG_FILE}: {e}")


try:
    WALLETS_CONFIG = load_wallets_config()
except Exception as e:
    print(f"❌ Error al cargar configuración de wallets: {e}")
    WALLETS_CONFIG = {"settings": {}, "candidatos": {}, "mesas": {}}

SETTINGS = WALLETS_CONFIG.get("settings", {})
LNBITS_ENDPOINT = (os.getenv("LNBITS_ENDPOINT") or SETTINGS.get("url_lnbits") or "http://localhost:5050").rstrip("/")
SATS_PER_VOTE = int(os.getenv("SATS_PER_VOTE") or SETTINGS.get("sats_per_vote", 100))


# ============================================================================
# CLIENTE API LNBITS (RED TOR .ONION)
# ============================================================================


class LNBitsAuditClient:
    """Cliente read-only para consultar transacciones vía Tor SOCKS5"""

    def __init__(self, endpoint: str, invoice_key: str, timeout: int = 15):
        self.endpoint = endpoint.rstrip("/")
        self.invoice_key = invoice_key
        self.timeout = timeout

    def _get_proxies(self, url: str) -> Optional[Dict[str, str]]:
        if ".onion" in url:
            return {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050"
            }
        return None

    def get_payments(self, limit: int = 100) -> List[Dict]:
        url = f"{self.endpoint}/api/v1/payments?limit={limit}"
        headers = {"X-Api-Key": self.invoice_key, "Content-Type": "application/json"}
        proxies = self._get_proxies(url)

        try:
            res = requests.get(url, headers=headers, proxies=proxies, timeout=self.timeout)
            if res.status_code == 200 and isinstance(res.json(), list):
                return res.json()
        except Exception:
            pass
        return []


# ============================================================================
# MOTOR DE AUDITORÍA Y RECONCILIACIÓN
# ============================================================================


class EstadoAuditVoto(str, Enum):
    VALIDO_AUTORIZADO = "VALIDO_AUTORIZADO"
    IRREGULAR_NO_AUTORIZADO = "IRREGULAR_NO_AUTORIZADO"
    DESCALCE_MESA_SOLO = "DESCALCE_MESA_SOLO"


@dataclass
class RegistroAuditVoto:
    payment_hash: str
    mesa_id: str
    mesa_nombre: str
    candidato_id: str
    candidato_nombre: str
    monto_sats: int
    votos_equivalentes: int
    memo: str
    fecha: str
    estado: EstadoAuditVoto
    es_irregular: bool
    origen_wallet_id: str


class MotorAuditoriaElectoral:
    """Motor central de reconciliación de transacciones y detección de irregularidades"""

    def __init__(self, config: Dict):
        self.config = config
        self.candidatos = config.get("candidatos", {})
        self.mesas = config.get("mesas", {})
        
        # Sets de IDs autorizados
        self.authorized_mesa_ids: Set[str] = set(self.mesas.keys())
        self.authorized_candidato_ids: Set[str] = set(self.candidatos.keys())
        
        # Mapeo de wallet_id (UUID) a ID lógico (ej. f0cd... -> mesa1)
        self.uuid_to_id: Dict[str, str] = {}
        for c_id, info in self.candidatos.items():
            u = info.get("wallet_id")
            if u: self.uuid_to_id[u] = c_id
        for m_id, info in self.mesas.items():
            u = info.get("wallet_id")
            if u: self.uuid_to_id[u] = m_id
        
        # Mapeo de ID -> Display Name
        self.id_to_name: Dict[str, str] = {}
        for wid, info in self.candidatos.items():
            self.id_to_name[wid] = info.get("display_name", wid)
        for wid, info in self.mesas.items():
            self.id_to_name[wid] = info.get("display_name", wid)

    def extraer_pagos_sqlite(self) -> Tuple[List[Dict], List[Dict]]:
        """Extrae pagos salientes de mesas y entrantes de candidatos desde database.sqlite3 si existe"""
        mesas_payments = []
        candidatos_payments = []

        if not DATABASE_FILE.exists():
            return mesas_payments, candidatos_payments

        try:
            conn = sqlite3.connect(DATABASE_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Consultar apipayments
            cursor.execute("SELECT wallet_id, amount, memo, payment_hash, time FROM apipayments ORDER BY time DESC")
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                
                wid_raw = row["wallet_id"]
                # Convertir UUID crudo a nuestro ID lógico (mesa1, candidato1)
                wid = self.uuid_to_id.get(wid_raw, wid_raw)
                
                amount_msat = row["amount"]
                amount_sats = abs(amount_msat) // 1000 if amount_msat else 0
                time_val = row["time"]
                date_str = datetime.fromtimestamp(time_val).strftime("%Y-%m-%d %H:%M:%S") if time_val else ""

                item = {
                    "wallet_id": wid,
                    "payment_hash": row["payment_hash"] or "",
                    "amount_sats": amount_sats,
                    "memo": row["memo"] or "",
                    "date": date_str,
                    "raw_amount": amount_msat
                }

                if wid in self.authorized_mesa_ids and amount_msat < 0:
                    mesas_payments.append(item)
                elif wid in self.authorized_candidato_ids and amount_msat > 0:
                    candidatos_payments.append(item)
                elif amount_msat > 0 and wid not in self.authorized_mesa_ids:
                    # Pago hacia un candidato o wallet desde una wallet no clasificada previamente
                    candidatos_payments.append(item)

        except Exception as e:
            print(f"⚠️ Nota: Consulta a SQLite local retornó: {e}")

        return mesas_payments, candidatos_payments

    def _formatear_fecha(self, time_val) -> str:
        if not time_val:
            return ""
        try:
            if isinstance(time_val, (int, float)):
                return datetime.fromtimestamp(time_val).strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(time_val, str):
                if time_val.isdigit():
                    return datetime.fromtimestamp(int(time_val)).strftime("%Y-%m-%d %H:%M:%S")
                return str(time_val)[:19]
        except Exception:
            pass
        return ""

    def extraer_pagos_api(self) -> Tuple[List[Dict], List[Dict]]:
        """Extrae pagos de LNbits en tiempo real vía API Tor"""
        mesas_payments = []
        candidatos_payments = []

        # 1. Pagos emitidos por Mesas
        for m_id, m_info in self.mesas.items():
            inv_key = m_info.get("invoice_key")
            if not inv_key:
                continue
            client = LNBitsAuditClient(LNBITS_ENDPOINT, inv_key)
            raw_payments = client.get_payments(limit=5000)
            for p in raw_payments:
                if p.get("pending"):
                    continue
                # Pagos salientes (outbound)
                amount_msat = p.get("amount", 0)
                if amount_msat >= 0:
                    continue  # Ignorar pagos entrantes a la mesa (ej. recargas)
                try:
                    amount_sats = abs(int(amount_msat)) // 1000 if amount_msat else 0
                except (ValueError, TypeError):
                    amount_sats = 0
                date_str = self._formatear_fecha(p.get("time", 0))

                mesas_payments.append({
                    "wallet_id": m_id,
                    "payment_hash": p.get("payment_hash", ""),
                    "amount_sats": amount_sats,
                    "memo": p.get("memo", ""),
                    "date": date_str,
                    "raw_amount": amount_msat
                })

        # 2. Pagos recibidos por Candidatos
        for c_id, c_info in self.candidatos.items():
            inv_key = c_info.get("invoice_key")
            if not inv_key:
                continue
            client = LNBitsAuditClient(LNBITS_ENDPOINT, inv_key)
            raw_payments = client.get_payments(limit=5000)
            for p in raw_payments:
                if p.get("pending"):
                    continue
                amount_msat = p.get("amount", 0)
                if amount_msat <= 0:
                    continue  # Ignorar pagos salientes (ej. retiro de liquidez)
                try:
                    amount_sats = abs(int(amount_msat)) // 1000 if amount_msat else 0
                except (ValueError, TypeError):
                    amount_sats = 0
                date_str = self._formatear_fecha(p.get("time", 0))

                candidatos_payments.append({
                    "wallet_id": c_id,
                    "payment_hash": p.get("payment_hash", ""),
                    "amount_sats": amount_sats,
                    "memo": p.get("memo", ""),
                    "date": date_str,
                    "raw_amount": amount_msat
                })

        return mesas_payments, candidatos_payments

    def ejecutar_auditoria(self) -> Dict:
        """
        Ejecuta la reconciliación y clasificación criptográfica de transacciones.
        Identifica votos Válidos Autorizados e Irregulares de Mesas No Autorizadas.
        """
        # Extraer datos de API y/o SQLite
        mesas_p, candidatos_p = self.extraer_pagos_api()
        if not mesas_p and not candidatos_p:
            mesas_p, candidatos_p = self.extraer_pagos_sqlite()

        # Mapear pagos de mesas por payment_hash
        mesa_by_hash = {p["payment_hash"]: p for p in mesas_p if p["payment_hash"]}

        registros_auditados: List[RegistroAuditVoto] = []
        candidato_totales = {c_id: {"autorizados": 0, "irregulares": 0, "sats_autorizados": 0, "sats_irregulares": 0} for c_id in self.authorized_candidato_ids}
        mesa_totales = {m_id: {"emitidos": 0, "sats_emitidos": 0} for m_id in self.authorized_mesa_ids}
        
        # Matriz Origen -> Destino
        matriz_origen_destino = {m_id: {c_id: 0 for c_id in self.authorized_candidato_ids} for m_id in self.authorized_mesa_ids}

        # Procesar todos los votos recibidos por los Candidatos
        for p_cand in candidatos_p:
            cand_id = p_cand["wallet_id"]
            hash_val = p_cand["payment_hash"]
            memo_val = p_cand["memo"]
            amount_sats = p_cand["amount_sats"]
            votos_count = max(1, amount_sats // SATS_PER_VOTE)
            date_str = p_cand["date"]

            # Nombre de candidato
            cand_name = self.id_to_name.get(cand_id, f"Wallet {cand_id[:8]}")

            # Buscar coincidencia en pagos de Mesas Autorizadas (Únicamente por Hash Criptográfico)
            match_mesa = mesa_by_hash.get(hash_val)

            if match_mesa:
                mesa_id = match_mesa["wallet_id"]
                mesa_name = self.id_to_name.get(mesa_id, f"Mesa {mesa_id[:8]}")
                
                reg = RegistroAuditVoto(
                    payment_hash=hash_val,
                    mesa_id=mesa_id,
                    mesa_nombre=mesa_name,
                    candidato_id=cand_id,
                    candidato_nombre=cand_name,
                    monto_sats=amount_sats,
                    votos_equivalentes=votos_count,
                    memo=memo_val,
                    fecha=date_str,
                    estado=EstadoAuditVoto.VALIDO_AUTORIZADO,
                    es_irregular=False,
                    origen_wallet_id=mesa_id
                )
                registros_auditados.append(reg)

                # Actualizar métricas
                if cand_id in candidato_totales:
                    candidato_totales[cand_id]["autorizados"] += votos_count
                    candidato_totales[cand_id]["sats_autorizados"] += amount_sats
                if mesa_id in mesa_totales:
                    mesa_totales[mesa_id]["emitidos"] += votos_count
                    mesa_totales[mesa_id]["sats_emitidos"] += amount_sats
                if mesa_id in matriz_origen_destino and cand_id in matriz_origen_destino[mesa_id]:
                    matriz_origen_destino[mesa_id][cand_id] += votos_count

            else:
                # VOTO IRREGULAR: Recibido por Candidato pero no proviene de ninguna Mesa Autorizada en wallets.json
                origen_id = "DESCONOCIDO / EXTERNO"
                
                reg = RegistroAuditVoto(
                    payment_hash=hash_val,
                    mesa_id="DESCONOCIDO",
                    mesa_nombre="⚠️ Mesa No Autorizada / Externa",
                    candidato_id=cand_id,
                    candidato_nombre=cand_name,
                    monto_sats=amount_sats,
                    votos_equivalentes=votos_count,
                    memo=memo_val,
                    fecha=date_str,
                    estado=EstadoAuditVoto.IRREGULAR_NO_AUTORIZADO,
                    es_irregular=True,
                    origen_wallet_id=origen_id
                )
                registros_auditados.append(reg)

                if cand_id in candidato_totales:
                    candidato_totales[cand_id]["irregulares"] += votos_count
                    candidato_totales[cand_id]["sats_irregulares"] += amount_sats

        # Totales consolidados
        total_votos_validos = sum(t["autorizados"] for t in candidato_totales.values())
        total_votos_irregulares = sum(t["irregulares"] for t in candidato_totales.values())
        total_votos_procesados = total_votos_validos + total_votos_irregulares
        pct_integridad = 100.0 if total_votos_procesados == 0 else round((total_votos_validos / total_votos_procesados) * 100, 2)

        return {
            "success": True,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "resumen": {
                "total_procesados": total_votos_procesados,
                "votos_validos": total_votos_validos,
                "votos_irregulares": total_votos_irregulares,
                "pct_integridad": pct_integridad,
                "sats_per_vote": SATS_PER_VOTE
            },
            "candidatos": [
                {
                    "id": c_id,
                    "nombre": self.id_to_name.get(c_id, c_id),
                    "votos_autorizados": candidato_totales[c_id]["autorizados"],
                    "votos_irregulares": candidato_totales[c_id]["irregulares"],
                    "total_votos": candidato_totales[c_id]["autorizados"] + candidato_totales[c_id]["irregulares"],
                    "sats_autorizados": candidato_totales[c_id]["sats_autorizados"],
                    "sats_irregulares": candidato_totales[c_id]["sats_irregulares"]
                }
                for c_id in self.authorized_candidato_ids
            ],
            "mesas": [
                {
                    "id": m_id,
                    "nombre": self.id_to_name.get(m_id, m_id),
                    "votos_emitidos": mesa_totales[m_id]["emitidos"],
                    "sats_emitidos": mesa_totales[m_id]["sats_emitidos"]
                }
                for m_id in self.authorized_mesa_ids
            ],
            "matriz_origen_destino": matriz_origen_destino,
            "transacciones": [asdict(r) for r in registros_auditados],
            "irregulares_list": [asdict(r) for r in registros_auditados if r.es_irregular]
        }


# Instancia del motor de auditoría
motor_auditoria = MotorAuditoriaElectoral(WALLETS_CONFIG)


# ============================================================================
# DASHBOARD WEB INTERACTIVO (FLASK PUERTO 7070)
# ============================================================================

app = Flask(__name__)
CORS(app)


HTML_AUDIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard de Auditoría Electoral BTCOL - Reconciliación 1:1</title>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg-dark: #090D16;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-card-hover: rgba(30, 41, 59, 0.85);
      --accent-gold: #F7931A;
      --accent-gold-glow: rgba(247, 147, 26, 0.35);
      --text-main: #F9FAFB;
      --text-muted: #9CA3AF;
      --success-green: #10B981;
      --danger-red: #EF4444;
      --warning-yellow: #F59E0B;
      --border-card: rgba(255, 255, 255, 0.08);
      --radius-lg: 20px;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(circle at 10% 10%, rgba(247, 147, 26, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 90% 90%, rgba(239, 68, 68, 0.08) 0%, transparent 40%);
      color: var(--text-main);
      min-height: 100vh;
      padding: 30px 20px;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
    }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 25px;
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
      font-size: 2.6rem;
      background: rgba(247, 147, 26, 0.15);
      padding: 12px 18px;
      border-radius: var(--radius-lg);
      border: 1px solid var(--accent-gold-glow);
    }

    .brand-title {
      font-family: 'Outfit', sans-serif;
      font-size: 2.2rem;
      font-weight: 800;
      background: linear-gradient(135deg, #FFF 0%, #F7931A 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-subtitle {
      font-size: 0.95rem;
      color: var(--text-muted);
    }

    /* Pestañas de Navegación */
    .nav-tabs-bar {
      display: flex;
      gap: 12px;
      margin-bottom: 25px;
      border-bottom: 1px solid var(--border-card);
      padding-bottom: 12px;
    }

    .nav-tab-btn {
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

    .nav-tab-btn:hover {
      background: rgba(247, 147, 26, 0.15);
      color: var(--accent-gold);
      border-color: var(--accent-gold-glow);
    }

    .nav-tab-btn.active {
      background: linear-gradient(135deg, #F7931A 0%, #E07A00 100%);
      color: #000;
      border-color: var(--accent-gold);
      font-weight: 800;
      box-shadow: 0 4px 20px var(--accent-gold-glow);
    }

    /* KPI Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 25px;
    }

    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      padding: 24px;
      backdrop-filter: blur(16px);
      text-align: center;
    }

    .kpi-val {
      font-family: 'Outfit', sans-serif;
      font-size: 2.8rem;
      font-weight: 800;
      line-height: 1;
      margin-bottom: 6px;
    }

    .kpi-label {
      font-size: 0.85rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 600;
    }

    /* Alerta de Irregularidades */
    .alert-irregular-box {
      background: rgba(239, 68, 68, 0.15);
      border: 2px solid var(--danger-red);
      border-radius: var(--radius-lg);
      padding: 20px 26px;
      margin-bottom: 25px;
      display: flex;
      align-items: center;
      gap: 18px;
      color: #FCA5A5;
    }

    /* Controles de Filtros */
    .filter-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      padding: 20px 24px;
      margin-bottom: 25px;
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      align-items: center;
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex: 1;
      min-width: 200px;
    }

    .filter-label {
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
    }

    select, input {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border-card);
      color: #FFF;
      padding: 10px 16px;
      border-radius: 12px;
      font-family: 'Inter', sans-serif;
      font-size: 0.95rem;
      outline: none;
    }

    select:focus, input:focus {
      border-color: var(--accent-gold);
    }

    /* Tablas y Contenedores */
    .section-card {
      background: var(--bg-card);
      border: 1px solid var(--border-card);
      border-radius: var(--radius-lg);
      padding: 28px;
      margin-bottom: 30px;
      backdrop-filter: blur(16px);
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-card);
    }

    .section-title {
      font-family: 'Outfit', sans-serif;
      font-size: 1.4rem;
      font-weight: 800;
      color: #FFF;
    }

    /* Gráfico */
    .chart-container-box {
      height: 340px;
      position: relative;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }

    th, td {
      padding: 14px 18px;
      text-align: left;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }

    th {
      font-family: 'Outfit', sans-serif;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      font-size: 0.8rem;
      letter-spacing: 0.5px;
      background: rgba(15, 23, 42, 0.5);
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .badge-status {
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 700;
      display: inline-block;
    }

    .badge-valid {
      background: rgba(16, 185, 129, 0.15);
      color: var(--success-green);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-irregular {
      background: rgba(239, 68, 68, 0.15);
      color: #FCA5A5;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }

    footer {
      text-align: center;
      color: var(--text-muted);
      font-size: 0.88rem;
      padding-top: 20px;
      border-top: 1px solid var(--border-card);
    }

    .tab-pane { display: block; }
    .tab-pane.hidden { display: none !important; }
    .hidden { display: none !important; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand-group">
        <div class="brand-icon">⚖️</div>
        <div>
          <h1 class="brand-title">Auditoría Electoral BTCOL</h1>
          <p class="brand-subtitle">Reconciliación Criptográfica 1:1 & Detección de Votos Irregulares</p>
        </div>
      </div>
      <div style="text-align: right;">
        <span class="badge-status badge-valid" style="font-size: 0.9rem;">🔍 Inspección en Tiempo Real</span>
      </div>
    </header>

    <!-- Pestañas Principales -->
    <div class="nav-tabs-bar">
      <button class="nav-tab-btn active" onclick="switchMainTab('summary', this)">📊 Resumen & Gráficos</button>
      <button class="nav-tab-btn" onclick="switchMainTab('transactions', this)">📜 Registro General de Transacciones</button>
    </div>

    <!-- PESTAÑA 1: RESUMEN Y GRÁFICOS -->
    <div id="paneSummary" class="tab-pane">
      <!-- Tarjetas KPI -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <div id="kpiTotalProcesados" class="kpi-val" style="color: #60A5FA;">--</div>
          <div class="kpi-label">Total Votos Procesados</div>
        </div>
        <div class="kpi-card">
          <div id="kpiValidos" class="kpi-val" style="color: var(--success-green);">--</div>
          <div class="kpi-label">🟢 Votos Válidos Autorizados</div>
        </div>
        <div class="kpi-card">
          <div id="kpiIrregulares" class="kpi-val" style="color: var(--danger-red);">--</div>
          <div class="kpi-label">🔴 Votos Irregulares Detectados</div>
        </div>
        <div class="kpi-card">
          <div id="kpiIntegridad" class="kpi-val" style="color: var(--accent-gold);">--</div>
          <div class="kpi-label">🛡️ % Integridad Electoral</div>
        </div>
      </div>

      <!-- Alerta de Irregularidades -->
      <div id="irregularAlertBox" class="alert-irregular-box hidden">
        <div style="font-size: 2.2rem;">⚠️</div>
        <div>
          <h3 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 4px;">ALERTA DE SEGURIDAD ELECTORAL</h3>
          <p id="irregularAlertMsg">Se han detectado votos en wallets de candidatos provenientes de mesas no autorizadas.</p>
        </div>
      </div>

      <!-- Controles de Filtros -->
      <div class="filter-card">
        <div class="filter-group">
          <span class="filter-label">🏛️ Filtrar por Mesa</span>
          <select id="filterMesa" onchange="applyFilters()">
            <option value="ALL">Todas las Mesas Electorales</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="filter-label">👥 Filtrar por Candidato</span>
          <select id="filterCandidato" onchange="applyFilters()">
            <option value="ALL">Todos los Candidatos</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="filter-label">🛡️ Estado de Auditoría</span>
          <select id="filterEstado" onchange="applyFilters()">
            <option value="ALL">Todos los Registros</option>
            <option value="VALIDO">Solo Válidos Autorizados</option>
            <option value="IRREGULAR">Solo Irregulares Detectados</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="filter-label">🔍 Buscar Memo / Payment Hash</span>
          <input type="text" id="searchInput" placeholder="Ej: Hash o palabra..." oninput="applyFilters()">
        </div>
      </div>

      <!-- Gráfico de Barras según Filtro Aplicado -->
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">📊 Interpretación Gráfica del Filtro Aplicado</h2>
          <span id="chartFilterBadge" style="font-size:0.85rem; color:var(--accent-gold);">Distribución por Candidato</span>
        </div>
        <div class="chart-container-box">
          <canvas id="auditBarChart"></canvas>
        </div>
      </div>

      <!-- Matriz Origen -> Destino -->
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">🏛️ Matriz Electoral Origen ➔ Destino (Mesas vs. Candidatos)</h2>
        </div>
        <div style="overflow-x: auto;">
          <table id="matrixTable">
            <thead>
              <tr id="matrixHeaderRow">
                <th>Mesa Electoral</th>
              </tr>
            </thead>
            <tbody id="matrixBody"></tbody>
          </table>
        </div>
      </div>

      <!-- Tabla de Votos Irregulares Detectados -->
      <div class="section-card" id="sectionIrregulares">
        <div class="section-header">
          <h2 class="section-title" style="color: #FCA5A5;">⚠️ Detalle de Votos Irregulares (Mesas No Autorizadas)</h2>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>Candidato Receptor</th>
                <th>Mesa Origen Detectada</th>
                <th>Monto (Sats)</th>
                <th>Votos Eq.</th>
                <th>Payment Hash</th>
                <th>Fecha / Hora</th>
                <th>Dictamen</th>
              </tr>
            </thead>
            <tbody id="irregularesTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- PESTAÑA 2: REGISTRO GENERAL DE TRANSACCIONES -->
    <div id="paneTransactions" class="tab-pane hidden">
      <div class="section-card">
        <div class="section-header">
          <h2 class="section-title">📜 Registro General de Transacciones Auditadas</h2>
          <span id="txCountBadge" style="font-size:0.88rem; color:var(--text-muted);">Cargando...</span>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>Mesa Origen</th>
                <th>Candidato Destino</th>
                <th>Monto (Sats)</th>
                <th>Votos</th>
                <th>Payment Hash</th>
                <th>Fecha / Hora</th>
                <th>Estado Criptográfico</th>
              </tr>
            </thead>
            <tbody id="generalAuditTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <footer>
      <p>🔐 Auditoría Criptográfica Autónoma | Sistema Electoral BTCOL</p>
      <p>Última auditoría completada: <span id="auditTimestamp">—</span></p>
    </footer>
  </div>

  <script>
    let globalAuditData = null;
    let chartInstance = null;

    function switchMainTab(tabName, btn) {
      document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      if (tabName === 'summary') {
        document.getElementById('paneSummary').classList.remove('hidden');
        document.getElementById('paneTransactions').classList.add('hidden');
      } else {
        document.getElementById('paneSummary').classList.add('hidden');
        document.getElementById('paneTransactions').classList.remove('hidden');
      }
    }

    async function loadAuditData() {
      try {
        const res = await fetch("/api/audit/ejecutar");
        const data = await res.json();

        if (data.success) {
          globalAuditData = data;
          renderDashboard(data);
        }
      } catch (err) {
        console.error("Error ejecutando auditoría:", err);
      }
    }

    function renderDashboard(data) {
      // 1. KPI Cards
      document.getElementById("kpiTotalProcesados").textContent = data.resumen.total_procesados;
      document.getElementById("kpiValidos").textContent = data.resumen.votos_validos;
      document.getElementById("kpiIrregulares").textContent = data.resumen.votos_irregulares;
      document.getElementById("kpiIntegridad").textContent = data.resumen.pct_integridad + "%";
      document.getElementById("auditTimestamp").textContent = data.timestamp;

      // 2. Alerta Irregulares
      const alertBox = document.getElementById("irregularAlertBox");
      if (data.resumen.votos_irregulares > 0) {
        alertBox.classList.remove("hidden");
        document.getElementById("irregularAlertMsg").textContent = 
          `Se han detectado ${data.resumen.votos_irregulares} votos irregulares provenientes de fuentes o mesas NO AUTORIZADAS en wallets.json.`;
      } else {
        alertBox.classList.add("hidden");
      }

      // 3. Poblar Filtros
      populateSelects(data);

      // 4. Renderizar Matriz Origen -> Destino
      renderMatrix(data);

      // 5. Renderizar Tablas y Gráfico
      applyFilters();
    }

    function populateSelects(data) {
      const selectMesa = document.getElementById("filterMesa");
      const selectCand = document.getElementById("filterCandidato");

      if (selectMesa.options.length <= 1) {
        data.mesas.forEach(m => {
          const opt = document.createElement("option");
          opt.value = m.id;
          opt.textContent = m.nombre;
          selectMesa.appendChild(opt);
        });
      }

      if (selectCand.options.length <= 1) {
        data.candidatos.forEach(c => {
          const opt = document.createElement("option");
          opt.value = c.id;
          opt.textContent = c.nombre;
          selectCand.appendChild(opt);
        });
      }
    }

    function renderMatrix(data) {
      const headerRow = document.getElementById("matrixHeaderRow");
      const tbody = document.getElementById("matrixBody");

      headerRow.innerHTML = "<th>Mesa Electoral</th>";
      data.candidatos.forEach(c => {
        const th = document.createElement("th");
        th.textContent = c.nombre;
        headerRow.appendChild(th);
      });
      headerRow.innerHTML += "<th>Total Emitidos</th>";

      tbody.innerHTML = "";
      data.mesas.forEach(m => {
        const tr = document.createElement("tr");
        let rowHtml = `<td><strong>${m.nombre}</strong></td>`;
        
        let sumMesa = 0;
        data.candidatos.forEach(c => {
          const count = (data.matriz_origen_destino[m.id] && data.matriz_origen_destino[m.id][c.id]) || 0;
          sumMesa += count;
          rowHtml += `<td>${count > 0 ? `<strong>${count}</strong>` : '0'}</td>`;
        });

        rowHtml += `<td style="color: var(--accent-gold);"><strong>${sumMesa}</strong></td>`;
        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
      });
    }

    function updateChart(filteredTx) {
      const ctx = document.getElementById('auditBarChart').getContext('2d');
      
      // Agrupar votos filtrados por candidato
      const candMap = {};
      globalAuditData.candidatos.forEach(c => {
        candMap[c.id] = { nombre: c.nombre, autorizados: 0, irregulares: 0 };
      });

      filteredTx.forEach(t => {
        if (!candMap[t.candidato_id]) {
          candMap[t.candidato_id] = { nombre: t.candidato_nombre, autorizados: 0, irregulares: 0 };
        }
        if (t.es_irregular) {
          candMap[t.candidato_id].irregulares += t.votos_equivalentes;
        } else {
          candMap[t.candidato_id].autorizados += t.votos_equivalentes;
        }
      });

      const labels = Object.values(candMap).map(c => c.nombre);
      const dataAutorizados = Object.values(candMap).map(c => c.autorizados);
      const dataIrregulares = Object.values(candMap).map(c => c.irregulares);

      if (chartInstance) {
        chartInstance.destroy();
      }

      chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: '🟢 Votos Válidos Autorizados',
              data: dataAutorizados,
              backgroundColor: 'rgba(16, 185, 129, 0.75)',
              borderColor: '#10B981',
              borderWidth: 2,
              borderRadius: 8
            },
            {
              label: '🔴 Votos Irregulares Detectados',
              data: dataIrregulares,
              backgroundColor: 'rgba(239, 68, 68, 0.75)',
              borderColor: '#EF4444',
              borderWidth: 2,
              borderRadius: 8
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#F9FAFB', font: { family: 'Outfit', size: 13 } } }
          },
          scales: {
            x: { ticks: { color: '#9CA3AF', font: { family: 'Inter', size: 12 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { ticks: { color: '#9CA3AF', font: { family: 'Outfit', size: 12 }, precision: 0 }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true }
          }
        }
      });
    }

    function applyFilters() {
      if (!globalAuditData) return;

      const selMesa = document.getElementById("filterMesa").value;
      const selCand = document.getElementById("filterCandidato").value;
      const selEstado = document.getElementById("filterEstado").value;
      const searchVal = document.getElementById("searchInput").value.toLowerCase().trim();

      const filteredTx = globalAuditData.transacciones.filter(t => {
        if (selMesa !== "ALL" && t.mesa_id !== selMesa) return false;
        if (selCand !== "ALL" && t.candidato_id !== selCand) return false;
        if (selEstado === "VALIDO" && t.es_irregular) return false;
        if (selEstado === "IRREGULAR" && !t.es_irregular) return false;
        
        if (searchVal) {
          const matchHash = t.payment_hash.toLowerCase().includes(searchVal);
          const matchMemo = t.memo.toLowerCase().includes(searchVal);
          const matchCand = t.candidato_nombre.toLowerCase().includes(searchVal);
          const matchMesa = t.mesa_nombre.toLowerCase().includes(searchVal);
          if (!matchHash && !matchMemo && !matchCand && !matchMesa) return false;
        }
        return true;
      });

      // Actualizar Gráfico según el filtro aplicado
      updateChart(filteredTx);

      // Tabla Irregulares
      const irregularesTbody = document.getElementById("irregularesTableBody");
      const irregularesList = filteredTx.filter(t => t.es_irregular);

      irregularesTbody.innerHTML = irregularesList.map(t => `
        <tr>
          <td><strong>${t.candidato_nombre}</strong></td>
          <td><span style="color:#FCA5A5;">${t.mesa_nombre}</span></td>
          <td>${t.monto_sats.toLocaleString()} Sats</td>
          <td><strong>${t.votos_equivalentes}</strong></td>
          <td style="font-family:monospace; color:var(--accent-gold);">${t.payment_hash ? t.payment_hash.substring(0, 12) + '...' : '—'}</td>
          <td>${t.fecha}</td>
          <td><span class="badge-status badge-irregular">🔴 IRREGULAR</span></td>
        </tr>
      `).join("");

      if (irregularesList.length === 0) {
        irregularesTbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">✅ Sin votos irregulares registrados en esta selección.</td></tr>`;
      }

      // Tabla General (Pestaña 2)
      document.getElementById("txCountBadge").textContent = `${filteredTx.length} transacciones encontradas`;
      const generalTbody = document.getElementById("generalAuditTableBody");
      generalTbody.innerHTML = filteredTx.map(t => `
        <tr>
          <td>${t.mesa_nombre}</td>
          <td><strong>${t.candidato_nombre}</strong></td>
          <td>${t.monto_sats.toLocaleString()} Sats</td>
          <td><strong>${t.votos_equivalentes}</strong></td>
          <td style="font-family:monospace; color:var(--accent-gold);">${t.payment_hash ? t.payment_hash.substring(0, 14) + '...' : '—'}</td>
          <td>${t.fecha}</td>
          <td>
            ${t.es_irregular 
              ? '<span class="badge-status badge-irregular">🔴 IRREGULAR</span>'
              : '<span class="badge-status badge-valid">🟢 AUTORIZADO</span>'}
          </td>
        </tr>
      `).join("");

      if (filteredTx.length === 0) {
        generalTbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No hay registros que coincidan con los filtros.</td></tr>`;
      }
    }

    // Inicializar y refrescar cada 10 segundos
    loadAuditData();
    setInterval(loadAuditData, 30000);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_AUDIT_TEMPLATE, sats_per_vote=SATS_PER_VOTE)


@app.route("/api/candidato_foto/<candidato_id>")
def obtener_foto_candidato_audit(candidato_id):
    foto_paths = [
        BASE_DIR / "mesa_code" / "data_mesa" / "fotos" / f"{candidato_id}.png",
        BASE_DIR / "mesa_code" / "data_mesa" / "fotos" / f"{candidato_id}.jpg",
        BASE_DIR / "mesa_code" / "data_mesa" / "fotos" / f"{candidato_id}.jpeg",
        BASE_DIR / "data_mesa" / "fotos" / f"{candidato_id}.png",
        BASE_DIR / "mesa_code" / "web" / "templates" / "avatar_placeholder.svg"
    ]
    for p in foto_paths:
        if p and p.exists():
            return send_file(p)
    return "", 404


@app.route("/api/audit/ejecutar")
def api_ejecutar_auditoria():
    try:
        data = motor_auditoria.ejecutar_auditoria()
        return jsonify(data)
    except Exception as e:
        print(f"Error en /api/audit/ejecutar: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# MAIN / CLI
# ============================================================================

if __name__ == "__main__":
    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║  Dashboard de Auditoría Electoral LNbits - Red Tor - v3.0    ║
║  Reconciliación 1:1 & Detección de Votos Irregulares         ║
╚═══════════════════════════════════════════════════════════════╝
    """
    )

    print(f"📍 LNbits Endpoint: {LNBITS_ENDPOINT}")
    print(f"📋 Archivo Wallets Autorizadas: {WALLETS_CONFIG_FILE}")
    print(f"🗳️ Tasa de conversión: 1 voto = {SATS_PER_VOTE} sats")
    print("")

    # Ejecutar auditoría CLI inicial
    res = motor_auditoria.ejecutar_auditoria()
    print("📊 RESUMEN INICIAL DE AUDITORÍA:")
    print(f"   🟢 Votos Válidos Autorizados: {res['resumen']['votos_validos']}")
    print(f"   🔴 Votos Irregulares Detectados: {res['resumen']['votos_irregulares']}")
    print(f"   🛡️ Integridad Electoral: {res['resumen']['pct_integridad']}%")
    print("")
    print("🚀 Dashboard Interactivo disponible en: http://localhost:7070")
    print("")

    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=7070, debug=debug)
