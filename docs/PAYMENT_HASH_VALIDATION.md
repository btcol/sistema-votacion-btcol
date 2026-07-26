# 🔐 Trazabilidad Criptográfica: Validación mediante Payment Hash

Este documento detalla el mecanismo matemático y logístico utilizado por el módulo de Auditoría Electoral (Puerto 7070) para rastrear de forma unívoca e inalterable el ciclo de vida de un voto en la red Lightning.

## 📊 Principio de Funcionamiento

La red Lightning (y por extensión LNbits) genera una huella criptográfica SHA-256 de 64 caracteres denominada `payment_hash` al momento de emitir una factura (invoice). Dado que el sistema de votación BTCOL ejecuta transferencias internas entre carteras (wallets) del mismo nodo u operando bajo la misma infraestructura, el `payment_hash` funciona como el **cordón umbilical criptográfico** que vincula ineludiblemente la salida de los fondos con la entrada.

### Trazabilidad del Libro Mayor (Ledger)

Cuando se consolida un voto, la tabla unificada de pagos exhibe el siguiente patrón:

```
[Transacción Emparejada] Hash LNbits: 79001b54c...54112

- Fila A (Emisor):  -100 sats | Memo: "voto_candidato_01" | Wallet Origen (Mesa 1)
- Fila B (Receptor): +100 sats | Memo: "voto_candidato_01" | Wallet Destino (Candidato 01)
```

**Interpretación Criptográfica:**
1. La Mesa 1 registró un egreso exacto de satoshis autorizado.
2. El Candidato 01 registró un ingreso idéntico.
3. El `payment_hash` idéntico en ambas filas demuestra matemáticamente que la Transacción A y la Transacción B son la **misma transferencia atómica**.

## ⚙️ Algoritmo de Detección de Fraude y Auditoría

El módulo de auditoría (`audit/auditoria_ln_votos.py`) implementa un motor de validación cruzada que inspecciona el 100% de las transacciones procesadas, ejecutando el siguiente flujo de comprobación estricta para cada `payment_hash` descubierto:

1. **Agrupación Hash**: El sistema aísla todos los registros compartiendo un mismo `payment_hash`.
2. **Identificación de Polos**: El algoritmo identifica la transacción con monto negativo (Origen/Mesa) y la transacción con monto positivo (Destino/Candidato).
3. **Malla de Validación Restrictiva**:
   - `Autorización Origen`: Verifica si el ID de la wallet origen existe en el padrón `mesas` dentro de `data/wallets.json`.
   - `Autorización Destino`: Verifica si el ID de la wallet destino existe en el padrón `candidatos` dentro de `data/wallets.json`.
   - `Simetría de Montos`: Garantiza que el valor egresado y el ingresado coincidan exactamente.
   - `Estado Transaccional`: Confirma que el estado en la red LNbits indique `status: paid` de forma irreversible.
4. **Emisión de Veredicto**:
   - Si la malla pasa con éxito: Se emite un certificado de **Voto Válido** y se proyecta en la matriz origen/destino.
   - Si alguna regla fracasa (ej. ingreso sin egreso rastreable, origen no autorizado, alteración de memo): El voto es flagrado y reportado en tiempo real como **Transacción Irregular (Posible Fraude)**.

## 🚨 Vectores de Ataque Mitigados

Gracias al aislamiento criptográfico del `payment_hash`, la plataforma es inmune a las siguientes tipologías de ataque electoral:

- **Inyección Externa de Votos (Fondos Fantasma)**: Si un actor malicioso o donante externo transfiere fondos directamente a la billetera de un candidato intentando engrosar artificialmente su número de votos, el algoritmo detectará un ingreso `+X sats` carente de una transacción de egreso `-X sats` proveniente de una Mesa autorizada.
- **Intercepción y Desvío**: Resulta imposible alterar el destinatario de un voto en tránsito, ya que esto rompería la confirmación del nodo o generaría `payment_hashes` desparejados en el árbol de transacciones.
- **Suplantación de Mesas Electorales**: Si un nodo comprometido intenta emitir votos a favor de un candidato, la auditoría cruzará el origen del hash contra el registro centralizado de firmas admitidas y descartará los sufragios apócrifos de forma expedita.

## 📈 Conclusión Arquitectónica

La implementación de la auditoría basada en validación cruzada del `payment_hash` provee una garantía matemática que supera sustancialmente los esquemas de bases de datos tradicionales, permitiendo detectar vulneraciones o adulteraciones incluso si la red perimetral o un componente del sistema operativo llegase a verse comprometido temporalmente.
