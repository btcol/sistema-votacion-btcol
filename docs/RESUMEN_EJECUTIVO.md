# 🗳️ Resumen Ejecutivo - Sistema de Votación BTCOL (LNbits)

**Sistema integral para votaciones electrónicas seguras, transparentes y auditables basado en la red Bitcoin Lightning Network.**

Este proyecto plantea una solución disruptiva a las elecciones tradicionales: reemplazar las papeletas de papel y urnas físicas por **transacciones de satoshis (fracciones de Bitcoin) sobre la red Lightning (LNbits)** y añadir una fuerte capa de validación de identidad in situ con criptografía simétrica para evitar fraudes, coacciones o falsificaciones.

## 🎯 ¿Cómo Funciona la Experiencia de Votación?

1. **Interacción Natural**: El elector se acerca a la "Urna Web" (una pantalla táctil corriendo en una tablet o computadora).
2. **Selección**: Toca la tarjeta con la foto de su candidato preferido.
3. **Captura de Identidad Inalterable**: La pantalla activa instantáneamente la cámara web. El elector muestra su Documento de Identidad o Cédula. El sistema toma una fotografía en alta resolución.
4. **Cifrado Automático (Zero Knowledge)**: Para garantizar la privacidad, la foto *no* se guarda visible en texto plano. Se genera un pago a la wallet del candidato en la red Lightning. La red arroja un comprobante criptográfico único (Hash de Pago). El sistema toma ese hash y lo usa como **clave maestra simétrica** para encriptar la foto en milisegundos. Solo quien conozca el hash exacto del voto podrá desbloquear la foto.
5. **Comprobante Físico**: Se emite automáticamente un ticket por impresora térmica que contiene la fecha, hora, el nombre del candidato, el Hash de la transacción y un **código QR con el Checksum SHA-256** del archivo encriptado para que el elector o los auditores certifiquen que la foto no fue adulterada a posteriori.

## 🛡️ Pilares de Seguridad y Transparencia

- **Red Anónima Tor (.onion)**: Toda la comunicación de votos (pagos Lightning) entre la Mesa y el nodo central pasa a través de la red Tor. Esto anonimiza el origen geográfico de los votos, protegiendo a los centros de votación contra censura o ataques dirigidos (DDoS).
- **Límite de Capacidad Inmanipulable**: No existen "archivos Excel" manipulables que digan cuántos votos puede emitir una mesa. El límite se calcula matemáticamente por la cantidad real de Satoshis en la wallet matriz de la mesa. Si la mesa se queda sin fondos, la pantalla se bloquea físicamente impidiendo cargar más votos de forma fraudulenta.
- **Auditoría 100% Matemática**: Al cruzar el reporte de los hashes en la blockchain Lightning contra el total de archivos `.enc` capturados, cualquier discrepancia salta a la luz. El módulo de Auditoría en Tiempo Real detecta automáticamente los "Votos Irregulares" (es decir, fondos o votos que hayan llegado a un candidato sin provenir de una mesa autorizada).

## 🚀 Módulos del Sistema

1. **Urna Electoral Web (Puerto 2007)**: La pantalla táctil del votante con captura de cámara en vivo y emisión de pago LNbits.
2. **Dashboard de Monitoreo (Puerto 5050)**: Pantalla gigante para ver el escrutinio de los candidatos actualizarse en vivo en el centro de campaña.
3. **Dashboard de Auditoría (Puerto 7070)**: Consola para fiscales electorales que detecta transacciones irregulares y valida los hashes criptográficos.
4. **Módulo Desencriptador Automático**: Herramienta de auditoría post-elección que lee automáticamente los hashes LNbits y desencripta miles de fotos de cédulas en segundos para verificar la validez humana de cada voto emitido.
