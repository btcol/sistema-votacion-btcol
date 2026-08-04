# 🛠️ Orquestador de Configuración Masiva, Cifrado Fernet & Ofuscación PyArmor
### *Módulo de Despliegue Seguro de Terminales Electorales BTCOL*

---

## 📖 Descripción General

El módulo `generador_configuracion_lote` es el componente centralizado de aprovisionamiento electoral. A partir de un archivo CSV consolidado de wallets (`wallets.csv`) y un archivo de parámetros globales (`config_global.md`), este orquestador realiza de forma completamente automatizada:

1. **Generación y Normalización de Entidades**: Identifica candidatos y mesas electorales asignando puertos, endpoints y parámetros.
2. **Cifrado Criptográfico Fernet (AES-128-CBC)**: Cifra todos los archivos de configuración (`candidatos.json.enc`, `mesa_config.json.enc`, `wallets.json.enc`).
3. **Aprovisionamiento Automático para Dashboards**: Genera y guarda automáticamente `data/wallets.json.enc` para el consumo del Dashboard de Monitoreo (`frontend/votos_dashboard.py`) y del Dashboard de Auditoría (`audit/auditoria_ln_votos.py`).
4. **Clonación y Personalización de Urnas**: Clona la plantilla base `mesa_code/` para cada mesa en `mesas_desplegadas/mesa_code<N>/` inyectándole sus archivos cifrados particulares.
5. **Inyección Dinámica de Claves y Ofuscación con PyArmor**: Inyecta la clave Fernet en `scripts/config.py` y compila el código fuente Python (`app_web_mesa.py`, `app_desktop.py`, `scripts/` e `impresora/`) con **PyArmor 9**, blindando las terminales de votación contra manipulación física o ingeniería inversa de los algoritmos de comprobante PDF y metadatos forenses.
6. **Eliminación Automática de Archivos Planos**: Borra por defecto los archivos `.json` en texto claro para evitar filtraciones de credenciales.

---

## 🔑 Gestión Segura de la Clave Fernet

La clave criptográfica se resuelve automáticamente siguiendo la siguiente jerarquía de precedencia (evitando quemar secretos en el código fuente):

1. **Parámetro CLI**: `--fernet-key "TU_CLAVE_BASE64="`
2. **Variable de Entorno**: `export FERNET_KEY="TU_CLAVE_BASE64="`
3. **Archivo de Configuración Global**: Campo `clave_fernet` dentro de `generador_configuracion_lote/config_global.md`

### Generar una nueva clave segura y aleatoria:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 📁 Estructura del Módulo y Salida Generada

```
sistema-votacion-btcol/
├── data/
│   └── wallets.json.enc              <-- Archivo cifrado de monitoreo global
│
└── generador_configuracion_lote/
    ├── config_global.md             <-- Parámetros globales locales (URL LNbits Tor, sats_per_vote, clave_fernet) [Ignorado en Git]
    ├── config_global.example.md     <-- Plantilla pública de parámetros globales
    ├── wallets.csv                  <-- CSV de carteras exportadas [Ignorado en Git]
    ├── wallets.example.csv          <-- Plantilla de ejemplo con formato esperado
    ├── generar_configs.py           <-- Script orquestador
    ├── candidatos.json.enc          <-- Lista consolidada de candidatos cifrada
    ├── wallets.json.enc             <-- Copia cifrada de respaldo
    └── mesas_desplegadas/
        ├── mesa_code1/              <-- Terminal de Mesa 1 (Código ofuscado con PyArmor: app_web, scripts e impresora)
        │   ├── app_web_mesa.py
        │   ├── impresora/            <-- Generador de PDF y cifrado de cédula (Ofuscado)
        │   ├── scripts/              <-- Controladores de DB y Fernet (Ofuscado)
        │   ├── pyarmor_runtime_000000/
        │   └── data_mesa/
        │       ├── candidatos.json.enc
        │       └── mesa_config.json.enc
        ├── mesa_code2/
        └── mesa_code3/
```

---

## ⚙️ Opciones de Línea de Comandos (`generar_configs.py`)

| Argumento | Tipo | Por Defecto | Descripción |
|---|---|---|---|
| `--csv` | Ruta | `wallets.csv` | Ruta al archivo CSV con las wallets exportadas. |
| `--config-md` | Ruta | `config_global.md` | Archivo Markdown con `url_lnbits`, `sats_per_vote` y `clave_fernet`. |
| `--fernet-key` | String Base64 | `None` (Usa config_global.md / FERNET_KEY) | Clave Fernet personalizada de 44 caracteres en Base64. |
| `--keep-json` | Flag | `False` | Conserva los archivos `.json` planos en disco (solo desarrollo). |
| `--skip-obfuscate` | Flag | `False` | Omite la ofuscación con PyArmor (útil para depuración). |
| `--output-dir` | Ruta | `.` | Directorio de salida para los archivos consolidados. |

---

## 🚀 Ejemplos de Uso

### 1. Despliegue Estándar de Producción (Leyendo `config_global.md`)
```bash
# Configurar parámetros en config_global.md a partir del ejemplo
cp generador_configuracion_lote/config_global.example.md generador_configuracion_lote/config_global.md

# Ejecutar orquestador
python3 generador_configuracion_lote/generar_configs.py
```

### 2. Despliegue pasando clave explícita por CLI
```bash
python3 generador_configuracion_lote/generar_configs.py --fernet-key "StxCyZIWBe4dvdrp14Wd3-xMNLJyQfJMBjLL2A0VbfE="
```

### 3. Modo de Desarrollo / Depuración (Mantiene JSONs y sin ofuscar)
```bash
python3 generador_configuracion_lote/generar_configs.py --keep-json --skip-obfuscate
```

---

## 🛡️ Medidas de Seguridad de las Terminales Desplegadas

1. **Inaccesibilidad de Credenciales**: Cada mesa en `mesas_desplegadas/mesa_code<N>` solo contiene archivos `.json.enc` binarios. No existen archivos `.env` ni JSONs legibles.
2. **Protección del Bytecode**: El código Python es procesado con PyArmor, evitando que la clave o la lógica interna de validación de cédulas y pagos pueda ser adulterada localmente.
3. **Aislamiento por Mesa**: Cada carpeta de mesa solo conoce su propia `Admin Key` y no tiene acceso a las credenciales de otras mesas.

