# 🛠️ Generador Masivo de Configuraciones JSON & Encriptación Fernet

Módulo automatizado en Python para procesar archivos CSV de wallets de la plataforma y un archivo de parámetros globales en Markdown (`config_global.md`), generando y encriptando en lote todas las configuraciones JSON necesarias para las Mesas Electorales, la Urna Web y los Dashboards de Auditoría/Monitoreo Global.

## ⚙️ Archivo de Parámetros Globales (`config_global.md`)

Puedes definir la URL de tu nodo LNbits (`url_lnbits`) y el valor en satoshis por voto (`sats_per_vote`) editando el archivo `config_global.md`:

```markdown
# ⚙️ Parámetros Globales de Configuración

- **url_lnbits**: http://tu_nodo_lnbits_o_tor.onion
- **sats_per_vote**: 1
```

---

## 📁 Estructura de Salida Generada

Al ejecutar `generar_configs.py`, se crean automáticamente en una sola pasada tanto los archivos `.json` en texto plano como sus versiones cifradas `.json.enc` con la clave Fernet empotrada:

```
generador_configuracion_lote/
├── config_global.md
├── wallets.csv
├── generar_configs.py               <-- Script unificado de generación y cifrado
├── candidatos.json                  <-- Lista consolidada en texto plano
├── candidatos.json.enc              <-- Lista consolidada cifrada con Fernet
├── wallets.json                     <-- Monitoreo global en texto plano
├── wallets.json.enc                 <-- Monitoreo global cifrado
└── mesas_config/
    ├── mesa_code1/
    │   ├── mesa_config.json
    │   └── mesa_config.json.enc    <-- Configuración cifrada lista para producción
    ├── mesa_code2/
    │   ├── mesa_config.json
    │   └── mesa_config.json.enc
    └── mesa_code3/
        ├── mesa_config.json
        └── mesa_config.json.enc
```

---

## 📊 Formato del Archivo CSV de Entrada

El CSV debe contener el siguiente encabezado de columnas:

```csv
"wallet_name","wallet_id","admin_key","invoice_key","initial_balance","status","error"
"candidato1","f8531e0f4b274852a45db0b199eb9fbb","","903ab1afc1034726ae12274b3cb277b5","0","success",""
"mesa1","37f8e544cbb04d1faacd668cc7a3d2d3","d56f9970fa5641f585fec79b8d9b3390","a31a64e9a0fc423dbe79e172a5b08ada","500","success",""
```

### Regla de Diferenciación Automática:
- **Mesa Electoral**: La fila contiene un valor no vacío en la columna `admin_key`. Se guarda en `mesas_config/mesa_code<N>/mesa_config.json` y `mesa_config.json.enc`.
- **Candidato**: La columna `admin_key` está vacía (`""`). Se agrupa en `candidatos.json` y `candidatos.json.enc`.

---

## 🚀 Instrucciones de Uso

```bash
# 1. Generación estándar (crea archivos .json y cifrados .json.enc)
python generador_configuracion_lote/generar_configs.py

# 2. Generación limpia para producción (elimina los .json planos y deja solo los .json.enc cifrados)
python generador_configuracion_lote/generar_configs.py --clean-json

# 3. Generación omitiendo el cifrado Fernet (solo archivos .json)
python generador_configuracion_lote/generar_configs.py --skip-encrypt
```
