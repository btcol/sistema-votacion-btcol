# LNBits Wallet Dashboard 🚀⚡ (Read-Only)

Dashboard interactivo en Python para **monitorear en tiempo real** el estado de múltiples wallets de LNBits. Versión de solo lectura usando Invoice Keys para máxima seguridad.

## 🎯 Características

✅ **Monitoreo en Tiempo Real**
- Visualización de saldo de múltiples wallets
- Estatus de conexión (online/offline)
- Actualización automática cada 30 segundos
- Historial de invoices/pagos recientes

✅ **Modo Read-Only (Seguro)**
- Usa Invoice Keys en lugar de Admin Keys
- Solo lectura: sin permisos de crear o pagar
- Perfecto para dashboards públicos o compartidos
- Máxima seguridad

✅ **Interfaz Moderna**
- Responsive design (funciona en móvil, tablet y desktop)
- Animaciones suaves
- Sistema de tarjetas intuitivo
- Indicadores de estado visual

✅ **API RESTful**
- Endpoints para obtener estado de wallets
- Endpoint para historial de pagos
- Respuestas JSON estructuradas
- Manejo robusto de errores

## 📋 Requisitos

### Sistema
- Python 3.8+
- pip (gestor de paquetes de Python)
- Acceso a una instancia de LNBits (local o remota)

### Paquetes Python
```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

### 1. Instalar dependencias

```bash
pip install flask flask-cors requests python-dotenv
```

O usar requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Obtener Invoice Keys de LNBits

Para cada wallet que quieras monitorear:

1. Abre tu instancia de LNBits
2. Selecciona la wallet (ej: "candidato1")
3. Ve a **API Keys** o **Acceso a la API**
4. Copia la **Invoice Key** (es la read-only key, más segura)

**⚠️ IMPORTANTE**: 
- Usa **Invoice Keys** (read-only), no Admin Keys
- Las Invoice Keys solo permiten lectura
- No pueden crear, pagar, ni modificar nada
- Perfectas para dashboards públicos

### 3. Configurar variables de entorno

**Opción A: Archivo .env (Recomendado)**

Copia el archivo de ejemplo:
```bash
cp .env.example .env
```

Edita `.env` con tus Invoice Keys:
```env
LNBITS_ENDPOINT=http://localhost:5000
WALLET_CANDIDATO1=tu_invoice_key_candidato1
WALLET_CANDIDATO2=tu_invoice_key_candidato2
WALLET_MESA0=tu_invoice_key_mesa0
```

**Opción B: Variables de entorno (Linux/Mac)**

```bash
export LNBITS_ENDPOINT="http://localhost:5000"
export WALLET_CANDIDATO1="tu_invoice_key_candidato1"
export WALLET_CANDIDATO2="tu_invoice_key_candidato2"
export WALLET_MESA0="tu_invoice_key_mesa0"
```

**Opción C: Variables de entorno (Windows PowerShell)**

```powershell
$env:LNBITS_ENDPOINT="http://localhost:5000"
$env:WALLET_CANDIDATO1="tu_invoice_key_candidato1"
$env:WALLET_CANDIDATO2="tu_invoice_key_candidato2"
$env:WALLET_MESA0="tu_invoice_key_mesa0"
```

## 🚀 Ejecución

### Opción 1: Ejecución directa

```bash
python lnbits_dashboard.py
```

### Opción 2: Con variables de entorno en línea (Linux/Mac)

```bash
LNBITS_ENDPOINT="http://localhost:5000" \
WALLET_CANDIDATO1="clave1" \
WALLET_CANDIDATO2="clave2" \
WALLET_MESA0="clave3" \
python lnbits_dashboard.py
```

### Opción 3: Setup interactivo

```bash
python setup.py
```

Este script se encarga de:
- Verificar Python 3.8+
- Instalar dependencias automáticamente
- Configurar .env interactivamente
- Probar la conexión con LNBits

## 🌐 Acceso al Dashboard

Una vez ejecutado, accede a:

```
http://localhost:5000
```

El dashboard mostrará:
- 📊 Tarjeta para cada wallet con saldo en tiempo real
- 🟢 Indicador de estado (online/offline)
- 📋 Últimos pagos/invoices de cada wallet
- 🔄 Botón para refrescar manualmente
- 🔒 Indicador de modo "Read Only"

## 📡 API Endpoints

### GET `/`
Retorna el dashboard HTML

### GET `/api/wallets/status`
Obtiene el estado de todas las wallets

**Respuesta:**
```json
{
  "success": true,
  "wallets": [
    {
      "name": "candidato1",
      "balance": 100000,
      "invoice_key": "abc12345...",
      "last_update": "2024-01-02T12:35:00",
      "is_available": true,
      "error_message": null
    }
  ]
}
```

### GET `/api/wallets/<wallet_name>/status`
Obtiene el estado de una wallet específica

**Ejemplo:**
```bash
curl http://localhost:5000/api/wallets/candidato1/status
```

### GET `/api/wallets/<wallet_name>/payments`
Obtiene el historial de pagos/invoices de una wallet

**Parámetros:**
- `limit` (opcional): Número máximo de pagos a retornar (default: 20)

**Ejemplo:**
```bash
curl http://localhost:5000/api/wallets/candidato1/payments?limit=10
```

### GET `/health`
Health check del servidor

**Respuesta:**
```json
{
  "status": "healthy",
  "mode": "read-only"
}
```

## 🔌 Integración con tu instancia de LNBits

### Endpoint Local (misma máquina)
```env
LNBITS_ENDPOINT=http://localhost:5000
```

### Endpoint Remoto (Tor/HTTPS)
```env
LNBITS_ENDPOINT=http://your-lnbits.onion
LNBITS_ENDPOINT=https://your-lnbits.com
```

### Endpoint en Red Local
```env
LNBITS_ENDPOINT=http://192.168.1.100:5000
```

## 🔒 Seguridad

### ¿Por qué Invoice Keys?

| Característica | Admin Key | Invoice Key |
|---|---|---|
| Ver balance | ✅ | ✅ |
| Ver pagos | ✅ | ✅ |
| Crear invoices | ✅ | ❌ |
| Pagar invoices | ✅ | ❌ |
| Modificar config | ✅ | ❌ |
| Eliminar datos | ✅ | ❌ |
| **Seguridad** | ⚠️ Crítica | ✅ Alta |

### Recomendaciones

1. **Usa Invoice Keys siempre**
   - No Admin Keys
   - Solo lectura
   - Máxima seguridad

2. **Protege tu instancia LNBits**
   - Usa HTTPS en producción
   - Configura autenticación
   - Restringe acceso por IP

3. **No versionices secretos**
   ```bash
   echo ".env" >> .gitignore
   ```

4. **Rota las keys regularmente**
   - Genera nuevas keys cada cierto tiempo
   - Revoca keys antiguas
   - Monitorea acceso

## 📊 Estructura del Código

```
lnbits_dashboard.py
├── Configuración          # Variables de entorno
├── Modelos de Datos       # WalletDetails, Payment
├── Cliente API            # Clase LNBitsClient (read-only)
├── Lógica de Negocio      # Clase WalletMonitor
├── Aplicación Flask       # Rutas y endpoints
└── Template HTML          # Interfaz web
```

## 🛠️ Características de Desarrollo

### Clase `LNBitsClient` (Read-Only)

```python
from lnbits_dashboard import LNBitsClient

client = LNBitsClient(
    endpoint="http://localhost:5000",
    invoice_key="your_invoice_key",
    timeout=10
)

# Obtener detalles de wallet
details = client.get_wallet_details()
print(f"Balance: {details['balance']} sats")

# Obtener pagos/invoices
payments = client.get_payments(limit=50)

# Verificar pago específico
status = client.check_payment(payment_hash="abc123...")

# Decodificar invoice
decoded = client.decode_invoice(bolt11="lnbc1000u1p3...")
```

### Clase `WalletMonitor`

```python
from lnbits_dashboard import WalletMonitor

monitor = WalletMonitor(
    endpoint="http://localhost:5000",
    wallets_config={
        "candidato1": "invoice_key_1",
        "candidato2": "invoice_key_2",
        "mesa0": "invoice_key_3"
    }
)

# Obtener estado de todas las wallets
statuses = monitor.get_all_wallets_status()

# Obtener estado de una wallet
status = monitor.get_wallet_status("candidato1")

# Obtener pagos
payments = monitor.get_wallet_payments("candidato1", limit=20)
```

## 🔧 Troubleshooting

### Error: "No se puede conectar a LNBits"
```
✓ Verifica que LNBits está corriendo
✓ Verifica la URL del ENDPOINT
✓ Comprueba firewall/puertos
✓ Revisa logs de LNBits
```

### Error: "Invoice key inválida"
```
✓ Verifica que copiaste la Invoice Key (no Admin Key)
✓ Copia sin espacios adicionales
✓ La key no debe estar expirada
✓ Verifica permisos en LNBits
```

### Error: "Timeout"
```
✓ Aumenta REQUEST_TIMEOUT en el código
✓ Verifica velocidad de red
✓ Comprueba si LNBits está sobrecargado
```

### Dashboard en blanco
```
✓ Abre la consola del navegador (F12)
✓ Revisa logs de Flask en terminal
✓ Verifica que los endpoints API responden:
   curl http://localhost:5000/api/wallets/status
```

## 📚 Recursos Adicionales

- [LNBits Documentación](https://docs.lnbits.org)
- [LNBits GitHub](https://github.com/lnbits/lnbits)
- [Lightning Network](https://lightning.network)
- [BOLT11 Invoices](https://github.com/lightningnetwork/lightning-rfc/blob/master/11-payment-encoding.md)

## 💡 Ejemplos de Uso

### Verificar saldo de todas las wallets

```bash
curl http://localhost:5000/api/wallets/status | jq '.wallets[] | {name, balance}'
```

### Ver historial de pagos

```bash
curl http://localhost:5000/api/wallets/candidato1/payments | jq '.payments'
```

### Monitoreo continuo (cada 10 segundos)

```bash
watch -n 10 'curl -s http://localhost:5000/api/wallets/status | jq'
```

## 🚀 Próximas Mejoras (Opcionales)

1. Agregar gráficos de balance en el tiempo
2. WebSockets para actualizaciones en tiempo real
3. Base de datos para historial persistente
4. Alertas por cambios de balance
5. Exportar reportes (CSV/PDF)
6. Soporte para más wallets dinámicamente

## 📄 Licencia

Este proyecto es software libre y de código abierto.

---

**Creado con ❤️ para la comunidad Lightning Network**

**Modo: 🔒 Solo Lectura (Read-Only)**
