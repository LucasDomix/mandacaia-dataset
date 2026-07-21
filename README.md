# Dataset anotado de *Melipona quadrifasciata* para deteccao de objetos

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21475933.svg)](https://doi.org/10.5281/zenodo.21475933)

Codigo, manifesto e caderno de validacao que acompanham a dissertacao
**"Dataset Anotado de Melipona Quadrifasciata para Deteccao de Objetos:
composicao, curadoria e validacao"** (PPGI, UTFPR Campus Cornelio Procopio).

O objetivo do repositorio e permitir a reproducao integral do processo descrito
no Capitulo 4 da dissertacao, da aquisicao das imagens a avaliacao do modelo.

## Dataset

O conjunto anotado esta publicado no Roboflow Universe, sob licenca CC BY-NC-SA 4.0:

- **Versao utilizada no treinamento e na avaliacao (v5):**
  https://universe.roboflow.com/aiutfprmqq/mandacaia-detection/dataset/5

A v5 inclui as copias geradas por aumento de dados no conjunto de treino.
O conjunto-fonte, anterior ao aumento, corresponde a **1.098 imagens** e
**2.567 instancias** em duas classes (`mandacaia` e `entrada`), com a mesma
particao 745 / 162 / 191.

## Manifesto

`manifesto/manifesto_dataset.csv` traz **uma linha por imagem do conjunto-fonte**
(1.098 linhas) e e a referencia que amarra as tabelas da dissertacao aos arquivos.

| Coluna | Descricao |
|---|---|
| `arquivo` | nome do arquivo no export |
| `fonte` | `iNaturalist` ou `acervo_autor` |
| `modalidade` | `fotografia_natureza`, `frame_video` ou `fotografia_direta` |
| `unidade_integridade` | unidade preservada na separacao: `observacao:<id>`, `colonia:<caixa>` ou `imagem_individual` |
| `split` | `treino`, `validacao` ou `teste` |
| `observation_id`, `photo_id` | identificadores do iNaturalist |
| `colonia`, `video_id`, `frame` | procedencia do material proprio em video |
| `sessao_captura`, `data_captura` | sessao das fotografias diretas (extraida do EXIF) |
| `n_mandacaia`, `n_entrada`, `n_instancias` | contagem de anotacoes por classe |
| `licenca`, `quality_grade`, `atribuicao`, `url` | procedencia e direitos |

O manifesto reconcilia exatamente com a Tabela de distribuicao por fonte,
modalidade e split apresentada na dissertacao.

### Unidades de integridade

A separacao entre conjuntos preservou unidades distintas conforme a fonte:

- **iNaturalist:** a observacao. As 288 observacoes que originaram as 643 imagens
  foram alocadas integralmente a um unico conjunto.
- **Frames de video:** a colonia. Cinco caixas, duas gravacoes por caixa, com tres
  caixas no treino, uma na validacao e uma no teste.
- **Fotografias diretas:** a imagem individual, sem agrupamento por sessao. Essa
  escolha introduz correlacao residual entre treino e teste nesse subconjunto e
  esta declarada entre as limitacoes do trabalho.

A coluna `sessao_captura` permite reagrupar as fotografias e refazer a particao.

## Estrutura e ordem de execucao

Os scripts estao numerados na ordem em que foram executados. Cada etapa
corresponde a uma secao do Capitulo 4 da dissertacao.

```
scripts/
  01_download_inaturalist.py       aquisicao via API (filtro por taxon e por licenca)
  02_remove_duplicates.py          deduplicacao por hash perceptual (dHash, limiar 4)
  03_clip_curation.py              curadoria semantica e duplicatas por CLIP (limiar 0,98)
  04_sincronizar_metadados.py      sincroniza o CSV com as imagens apos a revisao manual
  05_extrair_frames.py             extracao de frames dos videos (10 fps sobre 60 fps)
  06_merge_dataset.py              fusao das duas fontes e consolidacao de metadados
  07_adicionar_observation_id.py   cria a chave de integridade por observacao
  08_split_dataset.py              separacao em treino, validacao e teste
  09_gerar_manifesto.py            gera o manifesto a partir do export anotado
notebooks/
  YOLOv11s_Validacao_Mandacaia.ipynb   treinamento e avaliacao (YOLO11s)
manifesto/
  manifesto_dataset.csv
```

Duas dependencias entre etapas merecem atencao:

- **07 e pre-requisito de 08.** A separacao por integridade de observacao agrupa
  as imagens pela coluna `observation_id`, que nao vem pronta da API: ela e
  derivada da URL da observacao pelo script 07. Executar o 08 sem o 07 produz
  uma particao que nao preserva a integridade descrita na dissertacao.
- **04 depende de exclusao manual previa.** O script apenas remove do CSV as
  linhas cujas imagens ja nao existem na pasta, mantendo os metadados
  sincronizados com o conjunto que sobreviveu a revisao manual.

## Uso

```bash
pip install -r requirements.txt
pip install git+https://github.com/openai/CLIP.git

export MQ_DATA_DIR=/caminho/para/seus/dados
python scripts/01_download_inaturalist.py
```

Nenhum caminho absoluto esta fixo no codigo. Os scripts leem o diretorio base da
variavel de ambiente `MQ_DATA_DIR` e, na ausencia dela, usam o proprio diretorio
do script. No caderno do Colab, o caminho do Google Drive pode ser definido em
`MQ_DRIVE_PATH`.

Os scripts sao utilitarios de pesquisa, executados uma vez cada na ordem acima,
e nao uma biblioteca de uso geral.

## Licenca

Codigo sob licenca MIT. O dataset e distribuido sob CC BY-NC-SA 4.0. As imagens
do iNaturalist mantem as licencas Creative Commons originais de cada autor,
registradas por imagem no manifesto.

## Como citar

Para citar o codigo e o manifesto, use o DOI arquivado no Zenodo:

> CORDEIRO, Lucas Dominguez. *mandacaia-dataset*: pipeline de composicao, curadoria
> e validacao do dataset anotado de *Melipona quadrifasciata*. Versao v1.0.0.
> Zenodo, 2026. DOI: 10.5281/zenodo.21475933.

```bibtex
@software{cordeiro2026codigo,
  author    = {{Dominguez Cordeiro}, Lucas},
  title     = {mandacaia-dataset: pipeline de composicao, curadoria e validacao
               do dataset anotado de Melipona quadrifasciata},
  year      = {2026},
  version   = {v1.0.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21475933},
  url       = {https://doi.org/10.5281/zenodo.21475933}
}
```

Para citar o dataset, use a pagina da versao 5 no Roboflow Universe indicada na
secao Dataset. A referencia da dissertacao sera acrescentada apos o deposito.
