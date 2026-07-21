import cv2
import os
import math

# Diretorio base dos dados. Configure pela variavel de ambiente MQ_DATA_DIR
# ou edite o valor padrao abaixo. Nenhum caminho absoluto fica fixo no codigo.
DATA_DIR = os.environ.get("MQ_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))


# ================= CONFIGURAÇÕES =================
# Caminho exato que você passou
DIRETORIO_VIDEOS = os.path.join(DATA_DIR, "Videos")

# Nome da pasta que será criada lá dentro
NOME_PASTA_SAIDA = "frames_extraidos_3fps"

# Taxa de captura (ideal para Mandaçaia)
FRAMES_POR_SEGUNDO = 10
# =================================================

def processar_pasta():
    # 1. Cria o caminho completo de saída
    path_saida = os.path.join(DIRETORIO_VIDEOS, NOME_PASTA_SAIDA)

    if not os.path.exists(path_saida):
        os.makedirs(path_saida)
        print(f"Pasta criada: {path_saida}")
    else:
        print(f"Usando pasta existente: {path_saida}")

    # 2. Lista todos os arquivos da pasta
    arquivos = os.listdir(DIRETORIO_VIDEOS)
    videos = [f for f in arquivos if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]

    if not videos:
        print(f"Nenhum vídeo encontrado em: {DIRETORIO_VIDEOS}")
        return

    print(f"Encontrados {len(videos)} vídeos. Iniciando extração...\n")

    total_frames_gerados = 0

    # 3. Loop por cada vídeo
    for video_file in videos:
        caminho_video = os.path.join(DIRETORIO_VIDEOS, video_file)

        cap = cv2.VideoCapture(caminho_video)
        if not cap.isOpened():
            print(f"Erro ao abrir: {video_file} (pulando)")
            continue

        fps_original = cap.get(cv2.CAP_PROP_FPS)
        if fps_original == 0: # Evita divisão por zero em vídeos corrompidos
             print(f"FPS inválido no vídeo: {video_file} (pulando)")
             continue

        # Calcula o intervalo (pulo)
        intervalo = math.ceil(fps_original / FRAMES_POR_SEGUNDO)

        print(f"Processando: {video_file} ({fps_original:.2f} FPS originais -> pulando a cada {intervalo} frames)")

        frame_count = 0
        saved_count = 0
        nome_base = os.path.splitext(video_file)[0] # Remove a extensão .mp4 do nome

        while True:
            success, frame = cap.read()
            if not success:
                break

            # A Mágica: Só salva se for o momento certo
            if frame_count % intervalo == 0:
                # Nome: video01_0001.jpg
                nome_imagem = f"{nome_base}_{saved_count:04d}.jpg"
                caminho_final = os.path.join(path_saida, nome_imagem)

                cv2.imwrite(caminho_final, frame)
                saved_count += 1

            frame_count += 1

        cap.release()
        total_frames_gerados += saved_count
        print(f"   {saved_count} imagens extraídas de {video_file}")

    print("\n" + "="*40)
    print(f"CONCLUÍDO! Total de {total_frames_gerados} novas imagens.")
    print(f"Local: {path_saida}")
    print("="*40)
    print("PRÓXIMO PASSO: Abra a pasta, delete as fotos vazias e suba os 'borrões' para o Roboflow.")

if __name__ == "__main__":
    processar_pasta()