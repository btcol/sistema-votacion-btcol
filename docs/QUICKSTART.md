# 🚀 Guía de Inicio Rápido - Sistema de Votación BTCOL (LNbits + Tor)

Guía paso a paso para configurar e implementar los 3 componentes del **Sistema de Votación BTCOL**: Urna Electoral Web, Dashboard de Monitoreo en Tiempo Real y Dashboard de Auditoría Electoral.

---

## ⚡ Inicio en 4 Pasos

### 1. Clona e Instala Dependencias
```bash
git clone <URL_DEL_REPOSITORIO>
cd sistema-votacion-btcol
pip install -r requirements.txt
```
*O ejecuta el script automatizado:* `bash setup.sh`

### 2. Configura `data/wallets.json` (Dashboard + Auditoría)
Copiar la plantilla predeterminada y colocar las **Invoice Keys** (modo lectura) de LNbits para candidatos y mesas:

```bash
cp wallets.example.json data/wallets.json
nano data/wallets.json
```

**Estructura de `data/wallets.json`:**
```json
{
  "settings": {
    "url_lnbits": "http://localhost:5050",
    "sats_per_vote": 100,
    "puerto_web": 5050,
    "show_sats_and_votes": true
  },
  "candidatos": [
    {
      "id": "candidato1",
      "display_name": "Candidato Bob",
      "invoice_key": "tu_invoice_key_aqui",
      "foto_local": "fotos/bob.png"
    }
  ],
  "mesas": [
    {
      "id": "mesa_001",
      "display_name": "Mesa Electoral 1",
      "invoice_key": "tu_invoice_key_aqui"
    }
  ]
}
```

### 3. Configura la Mesa Electoral (`mesa_code/data_mesa/`)
La Urna Electoral Web necesita la **Admin Key** de la Mesa (para emitir pagos de votos):

- **`mesa_code/data_mesa/mesa_config.json`**:
```json
{
  "mesa": {
    "id": "mesa_001",
    "nombre": "Mesa Electoral 1 - Sección Central",
    "api_key": "tu_admin_key_real_de_la_mesa",
    "wallet_id": "e44d7c4e43ef4eda9a09a147c35154ed",
    "url_lnbits": "http://localhost:5050",
    "monto_voto_sats": 100,
    "puerto_web": 2007
  }
}
```

- **`mesa_code/data_mesa/candidatos.json`**:
```json
{
  "candidatos": [
    {
      "id": "candidato1",
      "nombre": "Candidato Bob",
      "wallet_id": "ad16ae0649cb4d779f94fe2507aae2df",
      "api_key": "tu_invoice_key_real_de_bob",
      "foto_local": "fotos/bob.png"
    }
  ]
}
```

---

## 🖥️ Ejecución de los 3 Servicios

| Servicio | Comando de Inicio | Dirección Web | Puerto |
|----------|-------------------|---------------|--------|
| **Urna Electoral Web (Mesa)** | `python mesa_code/app_web_mesa.py` | `http://localhost:2007` | 2007 |
| **Dashboard de Monitoreo en Vivo** | `python frontend/votos_dashboard.py` | `http://localhost:5050` | 5050 |
| **Dashboard de Auditoría Electoral** | `python audit/auditoria_ln_votos.py` | `http://localhost:7070` | 7070 |

---

## 🔒 Consideraciones de Seguridad
- **`data/wallets.json`**: Utiliza únicamente **Invoice Keys** de LNbits. Es seguro para uso en Dashboards públicos.
- **`mesa_code/data_mesa/mesa_config.json`**: Contiene la **Admin Key** de la mesa. Mantener resguardado y asegurado en la Raspberry Pi / PC de la mesa. Nunca subir a repositorios públicos Git.
