# 📝 Sistema de Votación BTCOL (LNbits + Tor) 🚀

Sistema integral, transparente, auditable y de alta disponibilidad para **votaciones electrónicas democráticas** basado en la red **Bitcoin Lightning Network**, **LNbits** y enrutamiento anónimo **Tor (.onion)**.

El sistema permite realizar elecciones electrónicas en las cuales cada voto se emite mediante una transacción Lightning Network desde la wallet de una **Mesa Electoral** hacia la wallet del **Candidato** seleccionado, registrando un memo criptográfico inalterable. 

Incluye una **Urna Electoral BTCOL**, un **Dashboard de Monitoreo BTCOL en Tiempo Real** y un **Dashboard Web Interactivo de Auditoría Electoral BTCOL** con detección de irregularidades.

---

## 📸 Capturas de Pantalla de la Plataforma

> [!NOTE]
> *Reemplazar las rutas de las imágenes en `docs/assets/` con las capturas de pantalla del despliegue real.*

### 1. Urna Electoral BTCOL (Puerto 2007)
![Urna Electoral BTCOL](docs/assets/urna_web_screenshot.png)

### 2. Dashboards Web de Monitoreo en Tiempo Real (Puerto 5050)

**Vista Principal: Escrutinio de Candidatos**
![Dashboard Candidatos](docs/assets/votos_dashboard_candidatos.png)

**Vista Secundaria: Estatus y Saldo de Mesas Electorales**
![Dashboard Mesas](docs/assets/votos_dashboard_mesas.png)

### 3. Dashboard Interactivo de Auditoría Electoral BTCOL (Puerto 7070)
![Dashboard de Auditoría Criptográfica](docs/assets/audit_dashboard_screenshot.png)

---

## 🎯 Funcionalidades y Capacidades Avanzadas

### 🧅 1. Conectividad Nativa Cifrada vía Red Anónima Tor (.onion)
- Todas las peticiones HTTP y WebSockets hacia la API de LNbits se enrutan de forma cifrada a través del proxy **Tor SOCKS5h (`socks5h://127.0.0.1:9050`)**.
- Garantiza la privacidad y el anonimato de las comunicaciones entre las Mesas Electorales, los Dashboards y el nodo Lightning, protegiendo contra censura o ataques dirigidos (DDoS).
- Incorpora mecanismos de **reintento automático y timeout extendido (25s)** ante fluctuaciones o reconstrucción de circuitos `.onion`.

### 🛡️ 2. Límite de Capacidad Dinámico e Inmanipulable por Saldo Real
- La capacidad autorizada de votos de cada Mesa Electoral se calcula matemáticamente en tiempo real en función del saldo en satoshis de su wallet LNbits:
  `Votos Disponibles = Saldo Actual de Wallet Mesa (Sats) / Monto por Voto`
- **Imposible de manipular localmente**: No existen valores enteros estáticos en archivos de configuración locales.
- **Bloqueo en Backend**: Si la wallet se queda sin saldo (`votos_disponibles < 1`), la Urna Electoral rechaza la solicitud de voto con HTTP 403 antes de registrarla en la base de datos local SQLite.
- **Indicador en Vivo & Banner de Cierre**: La interfaz de la mesa muestra un indicador en vivo con los votos restantes y bloquea automáticamente la pantalla táctil cuando la capacidad se agota.

### 👥 3. Dashboards de Monitoreo de Alto Rendimiento (Arquitectura WebSockets + RAM)
- **Sincronización en Tiempo Real**: El dashboard de monitoreo mantiene hilos en segundo plano suscritos a los WebSockets de LNbits.
- **Escalabilidad y Cero Costo de Red**: Las consultas de la interfaz gráfica no impactan a la red Tor. El backend en Python mantiene el estado en la memoria RAM, logrando tiempos de respuesta inferiores a 1 milisegundo y soportando miles de usuarios concurrentes.
- **Resiliencia de Conteos**: Implementación de sincronización HTTP híbrida de respaldo y caché (`last_known_status`) para mantener fijos y estables los votos ante fluctuaciones de la red Tor.

### ⚖️ 4. Dashboard Web Interactivo de Auditoría (`audit/auditoria_ln_votos.py` - Puerto 7070)
- **Navegación por Pestañas**:
  - **`📊 Resumen & Gráficos`**: Vista ejecutiva con tarjetas KPI, alertas de seguridad, matriz Origen ➔ Destino y gráficos interactivos.
  - **`📜 Registro General de Transacciones`**: Listado exhaustivo de todas las transacciones auditadas.
- **🚨 Detección Criptográfica de Votos Irregulares**: Identifica y aísla automáticamente cualquier voto o transacción acreditada a un candidato que provenga de una fuente o `wallet_id` **no registrada en `data/wallets.json`**.
- **Matriz Electoral Origen ➔ Destino**: Tabla cruzada que demuestra de forma transparente cuántos votos envió cada Mesa Electoral a cada Candidato.

### 🚀 5. Arquitectura Escalable e Impulsada por Datos (Data-Driven)
- El sistema escala de forma dinámica: para agregar nuevas Mesas o Candidatos, únicamente se deben registrar en el archivo centralizado `data/wallets.json`.
- Los módulos de la plataforma detectan e integran las nuevas carteras automáticamente sin requerir alteraciones en el código fuente.

---

## 🔒 Archivos Sensibles a Proteger (No Subir al Repositorio)

Por motivos de seguridad criptográfica, las claves privadas y las bases de datos locales **NUNCA deben subirse a repositorios públicos de Git**. El archivo `.gitignore` protege automáticamente:

| Archivo / Directorio | Descripción / Razón de Protección |
|----------------------|-----------------------------------|
| `data/wallets.json` | Contiene las **Invoice Keys** e IDs reales de todas las wallets de candidatos y mesas. |
| `mesa_code/data_mesa/mesa_config.json` | Contiene la **Admin Key** de la wallet de la Mesa Electoral (permiso de pago). |
| `mesa_code/data_mesa/candidatos.json` | Contiene las Invoice Keys reales de las wallets de candidatos. |
| `data/database.sqlite3` | Base de datos SQLite interna de la instancia LNbits (si aplica). |
| `mesa_code/data_mesa/votos_local.db` | Base de datos SQLite local de la Mesa Electoral. |
| `logs/`, `*.log` | Archivos de registros del sistema. |

> [!CAUTION]
> Asegurarse de utilizar únicamente archivos de plantilla como `wallets.example.json` para publicar en repositorios de control de versiones.

---

## 🏗️ Arquitectura General del Sistema

```
                                  ┌──────────────────────────────────────────┐
                                  │    Urna Electoral Web (Puerto 2007)      │
                                  │      [mesa_code/app_web_mesa.py]         │
                                  └────────────────────┬─────────────────────┘
                                                       │ 
                                                       │ Transacción Lightning por Tor (Sats + Memo Cifrado)
                                                       ▼
┌──────────────────────────────────────────┐       ┌──────────────────────────────────────────┐
│   Dashboard Interactivo de Auditoría    │◄──────┤        Nodo LNbits (Red Tor .onion)      │
│   (Puerto 7070)                          │       └────────────────────┬─────────────────────┘
│   [audit/auditoria_ln_votos.py]          │                            │
└──────────────────────────────────────────┘                            │ WebSockets en Tiempo Real
                                                                        ▼
                                                  ┌──────────────────────────────────────────┐
                                                  │       Dashboard Web (Puerto 5050)        │
                                                  │      [frontend/votos_dashboard.py]       │
                                                  └──────────────────────────────────────────┘
```

---

## 🚀 Guía de Inicio Rápido e Implementación

### 1. Requisitos Previos
- Python 3.8+
- Servicio proxy Tor activo en local (`127.0.0.1:9050`) para operaciones con nodos `.onion`.
- Nodo o instancia LNbits operativa.

### 2. Instalación
```bash
git clone <URL_DEL_REPOSITORIO>
cd sistema-votacion-btcol
bash setup.sh
```

### 3. Configuración de Credenciales LNbits

#### A. Configurar Wallets Globales (`data/wallets.json`)
Copiar la plantilla `wallets.example.json` a `data/wallets.json` e ingresar las **Invoice Keys** (solo lectura) correspondientes:
```bash
cp wallets.example.json data/wallets.json
nano data/wallets.json
```

#### B. Configurar la Urna de Mesa (`mesa_code/data_mesa/mesa_config.json`)
Configurar la **Admin Key** de la wallet asignada a la mesa (necesaria para emitir los pagos):
```bash
nano mesa_code/data_mesa/mesa_config.json
```

---

### 4. Ejecución de Componentes

#### 🖥️ A. Urna Electoral Web de Mesa (Puerto 2007)
```bash
python mesa_code/app_web_mesa.py
```
*Acceso en navegador:* `http://localhost:2007`

#### 🌐 B. Dashboard Web de Monitoreo en Tiempo Real (Puerto 5050)
```bash
python frontend/votos_dashboard.py
```
*Acceso en navegador:* `http://localhost:5050`

#### ⚖️ C. Dashboard Interactivo de Auditoría Electoral (Puerto 7070)
```bash
python audit/auditoria_ln_votos.py
```
*Acceso en navegador:* `http://localhost:7070`

#### 🔓 D. Desencriptación en Lote de Cédulas Capturadas
Para el escrutinio biométrico post-elección, el sistema puede desencriptar todas las fotos capturadas automáticamente. Las claves simétricas son los propios Hashes LNbits generados por la red durante los pagos.
```bash
./desencriptador/desencriptar_lote.sh
```
Las imágenes resultantes se guardarán en `desencriptador/cedulas_desencriptadas/`.

---

### 5. ¿Cómo usar la captura de cédulas web?
1. Abrir la Urna Electoral Web (`http://localhost:2007`).
2. Seleccionar la tarjeta del candidato a elegir.
3. Se habilitará el permiso de cámara en el navegador. Centrar el documento de identidad en el recuadro amarillo en pantalla.
4. Presionar la **Barra Espaciadora** o hacer clic en el botón de la cámara para capturar la imagen.
5. Confirmar el voto. El sistema cifrará la imagen instantáneamente utilizando como llave criptográfica el Hash generado en LNbits por la transacción del voto. Finalmente, se genera el comprobante digital (ticket con código QR).
6. Los archivos `.enc` permanecerán seguros y encriptados en `mesa_code/impresora/capturas_cedula/`.

---

## 📄 Licencia

Software libre y de código abierto. Desarrollado para robustecer la transparencia institucional mediante **Bitcoin Lightning Network**.
