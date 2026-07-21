import os
import shutil
import imagehash
from PIL import Image
from collections import defaultdict

# --- CONFIGURAÇÕES ---
IMAGE_DIR = "melipona_quadrifasciata_images"  # Sua pasta de imagens
QUARANTINE_DIR = "_DUPLICATAS_PARA_REVISAO"   # Para onde vão as cópias
SIMILARITY_THRESHOLD = 4  # 0 = Idênticas. Aumente (6-8) para ser mais agressivo.

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_image_hash(filepath):
    """
    Calcula o dhash (Difference Hash).
    É melhor que o average_hash para detectar sequências de fotos (burst mode).
    """
    try:
        with Image.open(filepath) as img:
            # dhash é excelente para detectar pequenas mudanças de ângulo/iluminação
            return imagehash.dhash(img)
    except Exception as e:
        print(f"Erro ao ler {os.path.basename(filepath)}: {e}")
        return None

def find_and_move_duplicates(source_dir, quarantine_dir, threshold=5):
    """
    Encontra grupos de imagens similares e move as 'piores' (menores) para quarentena.
    """
    ensure_dir(quarantine_dir)

    # 1. Coletar imagens
    image_files = [
        os.path.join(source_dir, f) for f in os.listdir(source_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))
    ]
    image_files.sort() # Ordenar para consistência

    if not image_files:
        print("Nenhuma imagem encontrada na pasta.")
        return

    print(f"Analisando {len(image_files)} imagens com dHash (Threshold: {threshold})...")

    # 2. Calcular Hashes
    hashes = {}
    for filepath in image_files:
        h = get_image_hash(filepath)
        if h:
            hashes[filepath] = h

    # 3. Comparar e Agrupar
    # Marcamos imagens já processadas para não reavaliar
    processed = set()
    moved_count = 0

    # Lista de arquivos ordenada pelo tamanho (do maior para o menor)
    # Isso ajuda a garantir que, se não processado, preferimos manter o maior.
    sorted_files = sorted(hashes.keys(), key=lambda x: os.path.getsize(x), reverse=True)

    for i, file_a in enumerate(sorted_files):
        if file_a in processed:
            continue

        # Consideramos file_a como a "Original/Mestra" deste grupo (pois é a maior disponível)
        processed.add(file_a)

        duplicates_in_group = []

        # Comparar com todas as outras não processadas
        for file_b in sorted_files[i+1:]:
            if file_b in processed:
                continue

            # Calcular a diferença entre os hashes
            diff = hashes[file_a] - hashes[file_b]

            if diff <= threshold:
                duplicates_in_group.append(file_b)
                processed.add(file_b) # Marca como processada (será movida)

        # 4. Ação: Mover duplicatas encontradas
        if duplicates_in_group:
            print(f"\nGrupo encontrado (Manter: {os.path.basename(file_a)})")
            for dup in duplicates_in_group:
                filename = os.path.basename(dup)
                dest_path = os.path.join(quarantine_dir, filename)

                # Mover arquivo
                try:
                    shutil.move(dup, dest_path)
                    print(f"   sc--> Movido para quarentena: {filename} (Dif: {hashes[file_a] - hashes[dup]})")
                    moved_count += 1
                except Exception as e:
                    print(f"   Erro ao mover {filename}: {e}")

    print("-" * 50)
    print(f"Concluído!")
    print(f"   Imagens analisadas: {len(image_files)}")
    print(f"   Similares movidas: {moved_count}")
    print(f"   Verifique a pasta: {quarantine_dir}")

if __name__ == "__main__":
    # Verifica se a pasta existe antes de rodar
    if os.path.exists(IMAGE_DIR):
        find_and_move_duplicates(IMAGE_DIR, QUARANTINE_DIR, SIMILARITY_THRESHOLD)
    else:
        print(f"A pasta '{IMAGE_DIR}' não existe. Ajuste a variável IMAGE_DIR no código.")