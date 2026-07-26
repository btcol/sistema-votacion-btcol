# 🗳️ Resumen Ejecutivo - Sistema de Votación BTCOL (LNbits)

**Plataforma de alta disponibilidad para votaciones electrónicas seguras, transparentes y auditables apoyadas sobre Bitcoin Lightning Network.**

Este proyecto plantea un paradigma disruptivo en los modelos de elecciones y comicios modernos: la sustitución de papeletas y urnas analógicas por **transacciones de satoshis sobre la red Lightning (implementación LNbits)**, aunada a un estricto mecanismo biométrico de validación de identidad cifrada con protección *Zero Knowledge* para evadir fraudes y coacciones.

## 🎯 Experiencia de Votación y Funcionamiento

1. **Interacción del Elector**: El ciudadano opera una "Urna Web" (una terminal táctil, tableta o computadora en el centro de votación).
2. **Selección**: Interactúa con la tarjeta y fotografía del candidato de su preferencia.
3. **Validación de Identidad Inalterable**: El dispositivo inicia un canal WebRTC local. El elector presenta su documento nacional de identidad a la cámara web. El sistema ejecuta una captura fotográfica en alta resolución del mismo.
4. **Cifrado Automático (Zero Knowledge)**: Para asegurar el anonimato absoluto, el archivo fotográfico **no** se almacena en su forma binaria original (texto plano). En su lugar, el sistema transacciona un pago a la billetera (wallet) del candidato seleccionado a través de la red Lightning. Una vez finalizada la confirmación de la red, ésta emite una huella criptográfica de confirmación (`payment_hash`). El algoritmo de la plataforma intercepta este hash y lo emplea como **clave maestra simétrica** para encriptar la biometría del elector en mili-segundos. Con esto, únicamente las entidades en posesión del listado de firmas hash de la elección podrán acceder a los datos.
5. **Comprobante Físico Auditado**: La urna imprime o despliega un recibo electoral que detalla: la fecha, hora, candidato seleccionado, el Hash de transacción, y un **código QR que codifica el checksum matemático SHA-256** del archivo encriptado. Dicho esquema blinda legal y logísticamente cualquier posibilidad de inyección o adulteración posterior de la información.

## 🛡️ Estándares de Seguridad y Transparencia

- **Red Anónima Tor (.onion)**: El tránsito completo de los votos (transacciones LN) se canaliza desde las mesas físicas hacia el servidor central a través de proxies Tor. Este mecanismo previene por completo ataques dirigidos tipo DDoS y bloquea cualquier intento de censura por parte de ISP's o entidades estatales hostiles.
- **Autorizaciones Limitadas Inmanipulables**: Ninguna mesa maneja un umbral de votantes configurado en texto estático. El límite operativo para los votos se determina dinámicamente según el saldo remanente (en satoshis) albergado en la `wallet` matriz de cada mesa electoral. Al agotarse dichos fondos, la terminal se bloqueará impidiendo técnicamente el registro de más votos.
- **Auditoría Matemática en Tiempo Real**: Toda discrepancia entre la traza blockchain de LNbits y los datos resguardados físicamente por la mesa activan alarmas dentro del módulo de Auditoría Electoral. El sistema detecta inmediatamente anomalías, incluyendo depósitos o inyecciones irregulares hacia las billeteras de los candidatos desde fuentes externas.

## 🚀 Arquitectura de Módulos Centrales

1. **Urna Electoral Web (Puerto 2007)**: Interfaz del centro de votación para la captura fotográfica del elector y desencadenante de pagos a Lightning.
2. **Dashboard de Monitoreo Analítico (Puerto 5050)**: Servidor apoyado en *WebSockets* y almacenamiento RAM para proyectar el escrutinio oficial con tasas de recarga sub-milisegundo, mitigando de raíz el impacto de latencia característico de la red Tor.
3. **Dashboard de Auditoría Escrutadora (Puerto 7070)**: Consola de control e inteligencia para fiscales electorales responsables de detectar transacciones malformadas y confirmar cruces de hashes SHA-256.
4. **Módulo Desencriptador Offline Automático**: Suite criptográfica de pos-elección capaz de iterar sobre los logs generados y descifrar volúmenes de documentos de identidad, certificando matemáticamente la veracidad humana por detrás de cada transacción Lightning aprobada.
