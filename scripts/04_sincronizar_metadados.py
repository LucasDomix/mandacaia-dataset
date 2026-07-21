import csv
import os

# Configurações
IMAGE_DIR = "melipona_quadrifasciata_images"
METADATA_FILE = "image_metadata.csv"
OUTPUT_FILE = "image_metadata_curated.csv"

def clean_metadata(image_dir, metadata_file, output_file):
    """Remove do CSV as linhas de imagens que foram deletadas"""

    # Verificar se arquivos existem
    metadata_path = os.path.join(image_dir, metadata_file)
    output_path = os.path.join(image_dir, output_file)

    if not os.path.exists(metadata_path):
        print(f"Arquivo não encontrado: {metadata_path}")
        return

    # Listar arquivos de imagem existentes na pasta
    existing_images = set()
    for file in os.listdir(image_dir):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            existing_images.add(file)

    print(f"Imagens encontradas na pasta: {len(existing_images)}")

    # Ler CSV original
    with open(metadata_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    print(f"Registros no CSV original: {len(all_rows)}")

    # Filtrar apenas linhas com imagens existentes
    curated_rows = []
    removed_count = 0

    for row in all_rows:
        filename = row.get('filename', '')
        if filename in existing_images:
            curated_rows.append(row)
        else:
            removed_count += 1

    # Salvar CSV limpo
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(curated_rows)

    # Estatísticas
    print(f"\n{'='*60}")
    print("RESULTADO DA LIMPEZA")
    print(f"{'='*60}")
    print(f"Registros mantidos: {len(curated_rows)}")
    print(f"Registros removidos: {removed_count}")
    print(f"Taxa de aprovação: {len(curated_rows)/len(all_rows)*100:.1f}%")
    print(f"\nCSV curado salvo em: {output_path}")
    print(f"{'='*60}")

    # Opcional: substituir arquivo original
    print(f"\n Para substituir o arquivo original, execute:")
    print(f"   mv {output_path} {metadata_path}")

if __name__ == "__main__":
    print("=" * 60)
    print("LIMPEZA DE METADADOS - iNaturalist")
    print("=" * 60)
    print("\nEste script mantém no CSV apenas imagens que ainda existem na pasta")
    print("\n")

    clean_metadata(IMAGE_DIR, METADATA_FILE, OUTPUT_FILE)
