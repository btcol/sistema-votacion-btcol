# ⚙️ Parámetros Globales de Configuración (Plantilla de Ejemplo)

Este archivo contiene la plantilla de configuración global requerida por el sistema de votación BTCOL (`generar_configs.py`, `votos_dashboard.py` y `auditoria_ln_votos.py`).

> [!NOTE]
> Para usar en tu despliegue local, copia este archivo como `config_global.md` y configura los valores correspondientes:
> ```bash
> cp generador_configuracion_lote/config_global.example.md generador_configuracion_lote/config_global.md
> ```

---

## 📋 Parámetros

- **url_lnbits**: <http://ejemplo_servidor_lnbits_o_onion_address.onion>
- **sats_per_vote**: 1
- **clave_fernet**: <TU_CLAVE_FERNET_BASE64_AQUI=>

---

### 🔑 ¿Cómo generar una nueva Clave Fernet aleatoria?
Ejecuta el siguiente comando en la terminal:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
