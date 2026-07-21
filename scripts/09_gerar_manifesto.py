#!/usr/bin/env python3
"""Gera o manifesto do dataset: uma linha por imagem efetivamente utilizada.
Fonte da verdade: export Roboflow v6 SEM aumento de dados (1.098 imagens)."""
import csv, os, re, glob, collections
from datetime import datetime

BASE = os.environ.get("MQ_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
EXPORT = f"{BASE}/imagens2026/Dataset_sem_augmentation/Mandacaia Detection.v6i.yolov11"
FOTOS  = f"{BASE}/imagens2026/minhas_fotos_mandacaia"
OUT    = f"{BASE}/manifesto_dataset.csv"
SPLIT_PT = {"train": "treino", "valid": "validacao", "test": "teste"}
CLASSES = {0: "entrada", 1: "mandacaia"}   # ordem REAL do data.yaml: ['entrada','mandacaia']

# ---------- metadados iNaturalist ----------
inat = {}
with open(f"{BASE}/imagens2026/melipona_quadrifasciata_images/image_metadata.csv", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        inat[(r["observation_id"], r["photo_id"])] = r

# ---------- EXIF das fotografias -> sessao de captura ----------
from PIL import Image
from PIL.ExifTags import TAGS
exif = {}
for f in glob.glob(f"{FOTOS}/IMG_*.JPG") + glob.glob(f"{FOTOS}/IMG_*.jpg"):
    try:
        raw = Image.open(f)._getexif() or {}
        d = {TAGS.get(k, k): v for k, v in raw.items()}
        s = d.get("DateTimeOriginal") or d.get("DateTime")
        if s:
            exif[os.path.splitext(os.path.basename(f))[0].upper()] = datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
# sessoes: novo bloco quando o intervalo entre fotos consecutivas passa de 60 min
sessao = {}
for i, (k, t) in enumerate(sorted(exif.items(), key=lambda x: x[1])):
    if i == 0 or (t - prev).total_seconds() > 3600:
        n = len(set(sessao.values())) + 1
    sessao[k] = f"sessao_{n:02d}_{t:%Y%m%d}"
    prev = t

# ---------- videos -> colonia (pares de gravacao consecutiva) ----------
vids = sorted({m.group(0) for s in SPLIT_PT
               for f in os.listdir(f"{EXPORT}/{s}/images")
               if (m := re.match(r"VID_(\d{8})_(\d{6})", f))})
# Mapeamento video -> caixa (colonia), CONFIRMADO pelo autor por inspecao visual:
# 5 caixas, 2 gravacoes consecutivas por caixa. Pareamento validado pelas contagens de
# frames: caixa_04 = 56 frames (todo o teste), caixa_05 = 40 frames (toda a validacao),
# caixas 01-03 = 160 frames (todo o treino).
col = {}
for k, (a, b) in enumerate([("VID_20260108_072446", "VID_20260108_072622"),
                            ("VID_20260118_082251", "VID_20260118_082347"),
                            ("VID_20260118_082426", "VID_20260118_082515"),
                            ("VID_20260118_082606", "VID_20260118_082657"),
                            ("VID_20260118_084513", "VID_20260118_084557")], start=1):
    col[a] = col[b] = f"caixa_{k:02d}"

# ---------- monta o manifesto ----------
linhas = []
for split_en, split_pt in SPLIT_PT.items():
    for fn in sorted(os.listdir(f"{EXPORT}/{split_en}/images")):
        lab = os.path.join(EXPORT, split_en, "labels",
                           os.path.splitext(fn)[0] + ".txt")
        cont = collections.Counter()
        if os.path.exists(lab):
            with open(lab) as fh:
                for ln in fh:
                    if ln.strip():
                        cont[CLASSES.get(int(ln.split()[0]), "?")] += 1

        r = dict(arquivo=fn, split=split_pt,
                 n_mandacaia=cont["mandacaia"], n_entrada=cont["entrada"],
                 n_instancias=sum(cont.values()),
                 fonte="", modalidade="", unidade_integridade="",
                 observation_id="", photo_id="", colonia="", video_id="",
                 sessao_captura="", frame="", data_captura="",
                 licenca="", atribuicao="", quality_grade="", url="")

        if m := re.match(r"melipona_quadrifasciata[a-z_]*_(\d+)_(\d+)_", fn, re.I):
            obs, pho = m.group(1), m.group(2)
            md = inat.get((obs, pho), {})
            r.update(fonte="iNaturalist", modalidade="fotografia_natureza",
                     unidade_integridade=f"observacao:{obs}",
                     observation_id=obs, photo_id=pho,
                     data_captura=md.get("observed_on", ""),
                     licenca=md.get("license", ""), atribuicao=md.get("photographer", ""),
                     quality_grade=md.get("quality_grade", ""), url=md.get("url", ""))
        elif m := re.match(r"(VID_\d{8}_\d{6})_(\d+)", fn):
            v, fr = m.group(1), m.group(2)
            r.update(fonte="acervo_autor", modalidade="frame_video",
                     unidade_integridade=f"colonia:{col[v]}",
                     colonia=col[v], video_id=v, frame=str(int(fr)),
                     data_captura=f"{v[4:8]}-{v[8:10]}-{v[10:12]}",
                     licenca="cc-by-nc-sa", atribuicao="Lucas Dominguez Cordeiro",
                     quality_grade="curadoria_manual")
        elif m := re.match(r"own_IMG_(\d+)_", fn):
            k = f"IMG_{m.group(1)}"
            t = exif.get(k)
            r.update(fonte="acervo_autor", modalidade="fotografia_direta",
                     unidade_integridade="imagem_individual",
                     sessao_captura=sessao.get(k, "nao_registrada"),
                     data_captura=t.strftime("%Y-%m-%d") if t else "",
                     licenca="cc-by-nc-sa", atribuicao="Lucas Dominguez Cordeiro",
                     quality_grade="curadoria_manual")
        elif m := re.match(r"own_WhatsApp-Image-(\d{4})-(\d{2})-(\d{2})-at-(\d{2})-(\d{2})-(\d{2})", fn):
            y, mo, d, hh, mm, ss = m.groups()
            r.update(fonte="acervo_autor", modalidade="fotografia_direta",
                     unidade_integridade="imagem_individual",
                     sessao_captura=f"sessao_whatsapp_{y}{mo}{d}",
                     data_captura=f"{y}-{mo}-{d}",
                     licenca="cc-by-nc-sa", atribuicao="Lucas Dominguez Cordeiro",
                     quality_grade="curadoria_manual")
        linhas.append(r)

campos = ["arquivo", "fonte", "modalidade", "unidade_integridade", "split",
          "observation_id", "photo_id", "colonia", "video_id", "frame",
          "sessao_captura", "data_captura", "n_mandacaia", "n_entrada",
          "n_instancias", "licenca", "quality_grade", "atribuicao", "url"]
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=campos)
    w.writeheader()
    w.writerows(linhas)
print(f"{OUT}: {len(linhas)} linhas")
