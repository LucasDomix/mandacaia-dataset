import os
import shutil
import csv
from datetime import datetime
import json

# Diretorio base dos dados. Configure pela variavel de ambiente MQ_DATA_DIR
# ou edite o valor padrao abaixo. Nenhum caminho absoluto fica fixo no codigo.
DATA_DIR = os.environ.get("MQ_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))


# Configurações
MY_PHOTOS_DIR = os.path.join(DATA_DIR, "minhas_fotos_mandacaia")
CURATED_DIR = "clip_curated_v2/approved"  # Imagens já curadas
OUTPUT_DIR = "dataset_final"  # Dataset combinado
METADATA_FILE = "dataset_metadata.csv"

class DatasetMerger:
    def __init__(self):
        self.metadata = []
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def add_inaturalist_images(self, curated_dir):
        """Adiciona imagens do iNaturalist já curadas"""
        print("\nAdicionando imagens do iNaturalist...")

        # Tentar carregar metadados existentes do iNaturalist
        inaturalist_meta_path = "melipona_quadrifasciata_images/image_metadata.csv"
        inaturalist_meta = {}

        if os.path.exists(inaturalist_meta_path):
            with open(inaturalist_meta_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    inaturalist_meta[row['filename']] = row
            print(f"  Metadados do iNaturalist carregados")

        # Copiar imagens curadas
        count = 0
        for filename in os.listdir(curated_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                src = os.path.join(curated_dir, filename)
                dst = os.path.join(OUTPUT_DIR, filename)

                shutil.copy2(src, dst)

                # Adicionar metadados
                if filename in inaturalist_meta:
                    meta = inaturalist_meta[filename]
                    self.metadata.append({
                        'filename': filename,
                        'source': 'iNaturalist',
                        'photographer': meta.get('photographer', 'Unknown'),
                        'license': meta.get('license', 'Unknown'),
                        'location': meta.get('location', 'Unknown'),
                        'observed_on': meta.get('observed_on', 'Unknown'),
                        'quality_grade': meta.get('quality_grade', 'Unknown'),
                        'url': meta.get('url', ''),
                        'notes': 'Curated with CLIP'
                    })
                else:
                    # Sem metadados detalhados
                    self.metadata.append({
                        'filename': filename,
                        'source': 'iNaturalist',
                        'photographer': 'Unknown',
                        'license': 'Unknown',
                        'location': 'Unknown',
                        'observed_on': 'Unknown',
                        'quality_grade': 'Unknown',
                        'url': '',
                        'notes': 'Curated with CLIP, original metadata not found'
                    })

                count += 1

        print(f"  {count} imagens do iNaturalist adicionadas")
        return count

    def add_my_photos(self, my_photos_dir, author_name, license_type="CC-BY-NC-4.0",
                      location="", notes=""):
        """Adiciona suas próprias fotos com metadados personalizados"""
        print("\nAdicionando suas fotos...")

        if not os.path.exists(my_photos_dir):
            print(f"   Pasta não encontrada: {my_photos_dir}")
            print(f"  Crie a pasta primeiro:")
            print(f"     mkdir '{my_photos_dir}'")
            return 0

        # Verificar se há imagens
        image_files = [f for f in os.listdir(my_photos_dir)
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if not image_files:
            print(f"   Nenhuma imagem encontrada em: {my_photos_dir}")
            print(f"  Formatos aceitos: .jpg, .jpeg, .png")
            return 0

        count = 0
        today = datetime.now().strftime('%Y-%m-%d')

        for filename in image_files:
            src = os.path.join(my_photos_dir, filename)

            # Renomear para evitar conflitos
            new_filename = f"own_{filename}"
            dst = os.path.join(OUTPUT_DIR, new_filename)

            shutil.copy2(src, dst)

            # Adicionar metadados personalizados
            self.metadata.append({
                'filename': new_filename,
                'source': 'Own Collection',
                'photographer': author_name,
                'license': license_type,
                'location': location,
                'observed_on': today,
                'quality_grade': 'research',
                'url': '',
                'notes': notes or 'Personal photograph for research'
            })

            count += 1

        print(f"  {count} fotos pessoais adicionadas")
        return count

    def save_metadata(self, output_dir):
        """Salva metadados em CSV e JSON"""

        # CSV para fácil leitura
        csv_path = os.path.join(output_dir, METADATA_FILE)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if self.metadata:
                fieldnames = self.metadata[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.metadata)

        print(f"\nMetadados salvos em: {csv_path}")

        # JSON para uso programático
        json_path = os.path.join(output_dir, "dataset_metadata.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

        print(f"Metadados salvos em: {json_path}")

    def generate_report(self):
        """Gera relatório do dataset final"""

        total = len(self.metadata)
        by_source = {}
        by_license = {}

        for item in self.metadata:
            source = item['source']
            license_type = item['license']

            by_source[source] = by_source.get(source, 0) + 1
            by_license[license_type] = by_license.get(license_type, 0) + 1

        print(f"\n{'='*70}")
        print("RELATÓRIO DO DATASET FINAL")
        print(f"{'='*70}")
        print(f"\nTotal de imagens: {total}")
        print(f"\nPor fonte:")
        for source, count in by_source.items():
            print(f"   • {source}: {count} ({count/total*100:.1f}%)")

        print(f"\nPor licença:")
        for license_type, count in by_license.items():
            print(f"   • {license_type}: {count} ({count/total*100:.1f}%)")

        print(f"\nLocalização: {OUTPUT_DIR}/")
        print(f"{'='*70}")

        # Salvar relatório
        report_path = os.path.join(OUTPUT_DIR, "dataset_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"DATASET FINAL - Melipona quadrifasciata\n")
            f.write(f"{'='*70}\n\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {total} imagens\n\n")
            f.write(f"Fontes:\n")
            for source, count in by_source.items():
                f.write(f"  - {source}: {count} ({count/total*100:.1f}%)\n")
            f.write(f"\nLicenças:\n")
            for license_type, count in by_license.items():
                f.write(f"  - {license_type}: {count} ({count/total*100:.1f}%)\n")

if __name__ == "__main__":
    print("="*70)
    print("COMBINAÇÃO DE DATASET - iNaturalist + Fotos Próprias")
    print("="*70)
    print(f"\nPasta das suas fotos: {MY_PHOTOS_DIR}")

    merger = DatasetMerger()

    # 1. Adicionar imagens do iNaturalist
    inaturalist_count = merger.add_inaturalist_images(CURATED_DIR)

    # 2. Adicionar suas fotos
    print("\n" + "="*70)
    print("CONFIGURAÇÃO DAS SUAS FOTOS")
    print("="*70)
    print("\nPreencha as informações:")

    author_name = input("\nSeu nome completo [Lucas Dominguez Cordeiro]: ").strip() or "Lucas Dominguez Cordeiro"

    print("\nLicença recomendada para dataset público:")
    print("  1. CC-BY-4.0 (permite uso comercial com atribuição)")
    print("  2. CC-BY-NC-4.0 (não comercial com atribuição)")
    print("  3. CC0 (domínio público)")

    license_choice = input("\nEscolha (1/2/3) [1]: ").strip() or "1"
    license_map = {
        "1": "CC-BY-4.0",
        "2": "CC-BY-NC-4.0",
        "3": "CC0"
    }
    license_type = license_map.get(license_choice, "CC-BY-4.0")

    location = input("\nLocalização das fotos [Mafra, SC]: ").strip() or "Mafra, SC"
    notes = input("\nNotas adicionais (opcional): ").strip()

    my_photos_count = merger.add_my_photos(
        MY_PHOTOS_DIR,
        author_name,
        license_type,
        location,
        notes
    )

    # 3. Salvar metadados
    if inaturalist_count > 0 or my_photos_count > 0:
        merger.save_metadata(OUTPUT_DIR)
        merger.generate_report()
    else:
        print("\n Nenhuma imagem foi adicionada!")

    print(f"\n{'='*70}")
    print("PRÓXIMOS PASSOS")
    print(f"{'='*70}")
    print(f"\n1. Dataset combinado em: {OUTPUT_DIR}/")
    print(f"\n2. Metadados completos em:")
    print(f"   - dataset_metadata.csv (para visualização)")
    print(f"   - dataset_metadata.json (para programas)")
    print(f"\n3.  Agora você pode:")
    print(f"   - Fazer anotação YOLO dessas imagens")
    print(f"   - Citar corretamente os autores na dissertação")
    print(f"   - Publicar dataset com metadados completos")
    print(f"\n4. Para publicar, inclua:")
    print(f"   - README.md descrevendo o dataset")
    print(f"   - dataset_metadata.csv para atribuições")
    print(f"   - LICENSE.txt com termos de uso")
    print(f"{'='*70}")
