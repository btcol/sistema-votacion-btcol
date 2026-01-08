# CHANGELOG - LNBits Dashboard Sistema de Votación

## v3.0 - Sistema Escalable de Votación (2024-01-02)

### 🚀 Cambios Principales - ARQUITECTURA COMPLETAMENTE RENOVADA

#### 1. ✨ Sistema de Votación con Conversión de Sats
- ✅ **Candidatos**: Muestran total de votos completados
  - Ejemplo: "2340 VOTOS" (234,000 sats con SATS_PER_VOTE=100)
  - Secundario: "(234,000 sats)" si SHOW_SATS_AND_VOTES=true

- ✅ **Mesas Electorales**: Muestran votos remanentes
  - Ejemplo: "125 VOTOS REMANENTES" (12,550 sats)
  - Muestra: "(50 sats sin completar voto)"
  - Redondeo hacia abajo (floor division)

- ✅ **Configuración Escalable**
  - `SATS_PER_VOTE` en `.env` (default: 100)
  - `SHOW_SATS_AND_VOTES` en `.env` (default: true)

#### 2. 🔄 Arquitectura Escalable - Wallets desde JSON
- ✅ **Archivo `wallets.json` (NUEVO)**
  - Reemplaza hardcoding en `.env`
  - Estructura clara y legible
  - Soporta unlimited candidatos y mesas
  - No requiere cambios de código

```json
{
  "candidatos": {
    "candidato1": {
      "invoice_key": "key1",
      "display_name": "Candidato A"
    }
  },
  "mesas": {
    "mesa0": {
      "invoice_key": "key0",
      "display_name": "Mesa Electoral 0"
    }
  }
}
```

- ✅ **Carga Dinámica**
  - Detecta automáticamente # de candidatos y mesas
  - Soporta 10, 100, 1000+ wallets sin cambios código
  - Inicio del script muestra resumen

#### 3. 🎨 UI Mejorada con Pestañas de Filtro
- ✅ **Pestañas dinámicas**:
  - 📊 Todos (candidatos + mesas)
  - 👥 Candidatos (solo candidatos)
  - 🏛️ Mesas (solo mesas)

- ✅ **Diseño Responsivo**
  - Funciona perfectamente en móvil, tablet, desktop
  - Gradientes modernos y animaciones
  - Iconos diferenciadores para candidatos y mesas
  - Cards con estado online/offline visual

#### 4. 📡 Nuevos Endpoints API
```
GET /api/candidatos/status    → Solo candidatos
GET /api/mesas/status         → Solo mesas
GET /api/config               → Configuración de conversión
(Anteriores mantienen compatibilidad)
```

#### 5. 🔧 Mejoras Técnicas

**Clases y Modelos:**
```python
# NUEVA: VoteConverter
class VoteConverter:
    def convert(sats: int) -> VoteInfo  # Redondeo hacia abajo

# NUEVA: WalletType Enum
class WalletType(Enum):
    CANDIDATO = "candidato"
    MESA = "mesa"

# REFACTORIZADO: WalletMonitor
class WalletMonitor:
    def get_candidatos_status() -> List[WalletDetails]
    def get_mesas_status() -> List[WalletDetails]
    def get_all_wallets_status() -> List[WalletDetails]
```

**Funciones de Carga:**
```python
def load_wallets_config() -> Dict:
    # Carga desde wallets.json con validación
    # Soporte para unlimited candidatos/mesas
    # Error handling claro
```

---

## v2.1.0 - Mejor Carga de Entorno (2024-01-02)

### ✨ Mejoras

#### Soporte automático para .env
- ✅ Carga variables desde archivo `.env` automáticamente
- ✅ Usa `python-dotenv` si está instalado
- ✅ Fallback graceful si no está disponible

#### Mejor carga de configuración
- Prioridad: `.env` → Variables del sistema → Valores por defecto
- Mensaje claro en consola sobre cómo se cargan las variables
- Mejores instrucciones en el startup

### 📝 Cambios en lnbits_dashboard.py
```python
# NUEVO: Al inicio del archivo
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables del sistema.")

# Ahora las variables se cargan automáticamente desde .env si existe
LNBITS_ENDPOINT = os.getenv("LNBITS_ENDPOINT", "http://localhost:5000")
```

---

## v2.0.0 - Read-Only Release (2024-01-02)

### 🔒 Cambios Principales

#### Seguridad
- ✅ **Cambio de Admin Key a Invoice Key**
  - Antes: Usaba Admin Keys (permisos totales)
  - Ahora: Usa solo Invoice Keys (read-only)
  - Beneficio: Máxima seguridad

- ✅ **Modo Read-Only Puro**
  - Solo operaciones GET
  - Sin POST/PUT/DELETE
  - Sin estado mutante

#### Funcionalidad Removida
- ❌ `POST /api/wallets/invoice` - Crear invoices
- ❌ Botón "Crear Invoice" en dashboard
- ❌ `client.create_invoice()` método
- ❌ `client.pay_invoice()` método
- ❌ Admin Key en configuración

#### Funcionalidad Mantenida
- ✅ `GET /api/wallets/status` - Ver estado
- ✅ `GET /api/wallets/<name>/status` - Wallet específica
- ✅ `GET /api/wallets/<name>/payments` - Historial
- ✅ Dashboard web con visualización completa
- ✅ Actualización automática cada 30 segundos
- ✅ API RESTful read-only

---

## v1.0.0 - Initial Release

### Características Iniciales
- Dashboard en Python/Flask
- Monitoreo de 3 wallets
- API RESTful completa
- Admin Keys
- Crear/Pagar invoices

---

## 📊 Comparativa de Versiones

| Aspecto | v1.0 | v2.0 | v2.1 | v3.0 |
|---------|------|------|------|------|
| **Modo** | Full | Read-Only | Read-Only | Read-Only |
| **Escalabilidad** | Hardcoded | Hardcoded | Hardcoded | ✅ JSON |
| **# Candidatos** | 3 fijo | 3 fijo | 3 fijo | ✅ Unlimited |
| **# Mesas** | 1 fijo | 1 fijo | 1 fijo | ✅ Unlimited |
| **Votos** | ❌ No | ❌ No | ❌ No | ✅ Sí |
| **Pestañas** | ❌ No | ❌ No | ❌ No | ✅ Sí |
| **Conversión Sats** | ❌ No | ❌ No | ❌ No | ✅ Configurable |
| **Wallets JSON** | ❌ No | ❌ No | ❌ No | ✅ Sí |
| **Votos Remanentes** | ❌ No | ❌ No | ❌ No | ✅ Mesas |

---

## 🔄 Guía de Migración

### De v2.1.0 a v3.0

#### 1. Descargar nuevos archivos
- `lnbits_dashboard.py` (completamente reescrito)
- `.env.example` (actualizado)
- `wallets.example.json` (NUEVO)
- `QUICKSTART.md` (actualizado)
- `CHANGELOG.md` (este archivo)

#### 2. Crear wallets.json
```bash
cp wallets.example.json wallets.json
nano wallets.json
# Editar con tus Invoice Keys
```

#### 3. Actualizar .env
```bash
# Opcional: actualizar desde .env.example
# Mínimo: agregar estas líneas si no las tienes:
WALLETS_CONFIG_FILE=wallets.json
SATS_PER_VOTE=100
SHOW_SATS_AND_VOTES=true
```

#### 4. Ejecutar
```bash
python lnbits_dashboard.py
```

---

## ✅ Testing Checklist v3.0

- [x] Dashboard carga sin errores
- [x] Muestra candidatos y mesas correctamente
- [x] Pestañas de filtro funcionan (Todos/Candidatos/Mesas)
- [x] Candidatos muestran votos completados
- [x] Mesas muestran votos remanentes
- [x] Redondeo hacia abajo funciona (floor division)
- [x] Cargar desde wallets.json dinámicamente
- [x] Soporta 10+ candidatos sin problemas
- [x] Soporta 5+ mesas sin problemas
- [x] API endpoints read-only funcionan
- [x] Historial de pagos se muestra
- [x] Actualización automática cada 30 segundos
- [x] Diseño responsivo (móvil/tablet/desktop)
- [x] Invoice Keys funcionan correctamente
- [x] Admin Keys no funcionan (401)

---

## 🐛 Bugs Conocidos

### v3.0
- Ninguno reportado

### v2.1.0
- Ninguno reportado

---

## 📚 Archivos de Documentación

| Archivo | Propósito |
|---------|-----------|
| `README.md` | Documentación completa y guía de uso |
| `TECHNICAL.md` | Detalles técnicos y ejemplos avanzados |
| `QUICKSTART.md` | Referencia rápida de inicio |
| `CHANGELOG.md` | Este archivo - historial de cambios |
| `.env.example` | Variables de entorno documentadas |
| `wallets.example.json` | Ejemplo de configuración de wallets |

---

## 🔐 Notas de Seguridad

### v3.0 - Recomendaciones
1. **Invoice Keys son seguras públicamente**
   - Solo lectura
   - No pueden pagar
   - No pueden crear invoices
   - No pueden modificar

2. **Guardar archivos en .gitignore**
   ```
   .env
   .env.local
   wallets.json
   *.env
   ```

3. **Rota las keys regularmente**
   - Genera nuevas Invoice Keys en LNBits
   - Actualiza wallets.json
   - Las antiguas dejan de funcionar instantáneamente

4. **Usa HTTPS en producción**
   - No expongas dashboard en HTTP público
   - Usa certificados SSL/TLS válidos
   - Considera firewall/IP whitelist

---

## 📈 Roadmap Futuro (v4.0+)

### Planificado
- [ ] Gráficos de tendencias en tiempo real
- [ ] Base de datos SQLite para histórico
- [ ] Alertas por cambios grandes (ej: +1000 votos)
- [ ] WebSockets para actualización instantánea
- [ ] Autenticación opcional por contraseña
- [ ] Exportar resultados (CSV, PDF, JSON)
- [ ] Dark mode / Light mode selector
- [ ] Soporte múltiples idiomas
- [ ] Integración con sistemas de conteo externo
- [ ] API de webhooks para notificaciones
- [ ] Estadísticas y reportes avanzados
- [ ] Soporte para múltiples nodos de LNBits

---

**Versión Actual:** 3.0
**Última Actualización:** 2024-01-02
**Modo:** 🔒 Read-Only (Invoice Keys)
**Escalabilidad:** ✅ Ilimitada (sin cambios de código)
**Python:** 3.8+
**Dependencies:** Flask, requests, python-dotenv, flask-cors
