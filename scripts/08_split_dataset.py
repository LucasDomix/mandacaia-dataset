import os
import shutil
import pandas as pd
import numpy as np
import random
from collections import defaultdict
from sklearn.cluster import KMeans

# Diretorio base dos dados. Configure pela variavel de ambiente MQ_DATA_DIR
# ou edite o valor padrao abaixo. Nenhum caminho absoluto fica fixo no codigo.
DATA_DIR = os.environ.get("MQ_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))


# Tentar importar CLIP
try:
    import torch
    import clip
    from PIL import Image
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    print("CLIP não detectado. A divisão será aleatória (mas respeitando IDs).")

# --- CONFIGURAÇÕES ---
CSV_PATH = os.path.join(DATA_DIR, "dataset_final/dataset_metadata.csv")       # Seu CSV com 'observation_id'
INPUT_DIR = os.path.join(DATA_DIR, "dataset_final")  # Pasta das imagens (já limpas)
OUTPUT_DIR = os.path.join(DATA_DIR, "dataset_final_split")            # Onde vai salvar
SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
N_CLUSTERS = 5  # Menos clusters pois agruparemos por ID, não por imagem
RANDOM_SEED = 42

def load_metadata_groups(csv_path, input_dir):
    """Agrupa imagens por observation_id verificando se existem no disco"""
    df = pd.read_csv(csv_path)
    available_files = set(os.listdir(input_dir))

    groups = defaultdict(list)
    files_without_metadata = list(available_files)

    # 1. Agrupar via CSV
    for _, row in df.iterrows():
        fname = row['filename']
        oid = row['observation_id']

        if fname in available_files:
            groups[oid].append(fname)
            if fname in files_without_metadata:
                files_without_metadata.remove(fname)

    # 2. Tratar órfãos (arquivos na pasta que não estão no CSV)
    # Criamos um ID fictício único para cada um para não perder dados
    for i, fname in enumerate(files_without_metadata):
        fake_id = f"orphan_{i}"
        groups[fake_id].append(fname)

    return groups

def get_group_embeddings(groups, input_dir, model, preprocess, device):
    """Calcula o embedding médio de cada GRUPO de fotos"""
    group_embeddings = {}
    print(f"Calculando embeddings para {len(groups)} observações...")

    for oid, filenames in groups.items():
        # Pega a primeira imagem do grupo (ou média de todas se quiser ser muito preciso)
        # Para velocidade, pegar a primeira geralmente basta para definir o "estilo" da observação
        img_path = os.path.join(input_dir, filenames[0])

        try:
            image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
            with torch.no_grad():
                emb = model.encode_image(image)
            group_embeddings[oid] = emb.cpu().numpy().flatten()
        except Exception as e:
            print(f"  Erro ao ler grupo {oid}: {e}")
            # Cria embedding zerado para não quebrar
            group_embeddings[oid] = np.zeros(512)

    return group_embeddings

def main():
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # 1. Carregar Dados
    print("Lendo arquivos e metadados...")
    groups = load_metadata_groups(CSV_PATH, INPUT_DIR)
    total_images = sum(len(v) for v in groups.values())
    print(f"   Total: {total_images} imagens em {len(groups)} observações únicas.")

    # 2. Clusterização Inteligente (se CLIP disponível)
    group_ids = list(groups.keys())

    if CLIP_AVAILABLE:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Carregando CLIP ({device})...")
        model, preprocess = clip.load("ViT-B/32", device=device)

        # Gera embedding para cada GRUPO (Observation ID)
        embeddings_dict = get_group_embeddings(groups, INPUT_DIR, model, preprocess, device)
        embeddings_matrix = np.array([embeddings_dict[oid] for oid in group_ids])

        # Clusteriza as OBSERVAÇÕES
        print(f"Agrupando observações em {N_CLUSTERS} clusters visuais...")
        kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_SEED)
        labels = kmeans.fit_predict(embeddings_matrix)

        # Organiza: { Cluster_0: [ID_1, ID_5], Cluster_1: [ID_2, ID_3] ... }
        clustered_groups = defaultdict(list)
        for oid, label in zip(group_ids, labels):
            clustered_groups[label].append(oid)
    else:
        # Fallback se não tiver CLIP: tudo num único cluster gigante
        clustered_groups = {0: group_ids}

    # 3. Divisão Estratificada
    final_split = {"train": [], "val": [], "test": []}

    print(" Realizando divisão estratificada...")

    for cluster_id, oids in clustered_groups.items():
        random.shuffle(oids) # Embaralha dentro do cluster

        n_total = len(oids)
        n_train = int(n_total * SPLIT_RATIOS["train"])
        n_val = int(n_total * SPLIT_RATIOS["val"])
        # O resto vai para test para garantir soma 100%

        final_split["train"].extend(oids[:n_train])
        final_split["val"].extend(oids[n_train : n_train+n_val])
        final_split["test"].extend(oids[n_train+n_val:])

    # 4. Mover Arquivos
    print(f"Movendo arquivos para {OUTPUT_DIR}...")

    stats = {"train": 0, "val": 0, "test": 0}

    for split_name, oids in final_split.items():
        split_dir = os.path.join(OUTPUT_DIR, split_name)
        os.makedirs(split_dir, exist_ok=True)

        for oid in oids:
            files = groups[oid]
            for f in files:
                src = os.path.join(INPUT_DIR, f)
                dst = os.path.join(split_dir, f)
                shutil.copy2(src, dst)
                stats[split_name] += 1

    # 5. Relatório
    print("\n" + "="*50)
    print("DATASET PRONTO PARA ROBOFLOW")
    print("="*50)
    print(f"Total Imagens: {total_images}")
    print(f"Train: {stats['train']} ({stats['train']/total_images:.1%}) - Observações inteiras")
    print(f"Val:   {stats['val']} ({stats['val']/total_images:.1%}) - Observações inteiras")
    print(f"Test:  {stats['test']} ({stats['test']/total_images:.1%}) - Observações inteiras")
    print("\nO Vazamento de Dados (Data Leakage) foi eliminado.")
    print(f"As imagens estão em: {OUTPUT_DIR}/")

if __name__ == "__main__":
    if os.path.exists(CSV_PATH) and os.path.exists(INPUT_DIR):
        main()
    else:
        print("Verifique os caminhos do CSV e da pasta de imagens no início do script.")