# 🔓 Módulo de Desencriptación y Auditoría Biométrica en Lote
### *Herramienta de Escrutinio y Verificación Criptográfica de Identidad*

---

## 📖 Descripción General

Durante el proceso electoral, cada terminal de mesa captura la fotografía del documento de identidad del elector y la cifra instantáneamente al vuelo antes de guardarla en disco.

La clave simétrica empleada para el cifrado de cada imagen es el **Payment Hash único de la transacción Lightning Network** emitido por LNbits al procesarse el voto.

Este módulo permite a los **auditores y autoridades electorales autorizadas** restaurar y auditar en lote todas las fotografías capturadas, validando su correspondencia matemática 1:1 con las transacciones registradas en el libro contable Lightning.

---

## 🚀 Guía de Uso

### 1️⃣ Ejecución Automática (Auto-Descubrimiento de Mesas)

Si no especificas argumentos, el orquestador escaneará automáticamente todas las mesas desplegadas en `generador_configuracion_lote/mesas_desplegadas/mesa_code*` y la mesa base `mesa_code/`:

```bash
./desencriptador/desencriptar_lote.sh
```

### 2️⃣ Especificar Mesas o Directorios Específicos

Puedes auditar una o varias mesas específicas pasando sus nombres o directorios:

```bash
# Auditar únicamente mesa_code6
./desencriptador/desencriptar_lote.sh -d mesa_code6

# Auditar múltiples mesas
./desencriptador/desencriptar_lote.sh -d mesa_code1 mesa_code2 mesa_code6

# Pasar rutas completas
python3 desencriptador/desencriptar_lote_cedulas.py -d generador_configuracion_lote/mesas_desplegadas/mesa_code3
```

---

## 📁 Estructura de Salida de Imágenes Restauradas

Para evitar sobreescrituras, las imágenes reconstruidas se almacenan organizadas por subcarpetas de mesa en:
👉 `desencriptador/cedulas_desencriptadas/<nombre_mesa>/restaurada_<memo_hash>.jpg`

Ejemplo:
```
desencriptador/cedulas_desencriptadas/
├── mesa_code1/
│   ├── restaurada_a1b2c3d4e5f67890.jpg
│   └── restaurada_f9e8d7c6b5a43210.jpg
├── mesa_code6/
│   └── restaurada_1f5c7f0571f542ac.jpg
```

---

## 🛡️ Verificación de Integridad Criptográfica (Checksum SHA-256)

Al procesar cada documento, el script calcula e imprime un informe consolidado de integridad:
- **Mesa Electoral procesada**
- **Archivo Fuente (.enc)**
- **Payment Hash utilizado como clave**
- **Checksum SHA-256 del comprobante original**
- **Estado de validación (ÉXITO / FALLO)**

---

## 🔒 Consideraciones de Privacidad y Seguridad

> [!IMPORTANT]
> **Acceso Restringido a Auditores:**
> Las imágenes restauradas contienen datos personales protegidos. Este procedimiento debe realizarse únicamente durante el acto formal de auditoría y escrutinio electoral por personal debidamente acreditado.
