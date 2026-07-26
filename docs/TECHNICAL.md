# ⚙️ Arquitectura Técnica del Sistema de Votación BTCOL

Este documento describe la arquitectura interna, los flujos de datos y los esquemas de seguridad implementados en la plataforma de Votación BTCOL, basada en **Python (Flask)**, **WebRTC** y **Bitcoin Lightning Network (LNbits)** a través de la red anónima **Tor**.

## 🏗️ Topología del Sistema

El ecosistema se distribuye en tres servidores web autónomos y un módulo CLI de auditoría en frío:

1. **Urna Electoral Web (`mesa_code/app_web_mesa.py`)**: 
   - **Frontend**: Interfaz de usuario táctil (`index.html` y `app.js`) que emplea la API **WebRTC** de HTML5 para capturar biometría fotográfica de documentos de identidad desde la cámara web.
   - **Backend**: Servidor Flask expuesto en el puerto `2007`. Recibe la fotografía codificada en Base64, tramita la transacción a través del nodo LNbits, ejecuta el algoritmo de cifrado, actualiza la base de datos local SQLite y genera el recibo del voto.

2. **Dashboards de Monitoreo (`frontend/votos_dashboard.py` y `audit/auditoria_ln_votos.py`)**:
   - Plataformas analíticas operando estrictamente en modo de solo lectura (mediante `Invoice Keys`).
   - Implementan un modelo de **WebSockets multihilo en backend** con estado en memoria RAM, erradicando el polling masivo sobre la red Tor y ofreciendo tiempos de respuesta de latencia ultrabaja para el usuario final.

3. **Módulo de Desencriptación en Lote (`desencriptador/desencriptar_lote.sh`)**:
   - Herramienta automatizada en Bash y Python diseñada para auditar el padrón biométrico en instalaciones offline (air-gapped). Reconstruye criptográficamente los archivos empleando las claves simétricas dinámicas generadas en las transacciones Lightning.

## 🔐 Flujo Criptográfico de Emisión de Voto

El siguiente pipeline detalla paso a paso las operaciones técnicas ejecutadas desde la selección del candidato hasta la generación del comprobante:

1. **Captura WebRTC a Backend**: El navegador extrae un fotograma en formato `.jpg` recortado, lo codifica en Base64 y lo transmite mediante el endpoint `POST /api/votar`, incluyendo el identificador del candidato.
2. **Emisión de Pago Lightning (LNbits)**: El backend genera una petición HTTP POST utilizando la `Admin Key` de la Mesa Electoral. Esta solicitud se enruta nativamente por un proxy SOCKS5 local (`127.0.0.1:9050`) hacia la dirección `.onion` del nodo LNbits, efectuando el pago en satoshis previamente configurado.
3. **Acuse de Recibo Criptográfico**: Si el pago se propaga y confirma exitosamente, el nodo LNbits retorna de manera síncrona el `payment_hash` de la transacción (ejemplo: `957228c167894bf3...`).
4. **Cifrado Simétrico PBKDF2 + AES-256 (RAM a Disco)**: 
   - El sistema decodifica la carga útil Base64 obteniendo el binario crudo del formato JPEG.
   - **Importante**: En ningún momento se vuelca el archivo JPEG crudo sobre el sistema de archivos del servidor.
   - El algoritmo utiliza el `payment_hash` como semilla (contraseña maestra) en conjunto con un estándar de derivación **PBKDF2** y un Salt aleatorio para generar la clave AES-256.
   - El archivo binario resultante, ofuscado y seguro, se almacena en `mesa_code/impresora/capturas_cedula/<payment_hash>.enc`.
5. **Generación de Checksum y Deduplicación**: El sistema procesa un algoritmo hash **SHA-256** sobre el binario final `.enc`. Tanto este Checksum como el `payment_hash` se registran en la base de datos `votos_local.db` para garantizar la inmutabilidad absoluta de la operación.
6. **Comprobante Físico/Digital (Ticket QR)**: El backend emite una imagen JPEG de alta resolución con un código QR que embebe el hash SHA-256 de auditoría del archivo cifrado.

## 🗄️ Esquema de la Base de Datos Local (SQLite)
Ruta: `mesa_code/data_mesa/votos_local.db`

La tabla central `votos_emitidos` mantiene un log transaccional resiliente para asegurar la recuperación del sistema de escrutinio frente a fallos temporales de conexión:

| Columna | Tipo de Dato | Descripción |
|---------|------|-------------|
| `id` | INTEGER (PK) | Identificador secuencial autonumérico. |
| `mesa_id` | TEXT | Identificador unívoco de la Mesa Electoral. |
| `candidato_id` | TEXT | Identificador del candidato receptor. |
| `timestamp` | DATETIME | Marca de tiempo ISO-8601 de la transacción. |
| `payment_hash_mesa` | TEXT (UNIQUE) | Hash oficial emitido por Lightning Network (`bolt11`). |
| `archivo_cedula_enc` | TEXT | Nombre del documento biométrico en disco (`<hash>.enc`). |
| `checksum256_cedula` | TEXT | Firma matemática SHA-256 del binario cifrado para comprobación de auditoría. |

## 🌐 Gestión de Enrutamiento y WebSockets Tor (.onion)

El módulo `mesa_code/scripts/cliente_lightning.py` inyecta configuraciones SOCKS5 de manera dinámica al detectar un endpoint `.onion` en el ambiente. La librería `requests` opera bajo las siguientes variables:

```python
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
```

El protocolo `socks5h` asegura que la resolución DNS de los dominios `.onion` sea delegada en su totalidad al circuito remoto de Tor, previniendo mitigaciones y fugas de DNS (DNS Leaks). Además, los submódulos WebSocket, integrados a partir de los recientes parches de optimización de RAM, utilizan la sintaxis proxy nativa de `websocket-client` para sostener sesiones asíncronas fiables a través del proxy SOCKS5 local sin sobrecargar la red onion en las consultas HTTP GET masivas de los dashboards.
