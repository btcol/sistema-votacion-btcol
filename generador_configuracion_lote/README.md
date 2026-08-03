# 🛠️ Orquestador de Configuración Masiva, Cifrado Fernet & Ofuscación PyArmor
### *Módulo de Despliegue Seguro de Terminales Electorales BTCOL*

---

## 📖 Descripción General

El módulo `generador_configuracion_lote` es el componente centralizado de aprovisionamiento electoral. A partir de un archivo CSV consolidado de wallets (`wallets.csv`) y un archivo de parámetros globales (`config_global.md`), este orquestador realiza de forma completamente automatizada:

1. **Generación y Normalización de Entidades**: Identifica candidatos y mesas electorales asignando puertos, endpoints y parámetros.
2. **Cifrado Criptográfico Fernet (AES-128-CBC)**: Cifra todos los archivos de configuración (`candidatos.json.enc`, `mesa_config.json.enc`, `wallets.json.enc`).
3. **Aprovisionamiento Automático para Dashboards**: Genera y guarda automáticamente `data/wallets.json.enc` para el consumo del Dashboard de Monitoreo (`frontend/votos_dashboard.py`) y del Dashboard de Auditoría (`audit/auditoria_ln_votos.py`).
4. **Clonación y Personalización de Urnas**: Clona la plantilla base `mesa_code/` para cada mesa en `mesas_desplegadas/mesa_code<N>/` inyectándole sus archivos cifrados particulares.
5. **Inyección Dinámica de Claves y Ofuscación con PyArmor**: Inyecta la clave Fernet en `scripts/config.py` y compila el código fuente Python con **PyArmor 9**, blindando las terminales de votación contra manipulación física o ingeniería inversa.
6. **Eliminación Automática de Archivos Planos**: Borra por defecto los archivos `.json` en texto claro para evitar filtraciones de credenciales.

---

## 🔑 Gestión de la Clave Fernet

La clave criptográfica puede definirse en la variable `CLAVE_FERNET` al inicio de `generar_configs.py` o pasarse mediante el argumento CLI `--fernet-key`.

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
    ├── config_global.md             <-- Parámetros globales (URL LNbits Tor, sats_per_vote)
    ├── wallets.csv                  <-- CSV de carteras exportadas
    ├── generar_configs.py           <-- Script orquestador
    ├── candidatos.json.enc          <-- Lista consolidada de candidatos cifrada
    ├── wallets.json.enc             <-- Copia cifrada de respaldo
    └── mesas_desplegadas/
        ├── mesa_code1/              <-- Terminal de Mesa 1 (Código ofuscado con PyArmor)
        │   ├── app_web_mesa.py
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
| `--config-md` | Ruta | `config_global.md` | Archivo Markdown con `url_lnbits` y `sats_per_vote`. |
| `--fernet-key` | String Base64 | `None` (Usa const) | Clave Fernet de 44 caracteres para cifrar las configuraciones. |
| `--keep-json` | Flag | `False` | Conserva los archivos `.json` planos en disco (solo desarrollo). |
| `--skip-obfuscate` | Flag | `False` | Omite la ofuscación con PyArmor (útil para depuración). |
| `--out-dir` | Ruta | `.` | Directorio de salida para los archivos consolidados. |

---

## 🚀 Ejemplos de Uso

### 1. Despliegue Estándar de Producción (Recomendado)
```bash
python3 generador_configuracion_lote/generar_configs.py --fernet-key "StxCyZIWBe4dvdrp14Wd3-xMNLJyQfJMBjLL2A0VbfE="
```

### 2. Modo de Desarrollo / Depuración (Mantiene JSONs y sin ofuscar)
```bash
python3 generador_configuracion_lote/generar_configs.py --keep-json --skip-obfuscate
```

---

## 🛡️ Medidas de Seguridad de las Terminales Desplegadas

1. **Inaccesibilidad de Credenciales**: Cada mesa en `mesas_desplegadas/mesa_code<N>` solo contiene archivos `.json.enc` binarios. No existen archivos `.env` ni JSONs legibles.
2. **Protección del Bytecode**: El código Python es procesado con PyArmor, evitando que la clave o la lógica interna de validación de cédulas y pagos pueda ser adulterada localmente.
3. **Aislamiento por Mesa**: Cada carpeta de mesa solo conoce su propia `Admin Key` y no tiene acceso a las credenciales de otras mesas.

