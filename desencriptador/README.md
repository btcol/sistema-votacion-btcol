# 🔓 Módulo de Desencriptación y Auditoría Biométrica en Lote
### *Herramienta de Escrutinio y Verificación Criptográfica de Identidad*

---

## 📖 Descripción General

Durante el proceso electoral, cada terminal de mesa captura la fotografía del documento de identidad del elector y la cifra instantáneamente al vuelo antes de guardarla en disco.

La clave simétrica empleada para el cifrado de cada imagen es el **Payment Hash único de la transacción Lightning Network** emitido por LNbits al procesarse el voto.

Este módulo permite a los **auditores y autoridades electorales autorizadas** restaurar y auditar en lote todas las fotografías capturadas, validando su correspondencia matemática 1:1 con las transacciones registradas en el libro contable Lightning.

---

## 🚀 Guía de Uso

### 1️⃣ Ejecutar la Desencriptación Automática

El script orquestador procesa todos los archivos binarios `.enc` ubicados en las terminales de votación:

```bash
./desencriptador/desencriptar_lote.sh
```

### 2️⃣ Directorio de Salida de Imágenes Restauradas

Las imágenes reconstruidas se almacenan en:
👉 `desencriptador/cedulas_desencriptadas/`

### 3️⃣ Verificación de Integridad Criptográfica (Checksum SHA-256)

Al procesar cada documento, el script calcula e imprime un informe de integridad:
- **Archivo Fuente (.enc)**
- **Payment Hash utilizado como clave**
- **Checksum SHA-256 del comprobante original**
- **Estado de validación (ÉXITO / FALLA)**

---

## 🔒 Consideraciones de Privacidad y Seguridad

> [!IMPORTANT]
> **Acceso Restringido a Auditores:**
> Las imágenes restauradas contienen datos personales protegidos. Este procedimiento debe realizarse únicamente durante el acto formal de auditoría y escrutinio electoral por personal debidamente acreditado.

