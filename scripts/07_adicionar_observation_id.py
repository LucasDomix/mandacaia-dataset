import pandas as pd
import os

# Diretorio base dos dados. Configure pela variavel de ambiente MQ_DATA_DIR
# ou edite o valor padrao abaixo. Nenhum caminho absoluto fica fixo no codigo.
DATA_DIR = os.environ.get("MQ_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

CSV_PATH = os.path.join(DATA_DIR, "dataset_final/dataset_metadata.csv")
OUTPUT_PATH = os.path.join(DATA_DIR, "dataset_final/dataset_metadata_fixed.csv")

# Ler CSV
print("Lendo CSV existente...")
df = pd.read_csv(CSV_PATH)

print(f"  Total de registros: {len(df)}")
print(f"  Colunas existentes: {list(df.columns)}")

# Adicionar observation_id
print("\nAdicionando coluna observation_id...")

def create_observation_id(row):
    """Cria observation_id baseado na fonte da imagem"""

    # Se for do iNaturalist e tiver URL, extrair ID
    if row['source'] == 'iNaturalist' and pd.notna(row.get('url', '')):
        url = str(row['url'])
        # URL típica: https://www.inaturalist.org/observations/123456
        if '/observations/' in url:
            try:
                obs_id = url.split('/observations/')[-1].split('/')[0].split('?')[0]
                return f"inat_{obs_id}"
            except:
                pass

    # Se for foto própria, usar filename como ID único
    if row['source'] == 'Own Collection':
        return row['filename']

    # Fallback: usar filename como ID
    return row['filename']

df['observation_id'] = df.apply(create_observation_id, axis=1)

# Verificar resultados
n_unique = df['observation_id'].nunique()
n_total = len(df)

print(f"\nColuna criada:")
print(f"  Total de imagens: {n_total}")
print(f"  Observações únicas: {n_unique}")
print(f"  Média de fotos por observação: {n_total/n_unique:.1f}")

# Mostrar amostra
print(f"\nAmostra:")
print(df[['filename', 'source', 'observation_id']].head(10).to_string())

# Salvar
df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
print(f"\nCSV corrigido salvo em:")
print(f"  {OUTPUT_PATH}")

# Substituir original
backup_path = CSV_PATH.replace('.csv', '_backup.csv')
import shutil


shutil.copy2(CSV_PATH, backup_path)
shutil.copy2(OUTPUT_PATH, CSV_PATH)

print(f"\nBackup do original em:")
print(f"  {backup_path}")
print(f"\nCSV original atualizado com observation_id!")
print(f"\nAgora pode executar: python split_dataset_adv.py")
