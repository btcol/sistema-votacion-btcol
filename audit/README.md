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
# 1. Automático (Lee clave_fernet desde generador_configuracion_lote/config_global.md)
python3 audit/auditoria_ln_votos.py

# 2. Pasando la clave Fernet por línea de comandos
python3 audit/auditoria_ln_votos.py --fernet-key "TU_CLAVE_FERNET_BASE64="

# 3. O mediante variable de entorno
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

---

## 🔍 Herramienta Forense de Comprobantes PDF (`auditar_comprobantes_pdf.py`)

Adicionalmente, el módulo de auditoría incluye el script CLI especializado para peritajes informáticos de comprobantes de voto emitidos en PDF:

```bash
# 1. Auditar un comprobante individual
python3 audit/auditar_comprobantes_pdf.py --archivo mesa_code/impresora/comprobantes_emitidos/comprobante_ejemplo.pdf

# 2. Auditoría masiva de toda una mesa o directorio
python3 audit/auditar_comprobantes_pdf.py --dir mesa_code/impresora/comprobantes_emitidos

# 3. Exportar resultados consolidados a CSV y JSON
python3 audit/auditar_comprobantes_pdf.py --dir . --export-csv audit/reporte_forense.csv --export-json audit/reporte_forense.json
```

### Validaciones Realizadas:
* Extracción de metadatos nativos PDF (`/Info` Dictionary).
* Trazabilidad de máquina: Hostname, SO, Versión de Kernel, Arquitectura y Runtime Python.
* Validación matemática del **Sello de Integridad HMAC-SHA256**.
* Reconciliación con el Checksum SHA-256 de la cédula encriptada y el Payment Hash Lightning.

