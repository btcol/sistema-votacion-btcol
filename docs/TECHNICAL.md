# ⚙️ Arquitectura Técnica del Sistema de Votación BTCOL

Este documento describe la arquitectura interna, los flujos de datos y los esquemas de seguridad aplicados en la plataforma de Votación BTCOL basada en **Python (Flask)**, **WebRTC** y **Bitcoin Lightning Network (LNbits)** sobre **Tor**.

## 🏗️ Topología del Sistema

El sistema está desacoplado en 3 servidores web autónomos y un módulo CLI de auditoría:

1. **Urna Electoral (`mesa_code/app_web_mesa.py`)**: 
   - **Frontend**: Interfaz táctil (`index.html` + `app.js`) que usa la API **WebRTC** de HTML5 para capturar video de la cámara web (Cédula).
   - **Backend**: Servidor Flask en el puerto `2007`. Recibe la foto en Base64, se comunica con el nodo LNbits, genera la encriptación local, actualiza SQLite y emite el ticket.

2. **Dashboards de Monitoreo (`frontend/votos_dashboard.py` y `audit/auditoria_ln_votos.py`)**:
   - Componentes reactivos en modo solo lectura (usan `Invoice Keys`).
   - Sincronizan el estado de LNbits cada 20 o 30 segundos, mitigando la sobrecarga sobre la red Tor.

3. **Módulo Desencriptador Lote (`desencriptador/desencriptar_lote.sh`)**:
   - Script Bash + Python que no requiere conexión a red. Lee metadatos locales y reconstruye criptográficamente el padrón de cédulas fotografiado usando las claves simétricas dinámicas.

## 🔐 Flujo Criptográfico del Voto

El siguiente es el pipeline técnico paso a paso desde que el usuario confirma el voto hasta la emisión del ticket:

1. **WebRTC al Backend**: El navegador toma un fotograma `.jpg` recortado de la cámara, lo codifica en Base64 y lo envía mediante `POST /api/votar` junto con el ID del candidato seleccionado.
2. **Pago Lightning (LNbits)**: El backend hace un HTTP POST usando la `Admin Key` de la Mesa hacia el servidor LNbits remoto (enrutado a través de un proxy SOCKS5 local `127.0.0.1:9050` a la dirección `.onion`). El pago transfiere los satoshis configurados (ej: 100 sats).
3. **Respuesta Criptográfica**: Si el pago es exitoso, el nodo LNbits devuelve un `payment_hash` (ej: `957228c167894bf3...`).
4. **Cifrado Simétrico PBKDF2 + AES (Memoria a Disco)**: 
   - El sistema decodifica el Base64 a bytes binarios crudos de la imagen JPEG.
   - El sistema **NUNCA** escribe este JPEG crudo al disco.
   - Utiliza el `payment_hash` como contraseña maestra para generar una clave AES de 256 bits mediante el estándar de derivación de claves seguras **PBKDF2** (con un Salt estático aleatorizado).
   - El archivo resultante, totalmente ilegible, se guarda como `mesa_code/impresora/capturas_cedula/<payment_hash>.enc`.
5. **Checksum y Deduplicación**: Se calcula el **SHA-256** del archivo `.enc`. Este checksum y el `payment_hash` se insertan en la base de datos local `votos_local.db` (SQLite) y garantizan la inmutabilidad y deduplicación.
6. **Ticket QR**: Se genera dinámicamente un comprobante JPEG de alta resolución con todos los datos y un código QR renderizado con el Checksum.

## 🗄️ Esquema de la Base de Datos Local (SQLite)
Ruta: `mesa_code/data_mesa/votos_local.db`

La tabla principal `votos_emitidos` mantiene el registro de resiliencia local en caso de que la mesa pierda conexión:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | INTEGER (PK) | Auto incremental |
| `mesa_id` | TEXT | Identificador de la mesa (ej: `mesa_001`) |
| `candidato_id` | TEXT | ID del candidato elegido |
| `timestamp` | DATETIME | Fecha y hora de la transacción |
| `payment_hash_mesa` | TEXT (UNIQUE) | Hash LNbits de la transacción enviada |
| `archivo_cedula_enc` | TEXT | Nombre del archivo cifrado (ej: `<hash>.enc`) |
| `checksum256_cedula` | TEXT | Hash SHA-256 matemático del archivo cifrado para auditoría |

## 🌐 Gestión de Conexiones Tor (.onion)

El módulo `mesa_code/scripts/cliente_lightning.py` inyecta automáticamente el uso de proxies si detecta una dirección `.onion` en el archivo de configuración, configurando la librería `requests` de la siguiente forma:

```python
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
```
*El uso de `socks5h` asegura que la resolución DNS del dominio `.onion` se haga remotamente a través de Tor, no localmente (evitando DNS Leaks).*
