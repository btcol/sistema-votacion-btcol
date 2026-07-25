# 🔓 Módulo de Desencriptación de Cédulas en Lote

Este módulo se encarga de recuperar y auditar las fotos de cédulas capturadas de manera segura durante el proceso de votación en las Mesas Electorales.

## ⚙️ ¿Cómo usar este módulo?

El módulo cuenta con un script principal `desencriptar_lote.sh` que se encarga de automatizar todo el proceso. **No necesitas ingresar claves manualmente**, ya que el sistema extrae automáticamente el Hash de la factura LNbits de cada archivo `.enc` para utilizarlo como su clave de descifrado individual.

### 1️⃣ Ejecutar la desencriptación automática

Desde la raíz del repositorio, ejecuta:

```bash
./desencriptador/desencriptar_lote.sh
```

### 2️⃣ ¿Dónde se guardan las imágenes?

El script leerá automáticamente la carpeta `mesa_code/impresora/capturas_cedula/` donde están los archivos `.enc` y guardará todas las imágenes reconstruidas de forma idéntica en:

👉 `desencriptador/cedulas_desencriptadas/`

### 3️⃣ Auditoría

Al finalizar, el script imprime un reporte de auditoría en la terminal, mostrando qué archivos se procesaron, el checksum SHA-256 de integridad de cada archivo y el estado de la restauración (éxito o falla).
