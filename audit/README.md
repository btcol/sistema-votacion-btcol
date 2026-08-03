# ⚖️ Dashboard Interactivo de Auditoría Criptográfica (Puerto 7070)
### *Módulo de Verificación Matemática 1:1 y Detección de Irregularidades Electorales*

---

## 📖 Descripción General

El **Dashboard de Auditoría Electoral BTCOL** (`audit/auditoria_ln_votos.py`) es la herramienta especializada para observadores electorales, auditores informáticos y delegados de los partidos políticos.

Permite auditar de forma exhaustiva, matemática e independiente cada voto liquidado en la red Lightning contra la base de datos o el libro contable de LNbits.

---

## 🎯 Capacidades Principales

1. **Reconciliación Matemática 1:1**: Comprueba la integridad de cada pago, validando montos en sats, fecha/hora y memos HMAC-SHA256.
2. **🚨 Detección Criptográfica de Votos No Autorizados**: Identifica e informa inmediatamente si alguna wallet o fuente desconocida intentó inyectar pagos hacia los candidatos sin pertenecer al padrón oficial de mesas electorales (`data/wallets.json.enc`).
3. **Matriz Electoral Origen ➔ Destino**: Muestra una tabla cruzada bidimensional que contabiliza cuántos votos exactos transfirió cada mesa a cada candidato.
4. **Exportación de Reportes**: Permite descargar la bitácora completa de auditoría para archivo judicial o electoral.

---

## 🚀 Guía de Ejecución

El script consume directamente la configuración cifrada `data/wallets.json.enc` y descifra las identidades de las carteras en RAM.

```bash
# 1. Pasando la clave Fernet por línea de comandos (Recomendado)
python3 audit/auditoria_ln_votos.py --fernet-key "TU_CLAVE_FERNET_BASE64="

# 2. O mediante variable de entorno
export FERNET_KEY="TU_CLAVE_FERNET_BASE64="
python3 audit/auditoria_ln_votos.py
```

*Acceso en navegador:* `http://localhost:7070`

---

## ⚙️ Opciones de Línea de Comandos

| Argumento | Tipo | Por Defecto | Descripción |
|---|---|---|---|
| `--fernet-key` | String Base64 | `None` (Usa const) | Clave de descifrado Fernet para `data/wallets.json.enc`. |
| `--port` | Entero | `7070` | Puerto HTTP para el servidor web de auditoría. |
| `--host` | String | `0.0.0.0` | Interfaz de escucha de red. |
