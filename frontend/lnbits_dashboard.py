#!/usr/bin/env python3
"""
LNBits Wallet Dashboard - Read Only Version (Escalable)
Visualiza el estado de múltiples wallets de LNBits a través de una interfaz web.
Versión de solo lectura usando Invoice Keys con configuración escalable desde wallets.json

Uso:
    python lnbits_dashboard.py

Luego accede a: http://localhost:5000

"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Directorio raíz del proyecto (2 niveles arriba desde frontend/)
BASE_DIR = Path(__file__).resolve().parent.parent  # frontend/ -> raíz
DATA_DIR = BASE_DIR / 'data'

# ============================================================================
# CARGAR VARIABLES DE ENTORNO DESDE .env
# ============================================================================

try:
    from dotenv import load_dotenv
    load_dotenv(DATA_DIR / '.env', override=True)
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables del sistema.")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# LNBits Endpoint
LNBITS_ENDPOINT = os.getenv("LNBITS_ENDPOINT", "http://localhost:5000").rstrip("/")

# Archivo de configuración de wallets
WALLETS_CONFIG_FILE = DATA_DIR / 'wallets.json'

# Configuración de votación
SATS_PER_VOTE = int(os.getenv("SATS_PER_VOTE", "100"))
SHOW_SATS_AND_VOTES = os.getenv("SHOW_SATS_AND_VOTES", "true").lower() == "true"

# Timeout para requests
REQUEST_TIMEOUT = 10

# ============================================================================
# FUNCIONES DE CARGA DE CONFIGURACIÓN
# ============================================================================


def load_wallets_config() -> Dict:
    """
    Carga la configuración de wallets desde archivo JSON
    
    Returns:
        Dict con estructura: {'candidatos': {...}, 'mesas': {...}}
    """
    config_file = Path(WALLETS_CONFIG_FILE)
    
    if not config_file.exists():
        raise FileNotFoundError(
            f"Archivo {WALLETS_CONFIG_FILE} no encontrado.\n"
            f"Copia wallets.example.json a {WALLETS_CONFIG_FILE} y edita con tus Invoice Keys"
        )
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Error parseando {WALLETS_CONFIG_FILE}. Asegúrate que es JSON válido.\n"
            f"Error: {e}"
        )


# Cargar configuración de wallets
try:
    WALLETS_CONFIG = load_wallets_config()
except (FileNotFoundError, ValueError) as e:
    print(f"❌ Error al cargar configuración: {e}")
    WALLETS_CONFIG = {"candidatos": {}, "mesas": {}}


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
        """Validar datos"""
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
# CLIENTE API DE LNBITS
# ============================================================================


class LNBitsClient:
    """Cliente read-only para interactuar con la API de LNBits"""

    def __init__(self, endpoint: str, invoice_key: str, timeout: int = 10):
        """
        Inicializa el cliente de LNBits (read-only)

        Args:
            endpoint: URL base de LNBits (ej: http://localhost:5000)
            invoice_key: Invoice key (read-only) de la wallet
            timeout: Timeout en segundos para las requests
        """
        self.endpoint = endpoint.rstrip("/")
        self.invoice_key = invoice_key
        self.timeout = timeout

    def _make_request(
        self, method: str, path: str, **kwargs
    ) -> Optional[Dict]:
        """
        Realiza una request a la API de LNBits

        Args:
            method: GET, POST, etc.
            path: Ruta del endpoint (ej: /api/v1/wallet)
            **kwargs: Argumentos adicionales para requests

        Returns:
            Respuesta JSON parseada o None en caso de error
        """
        url = f"{self.endpoint}{path}"
        headers = {"X-Api-Key": self.invoice_key, "Content-Type": "application/json"}

        try:
            if method.upper() == "GET":
                response = requests.get(
                    url, headers=headers, timeout=self.timeout, **kwargs
                )
            else:
                raise ValueError(f"Método HTTP no soportado en modo read-only: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout en {path}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 Error de conexión a {url}")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error HTTP {e.response.status_code} en {path}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en request: {e}")
            return None
        except json.JSONDecodeError:
            print(f"❌ Respuesta no es JSON válido")
            return None

    def get_wallet_details(self) -> Optional[Dict]:
        """Obtiene los detalles de la wallet"""
        return self._make_request("GET", "/api/v1/wallet")

    def get_payments(self, limit: int = 50) -> Optional[Dict]:
        """Obtiene el historial de pagos/invoices de la wallet"""
        return self._make_request("GET", f"/api/v1/payments?limit={limit}")

    def check_payment(self, payment_hash: str) -> Optional[Dict]:
        """Verifica el estado de un pago usando el payment_hash"""
        return self._make_request("GET", f"/api/v1/payments/{payment_hash}")

    def decode_invoice(self, bolt11: str) -> Optional[Dict]:
        """Decodifica una factura para obtener información"""
        return self._make_request(
            "GET", f"/api/v1/payments/decode?data={bolt11}"
        )


# ============================================================================
# LÓGICA DE NEGOCIO
# ============================================================================


class VoteConverter:
    """Convertidor de sats a votos"""
    
    def __init__(self, sats_per_vote: int):
        self.sats_per_vote = sats_per_vote
    
    def convert(self, sats: int) -> VoteInfo:
        """
        Convierte sats a votos (redondeo hacia abajo)
        
        Args:
            sats: Cantidad en satoshis
            
        Returns:
            VoteInfo con votos, sats restantes, etc.
        """
        votos = sats // self.sats_per_vote  # Floor division
        sats_remainder = sats % self.sats_per_vote
        
        return VoteInfo(
            votos=votos,
            sats=sats,
            sats_remainder=sats_remainder
        )


class WalletMonitor:
    """Monitor de estado de wallets (read-only, escalable)"""

    def __init__(self, endpoint: str, wallets_config: Dict):
        """
        Inicializa el monitor

        Args:
            endpoint: URL base de LNBits
            wallets_config: Dict {candidatos: {...}, mesas: {...}}
        """
        self.endpoint = endpoint
        self.wallets_config = wallets_config
        self.clients: Dict[str, LNBitsClient] = {}
        self.vote_converter = VoteConverter(SATS_PER_VOTE)
        self._init_clients()

    def _init_clients(self):
        """Inicializa clientes para todas las wallets"""
        for wallet_type in ['candidatos', 'mesas']:
            if wallet_type not in self.wallets_config:
                continue
                
            for wallet_name, wallet_info in self.wallets_config[wallet_type].items():
                invoice_key = wallet_info.get('invoice_key')
                if invoice_key:
                    self.clients[wallet_name] = LNBitsClient(
                        self.endpoint, invoice_key, timeout=REQUEST_TIMEOUT
                    )

    def _get_wallet_type(self, wallet_name: str) -> Optional[WalletType]:
        """Obtiene el tipo de wallet (candidato o mesa)"""
        if wallet_name in self.wallets_config.get('candidatos', {}):
            return WalletType.CANDIDATO
        elif wallet_name in self.wallets_config.get('mesas', {}):
            return WalletType.MESA
        return None

    def get_wallet_status(self, wallet_name: str) -> Optional[WalletDetails]:
        """Obtiene el estado actual de una wallet"""
        if wallet_name not in self.clients:
            return None

        client = self.clients[wallet_name]
        wallet_type = self._get_wallet_type(wallet_name)
        
        # Obtener información de la wallet
        if wallet_type == WalletType.CANDIDATO:
            wallet_info = self.wallets_config['candidatos'].get(wallet_name, {})
        else:
            wallet_info = self.wallets_config['mesas'].get(wallet_name, {})

        display_name = wallet_info.get('display_name', wallet_name)

        try:
            response = client.get_wallet_details()

            if response is None:
                return WalletDetails(
                    name=wallet_name,
                    display_name=display_name,
                    wallet_type=wallet_type,
                    balance=0,
                    vote_info=self.vote_converter.convert(0),
                    invoice_key=wallet_info.get('invoice_key', '')[:10] + "...",
                    last_update=datetime.now().isoformat(),
                    is_available=False,
                    error_message="No response from API",
                )

            balance = response.get("balance", 0) // 1000   # Convertir msat a sats
            vote_info = self.vote_converter.convert(balance)

            return WalletDetails(
                name=wallet_name,
                display_name=display_name,
                wallet_type=wallet_type,
                balance=balance,
                vote_info=vote_info,
                invoice_key=wallet_info.get('invoice_key', '')[:10] + "...",
                last_update=datetime.now().isoformat(),
                is_available=True,
                error_message=None,
            )

        except Exception as e:
            print(f"Error consultando wallet {wallet_name}: {e}")
            return WalletDetails(
                name=wallet_name,
                display_name=display_name,
                wallet_type=wallet_type,
                balance=0,
                vote_info=self.vote_converter.convert(0),
                invoice_key=wallet_info.get('invoice_key', '')[:10] + "...",
                last_update=datetime.now().isoformat(),
                is_available=False,
                error_message=str(e),
            )

    def get_all_wallets_status(self) -> List[WalletDetails]:
        """Obtiene el estado de todas las wallets"""
        status_list = []
        
        # Procesar candidatos
        for wallet_name in self.wallets_config.get('candidatos', {}).keys():
            status = self.get_wallet_status(wallet_name)
            if status:
                status_list.append(status)
        
        # Procesar mesas
        for wallet_name in self.wallets_config.get('mesas', {}).keys():
            status = self.get_wallet_status(wallet_name)
            if status:
                status_list.append(status)
        
        return status_list

    def get_candidatos_status(self) -> List[WalletDetails]:
        """Obtiene el estado de todos los candidatos"""
        status_list = []
        for wallet_name in self.wallets_config.get('candidatos', {}).keys():
            status = self.get_wallet_status(wallet_name)
            if status:
                status_list.append(status)
        return status_list

    def get_mesas_status(self) -> List[WalletDetails]:
        """Obtiene el estado de todas las mesas"""
        status_list = []
        for wallet_name in self.wallets_config.get('mesas', {}).keys():
            status = self.get_wallet_status(wallet_name)
            if status:
                status_list.append(status)
        return status_list

    def get_wallet_payments(self, wallet_name: str, limit: int = 20) -> List[Dict]:
        """Obtiene pagos/invoices recientes de una wallet"""
        if wallet_name not in self.clients:
            return []

        client = self.clients[wallet_name]
        response = client.get_payments(limit=limit)

        if response and "payments" in response:
            payments = []
            for payment in response["payments"][:limit]:
                payments.append(
                    {
                        "amount": payment.get("amount"),
                        "memo": payment.get("memo", "N/A"),
                        "date": payment.get("date"),
                        "paid": payment.get("paid", False),
                        "payment_hash": payment.get("payment_hash", "")[:10] + "...",
                    }
                )
            return payments
        return []


# ============================================================================
# APLICACIÓN FLASK
# ============================================================================

app = Flask(__name__)
CORS(app)

# Inicializar monitor
monitor = WalletMonitor(LNBITS_ENDPOINT, WALLETS_CONFIG)


# HTML TEMPLATE
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LNBits Wallet Dashboard - Read Only</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        header .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-top: 10px;
            backdrop-filter: blur(10px);
        }

        header p {
            font-size: 1.1em;
            opacity: 0.9;
            margin-top: 5px;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .tab-btn {
            padding: 10px 20px;
            border: 2px solid white;
            background: rgba(255,255,255,0.2);
            color: white;
            border-radius: 20px;
            cursor: pointer;
            font-weight: 600;
            font-size: 1em;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        .tab-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }

        .tab-btn.active {
            background: white;
            color: #667eea;
            border-color: white;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .wallet-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .wallet-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }

        .wallet-card.offline {
            opacity: 0.6;
            border-left: 5px solid #ff6b6b;
        }

        .wallet-card.online {
            border-left: 5px solid #51cf66;
        }

        .wallet-card.candidato::before {
            content: "👥";
            position: absolute;
            top: 10px;
            right: 15px;
            font-size: 1.5em;
        }

        .wallet-card.mesa::before {
            content: "🏛️";
            position: absolute;
            top: 10px;
            right: 15px;
            font-size: 1.5em;
        }

        .wallet-card {
            position: relative;
        }

        .wallet-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
            padding-right: 40px;
        }

        .wallet-name {
            font-size: 1.5em;
            font-weight: 700;
            color: #333;
        }

        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .status-badge.online {
            background: #d3f9d8;
            color: #2b8a3e;
        }

        .status-badge.offline {
            background: #ffe0e0;
            color: #c92a2a;
        }

        .wallet-info {
            margin-bottom: 20px;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }

        .info-label {
            font-weight: 600;
            color: #666;
        }

        .info-value {
            color: #333;
            font-family: 'Courier New', monospace;
            text-align: right;
            word-break: break-word;
            flex: 1;
            margin-left: 10px;
        }

        .balance {
            font-size: 1.8em;
            font-weight: 700;
            color: #667eea;
            text-align: center;
            padding: 15px;
            background: #f8f9ff;
            border-radius: 8px;
            margin: 15px 0;
        }

        .balance-votes {
            font-size: 2.2em;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .balance-unit {
            font-size: 0.6em;
            color: #999;
            display: block;
            font-weight: 400;
        }

        .balance-type {
            font-size: 0.5em;
            color: #667eea;
            font-weight: 600;
            margin-top: 5px;
        }

        .vote-remainder {
            font-size: 0.8em;
            color: #ff9800;
            margin-top: 8px;
            padding: 8px;
            background: #fff3e0;
            border-radius: 4px;
        }

        .actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        button {
            flex: 1;
            padding: 10px 15px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9em;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5568d3;
            transform: scale(1.02);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .error-message {
            background: #fff3cd;
            color: #856404;
            padding: 12px;
            border-radius: 6px;
            margin-top: 10px;
            border-left: 4px solid #ffc107;
        }

        .payment-history {
            margin-top: 20px;
            max-height: 250px;
            overflow-y: auto;
            border-top: 2px solid #f0f0f0;
            padding-top: 15px;
        }

        .payment-history h4 {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }

        .payment-item {
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            font-size: 0.85em;
            display: flex;
            justify-content: space-between;
        }

        .payment-item:last-child {
            border-bottom: none;
        }

        .payment-amount {
            font-weight: 600;
            color: #667eea;
        }

        .payment-status {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 600;
        }

        .payment-status.paid {
            background: #d3f9d8;
            color: #2b8a3e;
        }

        .payment-status.pending {
            background: #fff3cd;
            color: #856404;
        }

        .footer {
            text-align: center;
            color: white;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.2);
            opacity: 0.8;
        }

        .mode-badge {
            display: inline-block;
            background: rgba(255,255,255,0.15);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75em;
            margin-left: 10px;
            backdrop-filter: blur(10px);
        }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .wallet-card.hidden {
            display: none;
        }

        @media (max-width: 768px) {
            header h1 {
                font-size: 1.8em;
            }

            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .actions {
                flex-direction: column;
            }

            .tabs {
                gap: 5px;
            }

            .tab-btn {
                padding: 8px 15px;
                font-size: 0.9em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Sistema de Votación
                <span class="mode-badge">🔒 Read Only</span>
            </h1>
            <div class="badge">Conteo de Votos en Tiempo Real</div>
            <p>Estado en tiempo real de candidatos y mesas electorales</p>
        </header>

        <!-- Tabs/Filtros -->
        <div class="tabs">
            <button class="tab-btn active" onclick="filterView('all')">
                📊 Todos
            </button>
            <button class="tab-btn" onclick="filterView('candidatos')">
                👥 Candidatos
            </button>
            <button class="tab-btn" onclick="filterView('mesas')">
                🏛️ Mesas Electorales
            </button>
        </div>

        <div class="dashboard-grid" id="walletContainer">
            <div style="grid-column: 1/-1; text-align: center; color: white;">
                <div class="spinner"></div>
                <p style="margin-top: 15px;">Cargando estado de wallets...</p>
            </div>
        </div>

        <div class="footer">
            <p>🔐 Modo: Solo lectura (Invoice Keys)</p>
            <p>Tasa de conversión: 1 voto = {{ sats_per_vote }} sats</p>
            <p>Última actualización: <span id="lastUpdate">—</span></p>
        </div>
    </div>

    <script>
        const SATS_PER_VOTE = {{ sats_per_vote }};
        const SHOW_BOTH = {{ show_both_lower }};
        let currentFilter = 'all';
        
        async function loadWalletStatus() {
            try {
                const response = await fetch("/api/wallets/status");
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || "Error al cargar estado");
                }

                renderWallets(data.wallets);
                document.getElementById("lastUpdate").textContent = new Date().toLocaleTimeString('es-ES');
            } catch (error) {
                console.error("Error:", error);
                document.getElementById("walletContainer").innerHTML = `
                    <div style="grid-column: 1/-1; color: white;">
                        <div class="error-message" style="background: #f8d7da; color: #721c24; border-color: #f5c6cb;">
                            ❌ Error al conectar: ${error.message}
                        </div>
                    </div>
                `;
            }
        }

        async function loadPayments(walletName) {
            try {
                const response = await fetch(`/api/wallets/${walletName}/payments`);
                const data = await response.json();
                
                if (data.success && data.payments) {
                    return data.payments;
                }
                return [];
            } catch (error) {
                console.error("Error cargando pagos:", error);
                return [];
            }
        }

        function formatBalance(walletData) {
            const votes = walletData.vote_info.votos;
            const sats = walletData.vote_info.sats;
            const walletType = walletData.wallet_type;

            let display = `<div class="balance-votes">${votes}</div>`;
            
            if (walletType === 'candidato') {
                display += '<div class="balance-type">VOTOS</div>';
                if (SHOW_BOTH) {
                    display += `<span class="balance-unit">(${sats.toLocaleString()} sats)</span>`;
                }
            } else {
                // Para mesas, mostrar votos remanentes (sats remainder)
                const remainder = walletData.vote_info.sats_remainder;
                display += '<div class="balance-type">VOTOS REMANENTES</div>';
                if (SHOW_BOTH) {
                    display += `<span class="balance-unit">(${remainder} sats sin completar voto)</span>`;
                }
            }

            return display;
        }

        function renderWallets(wallets) {
            const container = document.getElementById("walletContainer");
            
            Promise.all(wallets.map(async (wallet) => {
                const payments = await loadPayments(wallet.name);
                return { wallet, payments };
            })).then(results => {
                container.innerHTML = results.map(({ wallet, payments }) => {
                    const typeClass = wallet.wallet_type === 'candidato' ? 'candidato' : 'mesa';
                    const typeFilter = wallet.wallet_type === 'candidato' ? 'candidatos' : 'mesas';
                    
                    return `
                        <div class="wallet-card ${typeClass} ${wallet.is_available ? 'online' : 'offline'} ${currentFilter !== 'all' && currentFilter !== typeFilter ? 'hidden' : ''}" data-type="${typeFilter}">
                            <div class="wallet-header">
                                <div>
                                    <span class="wallet-name">${wallet.display_name}</span>
                                </div>
                                <span class="status-badge ${wallet.is_available ? 'online' : 'offline'}">
                                    ${wallet.is_available ? '🟢 En línea' : '🔴 Offline'}
                                </span>
                            </div>

                            ${wallet.is_available ? `
                                <div class="balance">
                                    ${formatBalance(wallet)}
                                </div>

                                <div class="wallet-info">
                                    <div class="info-row">
                                        <span class="info-label">Saldо Total:</span>
                                        <span class="info-value">${wallet.vote_info.sats.toLocaleString()} sats</span>
                                    </div>
                                    <div class="info-row">
                                        <span class="info-label">Última actualización:</span>
                                        <span class="info-value">${new Date(wallet.last_update).toLocaleTimeString('es-ES')}</span>
                                    </div>
                                </div>

                                ${wallet.vote_info.sats_remainder > 0 ? `
                                    <div class="vote-remainder">
                                        ℹ️ ${wallet.vote_info.sats_remainder} sats remanentes (< 1 voto)
                                    </div>
                                ` : ''}

                                ${payments.length > 0 ? `
                                    <div class="payment-history">
                                        <h4>📋 Últimos Pagos/Invoices (${payments.length})</h4>
                                        ${payments.map(p => `
                                            <div class="payment-item">
                                                <div>
                                                    <div style="font-weight: 600;">${p.amount} sats</div>
                                                    <div style="color: #999; font-size: 0.8em;">${p.memo}</div>
                                                </div>
                                                <span class="payment-status ${p.paid ? 'paid' : 'pending'}">
                                                    ${p.paid ? '✓ Pagado' : '⏳ Pendiente'}
                                                </span>
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : ''}

                                <div class="actions">
                                    <button class="btn-primary" onclick="refreshWallet('${wallet.name}')">
                                        🔄 Refrescar
                                    </button>
                                </div>
                            ` : `
                                <div class="error-message">
                                    ${wallet.error_message || 'No se pudo conectar'}
                                </div>
                            `}
                        </div>
                    `;
                }).join("");
                applyFilter(currentFilter);
            });
        }

        function filterView(filter) {
            currentFilter = filter;
            
            // Actualizar botones activos
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Aplicar filtro
            applyFilter(filter);
        }

        function applyFilter(filter) {
            document.querySelectorAll('.wallet-card').forEach(card => {
                if (filter === 'all') {
                    card.classList.remove('hidden');
                } else {
                    const cardType = card.getAttribute('data-type');
                    if (cardType === filter) {
                        card.classList.remove('hidden');
                    } else {
                        card.classList.add('hidden');
                    }
                }
            });
        }

        async function refreshWallet(walletName) {
            loadWalletStatus();
        }

        // Cargar estado inicial y refrescar cada 30 segundos
        loadWalletStatus();
        setInterval(loadWalletStatus, 30000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Página principal del dashboard"""
    return render_template_string(
        HTML_TEMPLATE,
        sats_per_vote=SATS_PER_VOTE,
        show_both_lower="true" if SHOW_SATS_AND_VOTES else "false"
    )


@app.route("/api/wallets/status")
def get_wallets_status():
    """API: Obtener estado de todas las wallets"""
    try:
        wallets_status = monitor.get_all_wallets_status()
        return jsonify(
            {
                "success": True,
                "wallets": [asdict(w) for w in wallets_status],
            }
        )
    except Exception as e:
        print(f"Error en /api/wallets/status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/candidatos/status")
def get_candidatos_status():
    """API: Obtener estado de todos los candidatos"""
    try:
        wallets_status = monitor.get_candidatos_status()
        return jsonify(
            {
                "success": True,
                "wallets": [asdict(w) for w in wallets_status],
            }
        )
    except Exception as e:
        print(f"Error en /api/candidatos/status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/mesas/status")
def get_mesas_status():
    """API: Obtener estado de todas las mesas"""
    try:
        wallets_status = monitor.get_mesas_status()
        return jsonify(
            {
                "success": True,
                "wallets": [asdict(w) for w in wallets_status],
            }
        )
    except Exception as e:
        print(f"Error en /api/mesas/status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/wallets/<wallet_name>/status")
def get_wallet_status(wallet_name: str):
    """API: Obtener estado de una wallet específica"""
    try:
        status = monitor.get_wallet_status(wallet_name)
        if status is None:
            return jsonify({"success": False, "error": "Wallet no encontrada"}), 404

        return jsonify({"success": True, "wallet": asdict(status)})
    except Exception as e:
        print(f"Error en /api/wallets/{wallet_name}/status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/wallets/<wallet_name>/payments")
def get_wallet_payments(wallet_name: str):
    """API: Obtener pagos/invoices recientes de una wallet"""
    try:
        limit = request.args.get("limit", 20, type=int)
        payments = monitor.get_wallet_payments(wallet_name, limit)
        return jsonify({"success": True, "payments": payments})
    except Exception as e:
        print(f"Error en /api/wallets/{wallet_name}/payments: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/config")
def get_config():
    """API: Obtener configuración de conversión"""
    return jsonify({
        "success": True,
        "sats_per_vote": SATS_PER_VOTE,
        "show_both": SHOW_SATS_AND_VOTES
    })


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "mode": "read-only"})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║  LNBits Wallet Dashboard - Votación - Read Only Mode - v3.0  ║
╚═══════════════════════════════════════════════════════════════╝
    """
    )

    print(f"📍 LNBits Endpoint: {LNBITS_ENDPOINT}")
    print(f"📋 Archivo de configuración: {WALLETS_CONFIG_FILE}")
    print(f"🗳️  Tasa de conversión: 1 voto = {SATS_PER_VOTE} sats")
    print(f"📊 Mostrar sats y votos: {SHOW_SATS_AND_VOTES}")
    print(f"🔒 Modo: Solo lectura (Invoice Keys)")
    print("")
    print("📊 WALLETS CARGADAS:")
    print(f"   👥 Candidatos: {len(WALLETS_CONFIG.get('candidatos', {}))}")
    for name, info in WALLETS_CONFIG.get('candidatos', {}).items():
        print(f"      - {info.get('display_name', name)}")
    print(f"   🏛️  Mesas: {len(WALLETS_CONFIG.get('mesas', {}))}")
    for name, info in WALLETS_CONFIG.get('mesas', {}).items():
        print(f"      - {info.get('display_name', name)}")
    print("")
    print("🚀 Dashboard disponible en: http://localhost:5000")
    print("")

    # Detectar ambiente
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug,
        use_reloader=debug,
    )
