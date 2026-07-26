# Registro de Cambios (Changelog) - Sistema de Votación BTCOL

## v4.0.0 - Escalabilidad WebSockets y Tolerancia a Fallos Tor (Julio 2026)

### 🚀 Mejoras Arquitectónicas Mayores
- ✅ **Sincronización Ultrarrápida WebSockets + RAM**: 
  - Se reescribió la arquitectura del `frontend/votos_dashboard.py` eliminando por completo el patrón de polling HTTP masivo sobre la red Tor.
  - El backend ahora crea hilos independientes que mantienen conexiones WebSockets pasivas y permanentes (`wss://`) hacia LNbits. 
  - El estado se consolida en la memoria RAM, permitiendo al frontend actualizar su renderizado HTML a un intervalo de 2 segundos con cero peticiones de red hacia LNbits, garantizando latencias submilisegundo a nivel de dashboard.

- ✅ **Manejo Híbrido y Fallback Anti-Tor Drops**: 
  - Se mitigó la problemática natural de la inestabilidad de la red Tor. LNbits, por su arquitectura interna, omite enviar notificaciones WebSocket en pagos salientes (Mesas). 
  - Para resolver esto, se integró un hilo híbrido secundario (`DashboardSync`) que obliga una sincronización ligera por HTTP estrictamente cada 15 segundos para consolidar la consistencia de los datos en caso de reconexiones Tor o fallos de notificaciones asíncronas.

- ✅ **Tolerancia a Proxies SOCKS5 Dinámicos**:
  - Implementación nativa de enrutamiento a través de `.onion` en el cliente `websocket-client` haciendo uso del módulo subyacente `python-socks`. 
  - Se descarta el monkey-patching sobre sockets globales, aislando correctamente las resoluciones DNS y bloqueando las fugas DNS (DNS leaks) en los dashboards.

## v3.1.0 - Resiliencia de Conteos e Interfaz Dinámica (Principios 2026)

### ✨ Mejoras de Interfaz de Usuario
- ✅ **Dashboard de Monitoreo Optimizado (`votos_dashboard.py`)**:
  - Renovación total de la cuadrícula de tarjetas de candidatos (layout 2 columnas divididas). 
  - Aumento visual de la tipografía y de la fotografía oficial del candidato.
  - Integración de barra de porcentaje con gradiente que mapea el progreso relativo del candidato vs la suma total del escrutinio general.

- ✅ **Caché `last_known_status`**:
  - Para evitar saltos abruptos o parpadeos a "0 votos" cuando una solicitud HTTP de consulta caía producto de retardos de Tor, el frontend ahora retiene el último estado matemático comprobado en pantalla, manteniendo la robustez de las proyecciones visuales ante la prensa o los auditores.

## v3.0.0 - Unificación a Base de Datos y Centralización JSON (2024 - 2025)

### 🔒 Consolidación Criptográfica y de Estructura
- ✅ **Single Source of Truth (`data/wallets.json`)**:
  - Se descartó el modelo hardcodeado en variables `.env`. 
  - Se consolidó un diccionario unificado JSON escalable que permite integrar cientos de mesas o candidatos adicionales sin tocar el código base, empleando exclusivamente `Invoice Keys` (permisos de solo lectura) de las carteras LNbits.
  
- ✅ **Fórmula Límite de Votos por Saldo Real**:
  - Sustitución de contadores en disco por un límite físico criptográfico: los votos ahora se miden por el balance disponible de satoshis remanentes. 
  - Bloqueo por validación estricta de saldo previo a permitir la activación del módulo fotográfico WebRTC.

## v2.0.0 a v2.1.0 - Modo Solo Lectura (Principios 2024)

- ✅ **Mitigación de Riesgos (Read-Only)**: Desacoplamiento total del uso de `Admin Keys` en las plataformas visuales, permitiendo auditar y monitorizar sin delegar privilegios de firma a los dashboards.
- ✅ **Autocarga .env**: Despliegue de priorización para variables de entorno usando `python-dotenv`.

## v1.0.0 - Versión Base Inicial

- Estructura original de votación LNbits mediante polling crudo y validación local de 3 candidatos fijos.
