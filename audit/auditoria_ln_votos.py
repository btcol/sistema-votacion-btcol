"""
 Este script audita la base de datos de LNbits para verificar que los votos
 registrados en la base de datos coinciden con los votos registrados en las wallets
 de LNbits, detecta votos que provienen de wallets no autorizadas y detecta votos
 que provienen de wallets autorizadas.

 Uso:
    python auditoria_ln_votos.py

"""
import json
import sqlite3
import pandas as pd
import re
from pathlib import Path

# Directorio raíz del proyecto (2 niveles arriba desde audit/)
BASE_DIR = Path(__file__).resolve().parent.parent  # audit/ -> raíz
DATA_DIR = BASE_DIR / 'data'

# Load wallets.json
with open(DATA_DIR / 'wallets.json', 'r') as f:
    wallets_data = json.load(f)

# Wallet info dict: wallet_id -> {'display_name': ..., 'type': 'mesa' or 'candidato'}
wallet_info = {}
for section in ['candidatos', 'mesas']:
    for key, info in wallets_data.get(section, {}).items():
        wid = info['wallet_id']
        wallet_info[wid] = {
            'display_name': info['display_name'],
            'type': 'candidato' if section == 'candidatos' else 'mesa'
        }

mesa_wallets = [wid for wid, info in wallet_info.items() if info['type'] == 'mesa']
candidato_wallets = [wid for wid, info in wallet_info.items() if info['type'] == 'candidato']

print("Mesa wallets:", len(mesa_wallets))
print("Candidato wallets:", len(candidato_wallets))

# Connect to DB
conn = sqlite3.connect(DATA_DIR / 'database.sqlite3')
query = """
SELECT wallet_id, amount, fee, memo, payment_hash
FROM apipayments 
ORDER BY time DESC
"""
df = pd.read_sql_query(query, conn)
conn.close()

# Add info columns
df['display_name'] = df['wallet_id'].map({k: v['display_name'] for k, v in wallet_info.items()})
df['authorized_wallet'] = df['wallet_id'].isin(list(wallet_info.keys()))
df['wallet_type'] = df['wallet_id'].map({k: v['type'] for k, v in wallet_info.items()})

# Selecciona las wallet_id almacenadas en mesa_wallets y muestra los valores en la columna memo y que la columna amount < 0
mesa_df = df[(df['wallet_id'].isin(mesa_wallets)) & (df['amount'] < 0)]
print("Votos registrados por mesas:")
print(mesa_df[['wallet_id', 'display_name', 'memo', 'payment_hash']].head(10))
print("\nTotal votos por mesa:")
print(mesa_df['display_name'].value_counts())

# Selecciona las wallet_id almacenadas en candidato_wallets y muestra los valores en la columna memo y que la columna amount > 0
candidato_df = df[(df['wallet_id'].isin(candidato_wallets)) & (df['amount'] > 0)]
print("\nVotos registrados por candidatos:")
print(candidato_df[['wallet_id', 'display_name', 'memo', 'payment_hash']].head(10))
print("\nTotal votos por candidato:")
print(candidato_df['display_name'].value_counts())

# Merge para encontrar no-matches usando 'memo'
merged = pd.merge(
    mesa_df, 
    candidato_df, 
    on='memo', 
    how='outer', 
    suffixes=('_mesa', '_candidato'),
    indicator=True
)

# Filas que NO hacen match (solo en una tabla)
no_match = merged[merged['_merge'] != 'both'].copy()
print(" ")
print("Transacciones sin match por memo:")
print(no_match[['memo', 'wallet_id_mesa', 'display_name_mesa', 
                'wallet_id_candidato', 'display_name_candidato', '_merge']])
"""
# Opcional: separar por origen
# solo_mesas = no_match[no_match['_merge'] == 'left_only'][['memo', 'wallet_id_mesa', 'display_name_mesa']]
solo_candidatos = no_match[no_match['_merge'] == 'right_only'][['memo', 'wallet_id_candidato', 'display_name_candidato']]

# print("\nSolo en mesas:")
# print(solo_mesas)
print("\nSolo en candidatos:")
print(solo_candidatos)"""


# Separar por origen CON payment_hash
#solo_mesas = no_match[no_match['_merge'] == 'left_only'][
#    ['memo', 'wallet_id_mesa', 'display_name_mesa', 'payment_hash_mesa']
#].rename(columns={'wallet_id_mesa': 'wallet_id', 'display_name_mesa': 'display_name', 
#                  'payment_hash_mesa': 'payment_hash'})

solo_candidatos = no_match[no_match['_merge'] == 'right_only'][
    ['memo', 'wallet_id_candidato', 'display_name_candidato', 'payment_hash_candidato']
].rename(columns={'wallet_id_candidato': 'wallet_id', 'display_name_candidato': 'display_name', 
                  'payment_hash_candidato': 'payment_hash'})

#print("\nSolo en mesas (con payment_hash):")
#print(solo_mesas)

print("\nSolo en candidatos (con payment_hash):")
print(solo_candidatos)
