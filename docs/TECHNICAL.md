# Sistema de Votación BTCOL - Guía Técnica de Arquitectura (LNbits + Tor)

## 🏗️ Arquitectura General del Sistema

El sistema de votación está diseñado como una plataforma distribuida de alta disponibilidad basada en **Bitcoin Lightning Network**, **LNbits API** y cifrado de red **Tor (.onion)**.

```
┌─────────────────────────────────────────────────────────────┐
│             Urna Electoral Web (Puerto 2007)                │
│               [mesa_code/app_web_mesa.py]                   │
│ (Emite Votos Lightning usando Admin Key de la Mesa vía Tor) │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP POST / Invoices vía SOCKS5h Tor (9050)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Instancia LNbits (Red Tor)                  │
│       (Procesa y valida transacciones de Satoshis)          │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               │ Consultas Read-Only          │ Consultas Read-Only
               │ (Invoice Keys)               │ (Invoice Keys)
               ▼                              ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│    Dashboard Monitoreo       │ │    Dashboard Auditoría       │
│      (Puerto 5050)           │ │      (Puerto 7070)           │
│[frontend/votos_dashboard.py] │ │ [audit/auditoria_ln_votos.py]│
└──────────────────────────────┘ └──────────────────────────────┘
```

---

## 🔑 Diferencia entre Keys de LNbits

### Admin Key (`mesa_code/data_mesa/mesa_config.json`)
- **Uso exclusivo**: Urna Electoral (`mesa_code/app_web_mesa.py`).
- **Permisos**: Crear invoices, pagar invoices, transferir sats a la wallet del candidato seleccionado.
- **Seguridad**: Altamente sensible. Nunca debe compartirse ni subirse a repositorios Git.

### Invoice Key (`data/wallets.json` & `candidatos.json`)
- **Uso**: Dashboards de Monitoreo (`frontend/votos_dashboard.py`), Auditoría (`audit/auditoria_ln_votos.py`) y recepción de pagos.
- **Permisos**: Ver balance y consultar historial de pagos. NO permite retirar ni gastar fondos.
- **Seguridad**: Seguro para uso en servicios web de consulta pública.

---

## 🧅 Conectividad Tor Nactiva (SOCKS5h)

Todas las peticiones HTTP enviadas a dominios `.onion` se enrutan automáticamente mediante el proxy Tor local:
- Proxy: `socks5h://127.0.0.1:9050`
- Reintentos automáticos y timeout extendido (15s–25s) para manejar la latencia de los circuitos `.onion`.

---

## 📊 Endpoints de la API

### Urna Electoral Web (`http://localhost:2007`)
- `GET /` -> Interfaz Web Táctil de votación.
- `GET /api/candidatos` -> Lista de candidatos disponibles.
- `GET /api/status` -> Estado de conectividad y votos remanentes (saldo // 100).
- `POST /api/votar` -> Registra deduplicación en SQLite local y ejecuta el pago Lightning al candidato.

### Dashboard de Monitoreo (`http://localhost:5050`)
- `GET /` -> Dashboard en tiempo real con pestañas de filtro (Todos, Candidatos, Mesas).
- `GET /api/wallets/status` -> Retorna saldo y votos de todos los candidatos y mesas.
- `GET /api/candidatos/status` -> Solo candidatos.
- `GET /api/mesas/status` -> Solo mesas.
- `GET /health` -> Health check.

### Dashboard de Auditoría (`http://localhost:7070`)
- `GET /` -> Dashboard interactivo con alertas de seguridad, matriz Origen ➔ Destino y tablas filtrables.
- `GET /api/audit/data` -> Datos consolidados de auditoría y detección de irregularidades.
