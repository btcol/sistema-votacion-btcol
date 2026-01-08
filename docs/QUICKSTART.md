# Referencia Rápida - LNBits Dashboard v3.0

## 🚀 Inicio en 4 Pasos

### 1. Instalar
```bash
pip install -r requirements.txt
```

### 2. Configurar Wallets
```bash
# Copiar ejemplo
cp wallets.example.json wallets.json

# Editar con tus Invoice Keys
nano wallets.json
```

**Estructura de wallets.json:**
```json
{
  "candidatos": {
    "candidato1": {
      "invoice_key": "your_key_here",
      "display_name": "Candidato A"
    },
    "candidato2": { ... }
  },
  "mesas": {
    "mesa0": {
      "invoice_key": "your_key_here",
      "display_name": "Mesa Electoral 0"
    }
  }
}
```

### 3. Configurar .env
```bash
cp .env.example .env
nano .env
```

**Variables principales:**
```env
LNBITS_ENDPOINT=http://localhost:5000
WALLETS_CONFIG_FILE=wallets.json
SATS_PER_VOTE=100
SHOW_SATS_AND_VOTES=true
```

### 4. Ejecutar
```bash
python lnbits_dashboard.py
```

Accede a: **http://localhost:5000**

---

## 📊 Novedades v3.0

### ✨ Nuevas Características

#### 🗳️ Sistema de Votación
- **Candidatos**: Muestran total de votos completados
- **Mesas**: Muestran votos remanentes (sats sin completar un voto)
- **Conversión escalable**: Configurable via `SATS_PER_VOTE` en `.env`

#### 🔄 Arquitectura Escalable
- ✅ Añade 100 candidatos sin tocar código
- ✅ Añade 50 mesas sin tocar código
- ✅ Solo edita `wallets.json`
- ✅ Cambios se aplican automáticamente

#### 🎨 Pestañas de Filtro
- **Todos** - Ve candidatos y mesas juntos
- **Candidatos** - Solo candidatos (👥 votos completados)
- **Mesas** - Solo mesas (🏛️ votos remanentes)

#### 📱 Responsivo
- Diseño adaptativo para móvil, tablet, desktop
- Interfaz moderna con gradientes y animaciones
- Actualización automática cada 30 segundos

---

## 📝 Archivo wallets.json

### Formato Básico
```json
{
  "candidatos": {
    "candidato1": {
      "invoice_key": "your_invoice_key_here",
      "display_name": "Candidato A"
    },
    "candidato2": {
      "invoice_key": "your_invoice_key_here",
      "display_name": "Candidato B"
    }
  },
  "mesas": {
    "mesa0": {
      "invoice_key": "your_invoice_key_here",
      "display_name": "Mesa Electoral 0"
    },
    "mesa1": {
      "invoice_key": "your_invoice_key_here",
      "display_name": "Mesa Electoral 1"
    }
  }
}
```

### Ejemplo con 10 Candidatos y 5 Mesas
```json
{
  "candidatos": {
    "candidato1": {
      "invoice_key": "key1",
      "display_name": "Juan García"
    },
    "candidato2": {
      "invoice_key": "key2",
      "display_name": "María López"
    },
    "candidato3": {
      "invoice_key": "key3",
      "display_name": "Carlos Rodríguez"
    }
    // ... más candidatos
  },
  "mesas": {
    "mesa0": {
      "invoice_key": "key0",
      "display_name": "Mesa Electoral Zona Centro"
    },
    "mesa1": {
      "invoice_key": "key1",
      "display_name": "Mesa Electoral Zona Norte"
    }
    // ... más mesas
  }
}
```

---

## 🔧 Archivo .env

```env
# ============================================================================
# LNBITS SERVER CONFIGURATION
# ============================================================================

# URL de tu instancia de LNBits
LNBITS_ENDPOINT=http://localhost:5000

# ============================================================================
# WALLETS CONFIGURATION
# ============================================================================

# Archivo JSON con configuración de wallets (será cargado automáticamente)
WALLETS_CONFIG_FILE=wallets.json

# ============================================================================
# VOTACIÓN CONFIGURATION
# ============================================================================

# Conversión de sats a votos (redondeo hacia abajo)
# Ejemplo: 100 sats = 1 voto
# Así que 250 sats = 2 votos (50 sats remanentes)
SATS_PER_VOTE=100

# Mostrar tanto votos como sats en la interfaz
# true: "2340 votos (234,000 sats)"
# false: Solo "2340 votos"
SHOW_SATS_AND_VOTES=true

# ============================================================================
# FLASK CONFIGURATION
# ============================================================================

FLASK_DEBUG=False
# FLASK_PORT=5000  # Descomentar para cambiar puerto
```

---

## 📡 API Endpoints

### Nuevos Endpoints v3.0

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Dashboard HTML con pestañas |
| GET | `/api/wallets/status` | Candidatos + Mesas |
| GET | `/api/candidatos/status` | Solo candidatos |
| GET | `/api/mesas/status` | Solo mesas |
| GET | `/api/wallets/<name>/status` | Wallet específica |
| GET | `/api/wallets/<name>/payments` | Pagos/invoices de wallet |
| GET | `/api/config` | Configuración de conversión |
| GET | `/health` | Health check |

### Ejemplos de Uso

```bash
# Ver estado de todos (candidatos + mesas)
curl http://localhost:5000/api/wallets/status | jq

# Ver solo candidatos
curl http://localhost:5000/api/candidatos/status | jq

# Ver solo mesas
curl http://localhost:5000/api/mesas/status | jq

# Ver wallet específica
curl http://localhost:5000/api/wallets/candidato1/status | jq

# Ver configuración de conversión
curl http://localhost:5000/api/config | jq

# Ver pagos/invoices
curl http://localhost:5000/api/wallets/candidato1/payments?limit=10 | jq
```

### Ejemplo de Respuesta

```json
{
  "success": true,
  "wallets": [
    {
      "name": "candidato1",
      "display_name": "Candidato A",
      "wallet_type": "candidato",
      "balance": 234000,
      "vote_info": {
        "votos": 2340,
        "sats": 234000,
        "sats_remainder": 0
      },
      "is_available": true,
      "last_update": "2024-01-02T14:30:45.123456"
    },
    {
      "name": "mesa0",
      "display_name": "Mesa Electoral 0",
      "wallet_type": "mesa",
      "balance": 12550,
      "vote_info": {
        "votos": 125,
        "sats": 12550,
        "sats_remainder": 50
      },
      "is_available": true,
      "last_update": "2024-01-02T14:30:45.654321"
    }
  ]
}
```

---

## 🎯 Casos de Uso

### Caso 1: 3 Candidatos + 1 Mesa (Default)
```bash
# Ya viene preconfigurado en wallets.example.json
cp wallets.example.json wallets.json
nano wallets.json  # Reemplazar keys
```

### Caso 2: 10 Candidatos + 5 Mesas
```bash
# 1. Copiar y editar wallets.json
cp wallets.example.json wallets.json

# 2. Agregar los 7 candidatos y 4 mesas faltantes en JSON
nano wallets.json

# 3. Ejecutar (sin cambios en código)
python lnbits_dashboard.py
```

### Caso 3: 50 Candidatos + 20 Mesas (Elecciones Nacionales)
```bash
# El código se maneja igual, solo edita wallets.json
# Dashboard se adapta automáticamente al número de elementos
```

---

## 🎨 Dashboard Features

### Candidatos vs Mesas

#### Candidatos (👥)
- **Muestra**: Total de votos completados
- **Ejemplo**: "2340 VOTOS"
- **Secundario**: "(234,000 sats)"

#### Mesas (🏛️)
- **Muestra**: Total de votos remanentes
- **Ejemplo**: "125 VOTOS REMANENTES"
- **Nota**: Muestra sats que no completan un voto
- **Secundario**: "(50 sats sin completar voto)"

### Conversión de Sats a Votos

```
SATS_PER_VOTE = 100

Candidato A: 234,000 sats = 2,340 votos
Mesa 0:      12,550 sats = 125 votos + 50 sats remanentes

Redondeo: Hacia abajo (floor division)
99 sats = 0 votos (99 sats remanentes)
```

---

## 🔐 Seguridad

### Invoice Keys (Seguras ✅)
```
❌ NO pueden:
  - Crear invoices
  - Pagar invoices
  - Modificar configuración
  - Eliminar datos

✅ SI pueden:
  - Ver balance
  - Ver historial de pagos
  - Decodificar invoices
  - Verificar estado de pagos

➡️ Seguro para usar públicamente
```

### Admin Keys (Peligrosas ❌)
```
❌ NUNCA uses Admin Keys en este proyecto
❌ Tienen control total
❌ Pueden pagar desde la wallet
❌ Pueden eliminar datos
```

---

## 🔄 Actualización Automática

```javascript
// El dashboard se actualiza automáticamente cada 30 segundos
setInterval(loadWalletStatus, 30000);

// Para cambiar intervalo, editar en HTML_TEMPLATE
// Opciones: 5000 (5s), 10000 (10s), 30000 (30s), 60000 (60s)
```

---

## 🐛 Troubleshooting

### Error: "wallets.json no encontrado"
```bash
cp wallets.example.json wallets.json
# Editar con tus Invoice Keys
```

### Error: "JSON inválido en wallets.json"
```bash
# Validar JSON
python -m json.tool wallets.json

# O usar herramienta online: https://jsonlint.com/
```

### Error: "Wallet offline"
```bash
# Verificar:
1. LNBITS_ENDPOINT es correcto
2. LNBits está ejecutándose
3. Invoice Key es correcta
4. Conexión a red funciona

# Test:
curl http://localhost:5000/health
```

### Dashboard en blanco
```bash
# Abre la consola (F12) y busca errores
# Verifica los logs de Flask en terminal
# Asegúrate que las wallets.json es JSON válido
```

### Cambios en wallets.json no se aplican
```bash
# El archivo se carga al iniciar el script
# Requiere reiniciar:
python lnbits_dashboard.py

# (No es necesario restart automático - versión 3.0)
```

---

## 📊 Monitoreo en Tiempo Real

### Terminal 1: Ejecutar Dashboard
```bash
python lnbits_dashboard.py
```

### Terminal 2: Ver cambios en vivo
```bash
watch -n 5 'curl -s http://localhost:5000/api/wallets/status | jq ".wallets[] | {name, votos: .vote_info.votos}"'
```

### Terminal 3: Monitorear logs
```bash
tail -f ~/.lnbits/logs  # O donde estén tus logs de LNBits
```

---

## 📚 Estructura de Directorios

```
proyecto/
├── lnbits_dashboard.py      # Aplicación principal (v3.0)
├── setup.py                 # Setup interactivo
├── requirements.txt         # Dependencias
├── .env.example             # Configuración (nueva versión)
├── wallets.example.json     # NUEVO: Ejemplo de wallets
├── wallets.json             # Tu configuración (a crear)
├── .env                     # Tu configuración (a crear)
├── README.md                # Documentación completa
├── TECHNICAL.md             # Guía técnica
├── CHANGELOG.md             # Historial de cambios
└── QUICKSTART.md            # Este archivo
```

---

## ✅ Checklist de Setup v3.0

- [ ] Python 3.8+ instalado
- [ ] `pip install -r requirements.txt` ejecutado
- [ ] `.env.example` revisado
- [ ] `wallets.example.json` revisado
- [ ] `.env` creado desde `.env.example`
- [ ] `wallets.json` creado desde `wallets.example.json`
- [ ] Invoice Keys obtenidas de LNBits
- [ ] Invoice Keys pegadas en `wallets.json`
- [ ] LNBits está corriendo en `LNBITS_ENDPOINT`
- [ ] `python lnbits_dashboard.py` ejecutado sin errores
- [ ] Dashboard accesible en `http://localhost:5000`
- [ ] Candidatos muestran votos correctamente
- [ ] Mesas muestran votos remanentes correctamente
- [ ] Pestañas de filtro funcionan (Todos/Candidatos/Mesas)
- [ ] Actualización automática funciona cada 30 segundos

---

## 💡 Tips Avanzados

### Cambiar tasa de conversión
```env
# 50 sats por voto (más sensible)
SATS_PER_VOTE=50

# 1000 sats por voto (menos sensible)
SATS_PER_VOTE=1000
```

### Ocultar sats en la interfaz
```env
# Solo mostrar votos, no sats
SHOW_SATS_AND_VOTES=false
```

### Diferentes puertos
```bash
export FLASK_PORT=8000
python lnbits_dashboard.py
# Accede a http://localhost:8000
```

### Ejecutar en modo debug
```bash
FLASK_DEBUG=True python lnbits_dashboard.py
```

---

## 🚀 Próximas Mejoras Planificadas (v4.0)

- [ ] Gráficos de tendencias en tiempo real
- [ ] Base de datos SQLite para histórico
- [ ] Alertas por cambios grandes
- [ ] WebSockets para actualización instantánea
- [ ] Autenticación opcional por contraseña
- [ ] Exportar resultados (CSV, PDF)
- [ ] Dark mode
- [ ] Soporte múltiples idiomas

---

**Versión:** 3.0
**Última actualización:** 2024-01-02
**Modo:** 🔒 Read-Only (Invoice Keys)
**Escalabilidad:** ✅ Ilimitada (sin cambios de código)
