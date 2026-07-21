import os
import torch
import clip
from PIL import Image
import numpy as np
from tqdm import tqdm
import json
import imagehash
from collections import defaultdict

# Configurações
IMAGE_DIR = "melipona_quadrifasciata_images"
OUTPUT_DIR = "clip_curated_v2"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Prompts SIMPLIFICADOS e mais inclusivos
POSITIVE_PROMPTS = [
    "a photo of a bee",
    "a bee insect",
    "a small bee",
    "an insect on a flower",
    "a flying insect",
    "a bee close up",
    "bees on hive"
]

# Apenas rejeitar coisas MUITO óbvias
NEGATIVE_PROMPTS = [
    "completely black image",
    "completely white image",
    "text document",
    "screenshot",
    "cartoon drawing",
    "no insects visible"
]

# Thresholds MUITO permissivos
MIN_POSITIVE_SCORE = 0.15  # Bem mais baixo
MAX_NEGATIVE_SCORE = 0.30  # Bem mais alto

# Detecção de duplicatas (manter)
DUPLICATE_SIMILARITY_THRESHOLD = 0.98
PERCEPTUAL_HASH_THRESHOLD = 5

class CLIPCurator:
    def __init__(self, image_dir, output_dir):
        self.image_dir = image_dir
        self.output_dir = output_dir
        self.approved_dir = os.path.join(output_dir, "approved")
        self.rejected_dir = os.path.join(output_dir, "rejected")
        self.duplicates_dir = os.path.join(output_dir, "duplicates")

        os.makedirs(self.approved_dir, exist_ok=True)
        os.makedirs(self.rejected_dir, exist_ok=True)
        os.makedirs(self.duplicates_dir, exist_ok=True)

        print(f"\nCarregando modelo CLIP em {DEVICE}...")
        self.model, self.preprocess = clip.load("ViT-B/32", device=DEVICE)
        print(f"Modelo CLIP carregado com sucesso em {DEVICE.upper()}!")

        self.stats = {
            "total": 0,
            "approved": 0,
            "rejected_low_relevance": 0,
            "rejected_negative_match": 0,
            "rejected_duplicate": 0
        }

        self.image_embeddings = {}
        self.perceptual_hashes = {}

    def encode_prompts(self, prompts):
        """Codifica prompts de texto em embeddings"""
        text_tokens = clip.tokenize(prompts).to(DEVICE)
        with torch.no_grad():
            text_features = self.model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features

    def calculate_image_embedding(self, img_path):
        """Calcula embedding CLIP da imagem"""
        try:
            image = Image.open(img_path).convert('RGB')
            image_input = self.preprocess(image).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)

            return image_features.cpu().numpy()[0]
        except Exception as e:
            print(f"   Erro ao processar {os.path.basename(img_path)}: {e}")
            return None

    def calculate_perceptual_hash(self, img_path):
        """Calcula hash perceptual"""
        try:
            img = Image.open(img_path)
            return imagehash.average_hash(img)
        except:
            return None

    def calculate_image_scores(self, embedding, positive_features, negative_features):
        """Calcula scores de similaridade"""
        try:
            embedding_tensor = torch.from_numpy(embedding).unsqueeze(0).to(DEVICE)

            positive_similarities = (embedding_tensor @ positive_features.T).cpu().numpy()[0]
            negative_similarities = (embedding_tensor @ negative_features.T).cpu().numpy()[0]

            max_positive = float(np.max(positive_similarities))
            max_negative = float(np.max(negative_similarities))

            return max_positive, max_negative, positive_similarities, negative_similarities
        except:
            return 0.0, 1.0, [], []

    def is_duplicate(self, img_path, embedding):
        """Verifica se imagem é duplicata"""
        filename = os.path.basename(img_path)

        # Hash perceptual
        img_hash = self.calculate_perceptual_hash(img_path)
        if img_hash:
            for existing_hash, existing_file in self.perceptual_hashes.items():
                if img_hash - existing_hash <= PERCEPTUAL_HASH_THRESHOLD:
                    return True, existing_file, "perceptual_hash"

        # CLIP embedding
        if embedding is not None:
            for existing_file, existing_emb in self.image_embeddings.items():
                similarity = np.dot(embedding, existing_emb)
                if similarity >= DUPLICATE_SIMILARITY_THRESHOLD:
                    return True, existing_file, "clip_embedding"

        return False, None, None

    def curate_dataset(self):
        """Aplica curadoria"""

        print("\nCodificando prompts...")
        positive_features = self.encode_prompts(POSITIVE_PROMPTS)
        negative_features = self.encode_prompts(NEGATIVE_PROMPTS)
        print(f"  {len(POSITIVE_PROMPTS)} prompts positivos (SIMPLIFICADOS)")
        print(f"  {len(NEGATIVE_PROMPTS)} prompts negativos (APENAS ÓBVIOS)")

        image_files = []
        for file in os.listdir(self.image_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(self.image_dir, file))

        self.stats["total"] = len(image_files)

        print(f"\nAnalisando {len(image_files)} imagens...")
        print(f"   Thresholds PERMISSIVOS:")
        print(f"   - MIN_POSITIVE: {MIN_POSITIVE_SCORE}")
        print(f"   - MAX_NEGATIVE: {MAX_NEGATIVE_SCORE}")
        print()

        results = []

        for img_path in tqdm(image_files, desc="Processando"):
            filename = os.path.basename(img_path)

            embedding = self.calculate_image_embedding(img_path)
            if embedding is None:
                continue

            # Verificar duplicata
            is_dup, dup_of, dup_type = self.is_duplicate(img_path, embedding)

            if is_dup:
                rejection_reason = "duplicate"
                self.stats["rejected_duplicate"] += 1
                approved = False
                pos_score, neg_score = 0.0, 0.0

                import shutil
                dest = os.path.join(self.duplicates_dir, filename)
                try:
                    shutil.copy2(img_path, dest)
                except:
                    pass

                results.append({
                    "filename": filename,
                    "approved": False,
                    "positive_score": 0.0,
                    "negative_score": 0.0,
                    "rejection_reason": rejection_reason,
                    "duplicate_of": os.path.basename(dup_of),
                    "duplicate_type": dup_type
                })
                continue

            # Calcular scores
            pos_score, neg_score, pos_sims, neg_sims = self.calculate_image_scores(
                embedding, positive_features, negative_features
            )

            # Decisão MUITO PERMISSIVA
            approved = False
            rejection_reason = None

            if pos_score < MIN_POSITIVE_SCORE:
                rejection_reason = "low_relevance"
                self.stats["rejected_low_relevance"] += 1
            elif neg_score > MAX_NEGATIVE_SCORE:
                rejection_reason = "negative_match"
                self.stats["rejected_negative_match"] += 1
            else:
                approved = True
                self.stats["approved"] += 1

                self.image_embeddings[filename] = embedding
                img_hash = self.calculate_perceptual_hash(img_path)
                if img_hash:
                    self.perceptual_hashes[img_hash] = filename

            import shutil
            dest = os.path.join(
                self.approved_dir if approved else self.rejected_dir,
                filename
            )
            try:
                shutil.copy2(img_path, dest)
            except Exception as e:
                print(f"   Erro ao copiar {filename}: {e}")

            results.append({
                "filename": filename,
                "approved": approved,
                "positive_score": round(pos_score, 4),
                "negative_score": round(neg_score, 4),
                "rejection_reason": rejection_reason
            })

        results_path = os.path.join(self.output_dir, "clip_scores.json")
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return results

    def generate_report(self, results):
        """Gera relatório"""
        print(f"\n{'='*70}")
        print("RELATÓRIO DE CURADORIA (VERSÃO PERMISSIVA)")
        print(f"{'='*70}")
        print(f"\nTotal analisado: {self.stats['total']}")
        print(f"\nAPROVADAS: {self.stats['approved']} ({self.stats['approved']/self.stats['total']*100:.1f}%)")
        print(f"\nREJEITADAS: {self.stats['total'] - self.stats['approved']}")
        print(f"   • Baixa relevância: {self.stats['rejected_low_relevance']}")
        print(f"   • Match negativo: {self.stats['rejected_negative_match']}")
        print(f"   • Duplicatas: {self.stats['rejected_duplicate']}")

        # Mostrar range de scores
        approved_results = [r for r in results if r['approved']]
        rejected_results = [r for r in results if not r['approved'] and r['rejection_reason'] != 'duplicate']

        if approved_results:
            scores = [r['positive_score'] for r in approved_results]
            print(f"\nSCORES DAS APROVADAS:")
            print(f"   Mínimo: {min(scores):.4f}")
            print(f"   Máximo: {max(scores):.4f}")
            print(f"   Média: {np.mean(scores):.4f}")

            top_10 = sorted(approved_results, key=lambda x: x['positive_score'], reverse=True)[:10]
            print(f"\nTOP 10:")
            for i, r in enumerate(top_10, 1):
                print(f"   {i:2d}. {r['filename'][:50]:<50s} {r['positive_score']:.4f}")

        if rejected_results:
            rej_scores = [r['positive_score'] for r in rejected_results if r['positive_score'] > 0]
            if rej_scores:
                print(f"\nSCORES DAS REJEITADAS:")
                print(f"   Mínimo: {min(rej_scores):.4f}")
                print(f"   Máximo: {max(rej_scores):.4f}")
                print(f"   Média: {np.mean(rej_scores):.4f}")

        print(f"\nSaída: {self.output_dir}/")
        print(f"{'='*70}")

        # Salvar relatório
        report_path = os.path.join(self.output_dir, "curation_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"RELATÓRIO - VERSÃO PERMISSIVA\n")
            f.write(f"{'='*70}\n\n")
            f.write(f"Data: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total: {self.stats['total']}\n")
            f.write(f"Aprovadas: {self.stats['approved']} ({self.stats['approved']/self.stats['total']*100:.1f}%)\n")
            f.write(f"Rejeitadas: {self.stats['total'] - self.stats['approved']}\n")
            f.write(f"  - Baixa relevância: {self.stats['rejected_low_relevance']}\n")
            f.write(f"  - Match negativo: {self.stats['rejected_negative_match']}\n")
            f.write(f"  - Duplicatas: {self.stats['rejected_duplicate']}\n")

if __name__ == "__main__":
    print("="*70)
    print("CURADORIA CLIP - VERSÃO PERMISSIVA CORRIGIDA")
    print("="*70)
    print(f"\n MUDANÇAS nesta versão:")
    print(f"  • Prompts simplificados (sem distinção de espécies)")
    print(f"  • Thresholds muito permissivos")
    print(f"  • Foco em rejeitar apenas o óbvio (screenshots, texto, etc)")
    print(f"\nDispositivo: {DEVICE}")
    print(f"MIN_POSITIVE_SCORE: {MIN_POSITIVE_SCORE}")
    print(f"MAX_NEGATIVE_SCORE: {MAX_NEGATIVE_SCORE}")

    if not os.path.exists(IMAGE_DIR):
        print(f"\nErro: '{IMAGE_DIR}' não encontrado!")
        exit(1)

    curator = CLIPCurator(IMAGE_DIR, OUTPUT_DIR)
    results = curator.curate_dataset()
    curator.generate_report(results)

    print(f"\n{'='*70}")
    print("PRÓXIMOS PASSOS")
    print(f"{'='*70}")
    print("\n1. Veja o relatório acima")
    print("\n2. Se ainda rejeitar muito (< 70%), ajuste:")
    print("   MIN_POSITIVE_SCORE = 0.12  # Ainda mais permissivo")
    print("\n3. Revise manualmente algumas de cada pasta")
    print("\n4. Para dataset público, mantenha aprovação alta (~70-90%)")
    print("\n5. Curadoria manual final é sempre necessária!")
    print(f"{'='*70}")
