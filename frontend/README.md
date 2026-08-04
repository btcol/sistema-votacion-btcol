# 📊 Dashboard de Monitoreo Electoral en Tiempo Real (Puerto 5050)
### *Visualización y Escrutinio Instantáneo sobre Bitcoin Lightning Network*

---

## 📖 Descripción General

El **Dashboard de Monitoreo BTCOL** (`frontend/votos_dashboard.py`) es una aplicación web interactiva de alto rendimiento desarrollada en Flask que proporciona a los administradores electorales y veedores:

- **Escrutinio en Vivo de Candidatos**: Porcentaje de votos, total de satoshis acumulados y estado de la elección.
- **Monitoreo de Mesas Electorales**: Estado de conectividad, saldo restante en satoshis y votos disponibles por mesa.
- **Arquitectura de Cero Costo de Red**: Mantiene conexiones WebSocket persistentes en segundo plano hacia LNbits y sirve las consultas de los usuarios directamente desde la memoria RAM (< 1ms de latencia).

---

## 🛡️ Seguridad y Cifrado

El dashboard consume la configuración global cifrada en **`data/wallets.json.enc`** generada por el orquestador por lotes. 

Para arrancar el dashboard de forma segura, se puede proporcionar la clave Fernet autorizada mediante cualquiera de las siguientes opciones:

```bash
# 1. Automático (Lee clave_fernet desde generador_configuracion_lote/config_global.md)
python3 frontend/votos_dashboard.py

# 2. Pasando la clave por argumento CLI
python3 frontend/votos_dashboard.py --fernet-key "TU_CLAVE_FERNET_BASE64="

# 3. Mediante variable de entorno
export FERNET_KEY="TU_CLAVE_FERNET_BASE64="
python3 frontend/votos_dashboard.py
```

*Acceso en navegador:* `http://localhost:5050`

---

## ⚙️ Opciones de Línea de Comandos

| Argumento | Tipo | Por Defecto | Descripción |
|---|---|---|---|
| `--fernet-key` | String Base64 | `None` (Usa const) | Clave de descifrado Fernet para `data/wallets.json.enc`. |
| `--port` | Entero | `5050` | Puerto HTTP para el servidor web. |
| `--host` | String | `0.0.0.0` | Interfaz de escucha de red. |
