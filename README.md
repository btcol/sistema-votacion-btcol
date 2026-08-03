# 🗳️ Sistema de Votación Electrónica Criptográfica BTCOL
### *Bitcoin Lightning Network + Tor Onion Routing + Blindaje Anti-Manipulación Zero-Trust*

---

## 🌟 Visión General

El **Sistema de Votación BTCOL** es una plataforma integral, auditable en tiempo real y de alta disponibilidad para **elecciones democráticas electrónicas** construida sobre la red **Bitcoin Lightning Network**, **LNbits** y enrutamiento anónimo **Tor (`.onion`)**.

Cada voto emitido en una terminal física o virtual se procesa mediante una **micro-transacción Lightning Network** real desde la wallet autorizada de la **Mesa Electoral** hacia la wallet del **Candidato** seleccionado. Dicha transacción incorpora un memo criptográfico sellado con HMAC-SHA256 y se complementa con la captura biométrica del documento de identidad cifrado al vuelo, garantizando una **trazabilidad matemática inmutable**.

---

## 🛡️ Arquitectura de Seguridad: Blindaje Anti-Manipulación de Terminales

Esta versión incorpora un modelo de seguridad **Cero Confianza (Zero-Trust)** diseñado específicamente para mitigar ataques físicos o lógicos en las terminales de votación (urnas / Raspberry Pi):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        MODELO DE SEGURIDAD Y BLINDAJE ELECTORAL                                 │
├────────────────────────────────┬───────────────────────────────┬────────────────────────────────┤
│    🔒 Cifrado en Reposo        │    🛡️ Ofuscación Binaria       │    🧠 Descifrado en RAM        │
│   (Fernet AES-128-CBC)         │         (PyArmor)             │       (Cero Huella)            │
│ Archivos de configuración      │ Todo el código Python de las  │ Las Admin Keys y datos se      │
│ sensibles se almacenan como    │ mesas desplegadas se ofusca,  │ descifran exclusivamente en    │
│ .json.enc. No existen claves   │ protegiendo la clave Fernet   │ RAM al iniciar el proceso; no  │
│ en texto plano en disco.       │ empotrada contra desensamblado│ quedan residuos en disco.      │
└────────────────────────────────┴───────────────────────────────┴────────────────────────────────┘
```

### 1. 🔒 Cifrado Total en Reposo con Fernet (`.json.enc`)
- Ninguna terminal de mesa ni servidor de monitoreo almacena credenciales ni claves privadas en texto plano (`.json` o `.env`).
- Las configuraciones de las mesas (`mesa_config.json.enc`), listas de candidatos (`candidatos.json.enc`) y carteras globales (`wallets.json.enc`) se cifran mediante **Fernet (AES-128 en modo CBC con autenticación HMAC-SHA256)**.
- El generador por lotes elimina automáticamente todos los archivos `.json` en texto plano tras compilar las mesas.

### 2. 🛡️ Protección de Terminales contra Manipulación Física (Ofuscación PyArmor)
- Cada paquete de mesa electoral desplegado en `mesas_desplegadas/mesa_code<N>/` es transformado y ofuscado mediante **PyArmor**.
- Esto blinda la clave criptográfica empotrada en el bytecode de Python, imposibilitando que operadores de mesa o atacantes con acceso físico a las tarjetas SD / discos de las terminales puedan extraer las `Admin Keys`, alterar las direcciones de pago o modificar el código de votación.

### 3. 🧠 Descifrado Transparente Exclusivo en Memoria RAM
- El backend de la urna descifra las credenciales directamente en memoria durante el arranque del proceso Flask, sin volcar archivos temporales ni exponer información en el sistema de archivos local.

### 4. 🧅 Enrutamiento Anónimo Resiliente sobre Red Tor (.onion)
- Todas las peticiones HTTP y WebSockets hacia el nodo LNbits viajan a través del proxy **Tor SOCKS5h (`socks5h://127.0.0.1:9050`)**, blindando la ubicación física de las mesas y mitigando censura o ataques dirigidos de denegación de servicio (DDoS).

### 5. ⚡ Límite de Capacidad Inmanipulable por Saldo Real (Sats)
- La capacidad de votos de cada mesa se rige matemáticamente por el saldo real de su wallet en satoshis:
  $$\text{Votos Restantes} = \left\lfloor \frac{\text{Saldo Actual (Sats)}}{\text{Sats por Voto}} \right\rfloor$$
- Si la wallet se queda sin fondos, el backend bloquea automáticamente la emisión de votos (HTTP 403) y la interfaz táctil muestra un banner de cierre de mesa.

### 6. 🖨️ Doble Auditoría con Comprobantes Físicos Térmicos
- Cada voto confirmado genera un comprobante físico impreso con el nombre de la mesa, candidato, fecha/hora, **Payment Hash Lightning** y el **Checksum SHA-256** de la foto de la cédula cifrada, respaldado con un código QR para auditoría física cruzada en urna tradicional.

### 7. 📸 Cifrado Biométrico de Cédulas Vinculado al Voto
- Durante el sufragio, la foto del documento de identidad es capturada y cifrada al instante utilizando como clave simétrica el propio **Payment Hash** emitido por la red Lightning. Solo con las transacciones oficiales es posible restaurar las imágenes en la fase de escrutinio posterior.

---

## 🏗️ Arquitectura General del Sistema

```
                                  ┌──────────────────────────────────────────┐
                                  │      Urna Táctil de Mesa (Puerto 2007)   │
                                  │    [mesas_desplegadas/mesa_code<N>/]     │
                                  │      (PyArmor + Fernet RAM Decrypt)      │
                                  └────────────────────┬─────────────────────┘
                                                       │ 
                                                       │ Transacción Lightning por Tor (Sats + Memo Cifrado)
                                                       ▼
┌──────────────────────────────────────────┐       ┌──────────────────────────────────────────┐
│   Dashboard Interactivo de Auditoría    │◄──────┤       Nodo LNbits (Red Tor .onion)       │
│   (Puerto 7070)                          │       └────────────────────┬─────────────────────┘
│   [audit/auditoria_ln_votos.py]          │                            │
│   (Soporte --fernet-key)                 │                            │ WebSockets en Tiempo Real
└──────────────────────────────────────────┘                            │
                                                                        ▼
                                                   ┌──────────────────────────────────────────┐
                                                   │   Dashboard de Monitoreo (Puerto 5050)   │
                                                   │      [frontend/votos_dashboard.py]       │
                                                   │      (Soporte --fernet-key)              │
                                                   └──────────────────────────────────────────┘
```

---

## 📸 Componentes de la Plataforma

| Componente | Puerto | Descripción |
|---|---|---|
| **Urna Electoral Web** | `2007` (o config) | Interfaz táctil para el elector con captura de cédula, emisión Lightning y generación de comprobante. |
| **Dashboard de Monitoreo** | `5050` | Tablero de escrutinio en tiempo real de candidatos y monitoreo de saldo de mesas vía WebSockets. |
| **Dashboard de Auditoría** | `7070` | Reconciliación matemática 1:1, matriz origen-destino y detección de votos no autorizados. |
| **Generador por Lote** | CLI | Orquestador de cifrado, clonación y ofuscación masiva de terminales de mesa. |
| **Desencriptador de Cédulas**| CLI | Recuperador automatizado de fotos de identidad post-elección mediante hashes Lightning. |

---

## 🚀 Guía de Uso y Despliegue Paso a Paso

### Paso 0: Instalación de Dependencias

```bash
git clone <URL_DEL_REPOSITORIO>
cd sistema-votacion-btcol
bash setup.sh
```

Asegúrate de que el servicio Tor esté activo:
```bash
sudo systemctl start tor
```

---

### Paso 1: Generar la Clave Criptográfica Centralizada

Genera una clave Fernet aleatoria de 44 caracteres Base64:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
*Ejemplo de salida:* `StxCyZIWBe4dvdrp14Wd3-xMNLJyQfJMBjLL2A0VbfE=`

---

### Paso 2: Configurar y Desplegar las Mesas en Lote

1. Edita el archivo `generador_configuracion_lote/wallets.csv` con las wallets y claves de candidatos y mesas.
2. Edita `generador_configuracion_lote/config_global.md` con la URL de LNbits (`.onion`) y satoshis por voto.
3. Ejecuta el generador pasando tu clave:
```bash
python3 generador_configuracion_lote/generar_configs.py --fernet-key "TU_CLAVE_FERNET="
```

**¿Qué hace este comando automáticamente?**
- Genera `candidatos.json.enc` y `mesa_config.json.enc` para cada mesa.
- Crea `data/wallets.json.enc` para los dashboards de monitoreo y auditoría.
- Clona la urna electoral en `generador_configuracion_lote/mesas_desplegadas/mesa_code1/`, `mesa_code2/`, etc.
- Inyecta la clave Fernet dentro del código de cada mesa.
- **Ofusca el código con PyArmor** para blindar la terminal.
- Elimina los archivos `.json` en texto plano.

---

### Paso 3: Iniciar las Terminales de Votación (Urnas Electorales)

En cada equipo o Raspberry Pi asignada a una mesa electoral:

```bash
cd generador_configuracion_lote/mesas_desplegadas/mesa_code1
python3 app_web_mesa.py
```
*Acceso en pantalla táctil o navegador:* `http://localhost:2007` (o la IP de la mesa).

---

### Paso 4: Iniciar el Dashboard de Monitoreo en Tiempo Real (Puerto 5050)

Solo para administradores electorales autorizados:

```bash
python3 frontend/votos_dashboard.py --fernet-key "TU_CLAVE_FERNET="
```
*Acceso en navegador:* `http://localhost:5050`

---

### Paso 5: Iniciar el Dashboard de Auditoría Electoral (Puerto 7070)

Para auditores y veedores del proceso:

```bash
python3 audit/auditoria_ln_votos.py --fernet-key "TU_CLAVE_FERNET="
```
*Acceso en navegador:* `http://localhost:7070`

---

### Paso 6: Escrutinio y Desencriptación Masiva de Cédulas

Una vez concluido el evento electoral, los auditores pueden desencriptar las imágenes de los votantes utilizando los hashes de pago generados por la red:

```bash
./desencriptador/desencriptar_lote.sh
```
Las imágenes recuperadas y el reporte con Checksum SHA-256 se guardarán en:
`desencriptador/cedulas_desencriptadas/`

---

## 🔒 Buenas Prácticas de Seguridad en Producción

> [!IMPORTANT]
> **Custodia de Claves Fernet:**
> Las claves criptográficas Fernet permiten descifrar en memoria las carteras y la configuración del evento. Deben ser manejadas y custodiadas estrictamente por los administradores y auditores autorizados.

> [!CAUTION]
> **Protección del Repositorio:**
> El archivo `.gitignore` excluye automáticamente archivos `.csv`, `.json`, `.enc`, `*.db`, bases de datos SQLite y carpetas de capturas. Nunca fuerces la inclusión de credenciales ni claves en el control de versiones.

---

## 📄 Licencia

Software libre y de código abierto desarrollado bajo principios de transparencia democrática, soberanía digital y criptografía inmutable sobre **Bitcoin Lightning Network**.

