import requests
import os
import time
import csv
from datetime import datetime

# Configurações
TAXON_IDS = [418697, 965825]  # M. quadrifasciata e M. q. quadrifasciata
OUTPUT_DIR = "melipona_quadrifasciata_images"
METADATA_FILE = "image_metadata.csv"

# Licenças aceitas (abertas e acadêmicas)
ACCEPTED_LICENSES = [
    "cc0",           # CC0 - Public Domain
    "cc-by",         # Creative Commons Attribution
    "cc-by-sa",      # Creative Commons Attribution-ShareAlike
    "cc-by-nc",      # Creative Commons Attribution-NonCommercial
    "cc-by-nc-sa"    # Creative Commons Attribution-NonCommercial-ShareAlike
]

# Criar diretório de saída
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Função para buscar observações via API
def get_observations(taxon_id, per_page=200, max_pages=50):
    """Busca observações do iNaturalist com fotos e licenças abertas"""
    observations = []
    base_url = "https://api.inaturalist.org/v1/observations"

    for page in range(1, max_pages + 1):
        params = {
            "taxon_id": taxon_id,
            "photos": "true",
            "photo_license": ",".join(ACCEPTED_LICENSES),
            "per_page": per_page,
            "page": page
        }

        print(f"Buscando página {page} para taxon {taxon_id}...")

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                print(f"Nenhum resultado na página {page}. Finalizando busca para taxon {taxon_id}.")
                break

            observations.extend(results)
            print(f"  {len(results)} observações encontradas")

            # Respeitar limite de taxa (60 req/min)
            time.sleep(1.2)

        except Exception as e:
            print(f"Erro na página {page}: {e}")
            break

    return observations

# Função para baixar imagens
def download_image(url, filename, max_retries=3):
    """Baixa uma imagem com retry"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Tentativa {attempt + 1} falhou, tentando novamente...")
                time.sleep(2)
            else:
                print(f"  Erro ao baixar {url}: {e}")
                return False
    return False

# Processar observações e baixar imagens
def process_observations(observations, taxon_name):
    """Processa observações e baixa imagens"""
    metadata = []
    downloaded_count = 0

    print(f"\nProcessando {len(observations)} observações de {taxon_name}...")

    for idx, obs in enumerate(observations, 1):
        obs_id = obs.get("id")
        photos = obs.get("photos", [])
        user = obs.get("user", {}).get("login", "unknown")
        license_code = obs.get("license_code", "no_license")
        location = obs.get("place_guess", "Unknown location")
        observed_on = obs.get("observed_on", "Unknown date")
        quality_grade = obs.get("quality_grade", "unknown")

        print(f"\n[{idx}/{len(observations)}] Observação {obs_id} - {len(photos)} foto(s)")

        for photo_idx, photo in enumerate(photos):
            photo_id = photo.get("id")
            photo_license = photo.get("license_code", license_code)

            # Verificar se tem licença aceita
            if photo_license not in ACCEPTED_LICENSES:
                print(f"  Foto {photo_id}: licença '{photo_license}' não aceita, pulando...")
                continue

            # URL da imagem em tamanho original
            image_url = photo.get("url", "").replace("square", "original")

            if not image_url:
                continue

            # Nome do arquivo
            filename = f"{taxon_name}_{obs_id}_{photo_id}_{photo_license}.jpg"
            filepath = os.path.join(OUTPUT_DIR, filename)

            # Baixar imagem
            if os.path.exists(filepath):
                print(f"  Foto {photo_id}: já existe, pulando...")
            else:
                print(f"  Baixando foto {photo_id} ({photo_license})...")
                if download_image(image_url, filepath):
                    downloaded_count += 1
                    print(f"    Salva: {filename}")

                # Delay entre downloads
                time.sleep(0.5)

            # Salvar metadados
            metadata.append({
                "filename": filename,
                "observation_id": obs_id,
                "photo_id": photo_id,
                "taxon_name": taxon_name,
                "license": photo_license,
                "photographer": photo.get("attribution", user),
                "location": location,
                "observed_on": observed_on,
                "quality_grade": quality_grade,
                "url": f"https://www.inaturalist.org/observations/{obs_id}"
            })

    return metadata, downloaded_count

# MAIN
if __name__ == "__main__":
    print("=" * 60)
    print("DOWNLOAD DE IMAGENS - iNaturalist")
    print("Melipona quadrifasciata (Mandaçaia)")
    print("=" * 60)
    print(f"\nLicenças aceitas: {', '.join(ACCEPTED_LICENSES)}")
    print(f"Diretório de saída: {OUTPUT_DIR}")

    all_metadata = []
    total_downloaded = 0

    # Processar cada taxon
    taxon_names = {
        418697: "melipona_quadrifasciata",
        965825: "melipona_quadrifasciata_quadrifasciata"
    }

    for taxon_id in TAXON_IDS:
        print(f"\n{'=' * 60}")
        print(f"Processando taxon_id: {taxon_id}")
        print(f"Nome: {taxon_names[taxon_id]}")
        print(f"{'=' * 60}")

        # Buscar observações
        observations = get_observations(taxon_id)
        print(f"\nTotal de observações encontradas: {len(observations)}")

        if observations:
            # Processar e baixar
            metadata, downloaded = process_observations(observations, taxon_names[taxon_id])
            all_metadata.extend(metadata)
            total_downloaded += downloaded

    # Salvar metadados em CSV
    if all_metadata:
        csv_path = os.path.join(OUTPUT_DIR, METADATA_FILE)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_metadata[0].keys())
            writer.writeheader()
            writer.writerows(all_metadata)
        print(f"\nMetadados salvos em: {csv_path}")

    # Resumo final
    print(f"\n{'=' * 60}")
    print("RESUMO")
    print(f"{'=' * 60}")
    print(f"Total de imagens baixadas: {total_downloaded}")
    print(f"Total de registros de metadados: {len(all_metadata)}")
    print(f"Diretório: {OUTPUT_DIR}")
    print(f"\nBaixe o script salvo como: download_inaturalist.py")
    print("Execute com: python download_inaturalist.py")
    print(f"{'=' * 60}")
