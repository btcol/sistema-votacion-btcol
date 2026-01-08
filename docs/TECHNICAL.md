# LNBits Dashboard - Guía Técnica (Read-Only)

## Arquitectura del Sistema - Modo Read-Only

```
┌─────────────────────────────────────────────────────────────┐
│                      Navegador Web                          │
│                   (Dashboard HTML/JS)                       │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/REST (Solo GET)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask Application (Puerto 5000)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Rutas y Endpoints (Read-Only)                       │  │
│  │  - GET /              (Dashboard)                    │  │
│  │  - GET /api/wallets/status                           │  │
│  │  - GET /api/wallets/<name>/status                    │  │
│  │  - GET /api/wallets/<name>/payments                  │  │
│  │  - GET /health                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  WalletMonitor (Read-Only)                           │  │
│  │  - Gestiona múltiples clientes LNBits               │  │
│  │  - Solo lectura de estado                           │  │
│  │  - Sin operaciones de escritura                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LNBitsClient (x3 instancias - Read-Only)           │  │
│  │  - candidato1 client (Invoice Key)                   │  │
│  │  - candidato2 client (Invoice Key)                   │  │
│  │  - mesa0 client (Invoice Key)                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP GET + Invoice Keys (Read-Only)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              LNBits API (Remote/Local)                       │
│  - /api/v1/wallet            (obtener detalles) ✓           │
│  - /api/v1/payments          (ver historial) ✓              │
│  - /api/v1/payments/decode   (decodificar) ✓                │
│                                                              │
│  NO DISPONIBLE EN ESTE PROYECTO:                            │
│  - /api/v1/invoices          (crear invoices) ✗             │
│  - POST /api/v1/payments     (pagar) ✗                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
        Nodo Lightning Network
```

## Flujo de Datos (Read-Only)

### 1. Obtener Estado de Wallets

```
Usuario abre dashboard
    ↓
Navegador carga HTML + ejecuta JS
    ↓
JS hace fetch GET a /api/wallets/status
    ↓
Flask llama a monitor.get_all_wallets_status()
    ↓
WalletMonitor itera sobre todas las wallets
    ↓
Para cada wallet:
  - LNBitsClient.get_wallet_details()
  - HTTP GET a /api/v1/wallet con X-Api-Key (Invoice Key)
  - LNBits retorna balance e información
    ↓
Datos se envuelven en WalletDetails dataclass
    ↓
Se convierten a JSON y retornan al navegador
    ↓
JavaScript renderiza tarjetas con la información
```

### 2. Ver Historial de Pagos

```
Usuario visualiza tarjeta de wallet
    ↓
JavaScript hace fetch GET a /api/wallets/<name>/payments
    ↓
Flask llama a monitor.get_wallet_payments(wallet_name)
    ↓
LNBitsClient.get_payments(limit=20)
    ↓
HTTP GET a /api/v1/payments con X-Api-Key (Invoice Key)
    ↓
LNBits retorna lista de pagos/invoices
    ↓
Se procesan y formatean los datos
    ↓
JavaScript renderiza historial de pagos
```

## Diferencias: Admin Key vs Invoice Key

### Admin Key (NO USAR)
```python
# ❌ NO recomendado para este proyecto
admin_key = "f1234567890abcdef1234567890abcdef1234567890..."

# Permisos:
# - GET /api/v1/wallet                  ✓
# - GET /api/v1/payments                ✓
# - POST /api/v1/invoices               ✓ (crear)
# - POST /api/v1/payments               ✓ (pagar)
# - DELETE operaciones                  ✓
# 
# Riesgo: Si se expone, pueden robar fondos
```

### Invoice Key (USAR)
```python
# ✅ Recomendado para este proyecto
invoice_key = "e1234567890abcdef1234567890abcdef1234567890..."

# Permisos:
# - GET /api/v1/wallet                  ✓ (ver balance)
# - GET /api/v1/payments                ✓ (ver historial)
# - POST /api/v1/invoices               ✗ (NO puede crear)
# - POST /api/v1/payments               ✗ (NO puede pagar)
# - DELETE operaciones                  ✗
# 
# Ventaja: Seguro incluso si se expone públicamente
```

## Ejemplos de Uso

### Ejemplo 1: Monitoreo Simple

```python
#!/usr/bin/env python3
"""Script que monitorea wallets"""

import requests
import time

DASHBOARD_URL = "http://localhost:5000/api/wallets/status"

def check_wallets():
    """Verifica el estado de las wallets"""
    try:
        response = requests.get(DASHBOARD_URL, timeout=5)
        data = response.json()
        
        for wallet in data['wallets']:
            print(f"{wallet['name']}: {wallet['balance']} sats")
            
            if wallet['is_available']:
                print("✓ Online")
            else:
                print(f"✗ Offline: {wallet['error_message']}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("Iniciando monitor...")
    while True:
        check_wallets()
        time.sleep(60)
```

### Ejemplo 2: Usar LNBitsClient Directamente

```python
#!/usr/bin/env python3
"""Uso directo del cliente LNBits (Read-Only)"""

from lnbits_dashboard import LNBitsClient

# Crear cliente (SOLO con Invoice Key)
client = LNBitsClient(
    endpoint="http://localhost:5000",
    invoice_key="your_invoice_key",  # ✅ Invoice Key
    timeout=10
)

# 1. Obtener detalles de la wallet
details = client.get_wallet_details()
print(f"Balance: {details['balance']} sats")

# 2. Obtener historial de pagos
payments = client.get_payments(limit=10)
for payment in payments['payments']:
    print(f"- {payment['memo']}: {payment['amount']} sats (paid: {payment['paid']})")

# 3. Verificar pago específico
status = client.check_payment(
    payment_hash="abc123..."
)
print(f"Pagado: {status.get('paid')}")

# 4. Decodificar invoice
decoded = client.decode_invoice(
    bolt11="lnbc50000n1p3..."
)
print(f"Cantidad: {decoded.get('amount_msat')} msats")
```

### Ejemplo 3: Usar WalletMonitor

```python
#!/usr/bin/env python3
"""Uso del WalletMonitor para múltiples wallets"""

from lnbits_dashboard import WalletMonitor

# Inicializar monitor con Invoice Keys
monitor = WalletMonitor(
    endpoint="http://localhost:5000",
    wallets_config={
        "candidato1": "invoice_key_1",   # ✅ Invoice Keys
        "candidato2": "invoice_key_2",
        "mesa0": "invoice_key_3"
    }
)

# 1. Obtener estado de todas las wallets
all_wallets = monitor.get_all_wallets_status()
for wallet in all_wallets:
    print(f"{wallet.name}: {wallet.balance} sats")

# 2. Obtener estado de una wallet específica
wallet = monitor.get_wallet_status("candidato1")
if wallet.is_available:
    print(f"Candidato1 está online con {wallet.balance} sats")

# 3. Obtener pagos recientes
payments = monitor.get_wallet_payments("candidato1", limit=5)
for payment in payments:
    print(f"- {payment['memo']}: {payment['amount']} sats")
```

## Respuestas de API

### GET /api/wallets/status

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "wallets": [
    {
      "name": "candidato1",
      "balance": 100000,
      "invoice_key": "abc12345...",
      "last_update": "2024-01-02T12:35:00.123456",
      "is_available": true,
      "error_message": null
    }
  ]
}
```

### GET /api/wallets/candidato1/payments

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "payments": [
    {
      "amount": 1000,
      "memo": "Pago 1",
      "date": "2024-01-02T12:30:00",
      "paid": true,
      "payment_hash": "abc12345..."
    },
    {
      "amount": 500,
      "memo": "Pago 2",
      "date": "2024-01-02T12:25:00",
      "paid": false,
      "payment_hash": "def67890..."
    }
  ]
}
```

### GET /health

**Respuesta (200):**
```json
{
  "status": "healthy",
  "mode": "read-only"
}
```

## Debugging

### Ver logs de Flask

```bash
# Terminal 1: Ejecutar dashboard con debug
FLASK_DEBUG=True python lnbits_dashboard.py

# Terminal 2: Ver requests en tiempo real
curl -v http://localhost:5000/api/wallets/status
```

### Probar endpoints manualmente

```bash
# Obtener estado de todas las wallets
curl http://localhost:5000/api/wallets/status | jq

# Obtener estado de una wallet
curl http://localhost:5000/api/wallets/candidato1/status | jq

# Obtener pagos
curl http://localhost:5000/api/wallets/candidato1/payments | jq
```

### Verificar conectividad con LNBits

```bash
# Revisar si LNBits está corriendo
curl http://localhost:5000/health

# Probar con una invoice key
curl -H "X-Api-Key: your_invoice_key" \
  http://localhost:5000/api/v1/wallet

# Ver si la key es válida
curl -H "X-Api-Key: your_invoice_key" \
  http://localhost:5000/api/v1/payments
```

## Seguridad

### Por qué Invoice Keys son seguras

1. **Solo lectura**: No pueden crear ni pagar invoices
2. **No modifican**: No pueden cambiar configuración
3. **No eliminan**: No pueden borrar datos
4. **Públicamente compartibles**: Puedes mostrar el dashboard públicamente
5. **Revocables**: Puedes generar nuevas keys cuando quieras

### Mejores prácticas

1. **Siempre usa Invoice Keys**
   ```env
   WALLET_CANDIDATO1=your_invoice_key  # ✓ Correcto
   WALLET_CANDIDATO1=your_admin_key    # ✗ Incorrecto
   ```

2. **Rota las keys regularmente**
   - Genera nuevas keys cada mes
   - Revoca las antiguas en LNBits

3. **Monitorea el acceso**
   - Revisa logs de LNBits
   - Verifica que solo tú accedes

4. **Usa HTTPS en producción**
   - Encripta las comunicaciones
   - Protege contra eavesdropping

## Performance

### Caching
El dashboard actualiza cada 30 segundos. Puedes cambiar en JavaScript:

```javascript
// Cambiar intervalo de actualización (en milisegundos)
setInterval(loadWalletStatus, 30000);  // 30 segundos
setInterval(loadWalletStatus, 60000);  // 60 segundos
```

### Optimizaciones posibles

1. **Caché en servidor**: Guardar resultados por 30 segundos
2. **Bases de datos**: Guardar historial en SQLite
3. **WebSockets**: Actualizaciones en tiempo real
4. **Compresión**: Comprimir respuestas JSON

## Extensiones Futuras

1. **Gráficos**: Visualizar tendencias de balance
2. **Base de datos**: Historial persistente
3. **Alertas**: Notificaciones por cambios
4. **Estadísticas**: Reportes y análisis
5. **Multi-idioma**: Soporte en diferentes idiomas

---

**Este proyecto es 100% read-only usando Invoice Keys**
