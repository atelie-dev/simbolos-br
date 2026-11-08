# Símbolos — acervo de brasões e bandeiras do Brasil

Acervo aberto dos símbolos de municípios e estados brasileiros, com
procedência declarada, licença por arquivo e URLs estáveis para embutir em
qualquer documento.

- Site: <https://coletivo.dev.br/simbolos>
- Ativos: `https://simbolos.coletivo.dev.br/embed/v1/{brasao|bandeira}/{cod_ibge}.{svg,png,jpg}`
- Metadados por item: `https://simbolos.coletivo.dev.br/meta/v1/{tipo}/{cod_ibge}.json`

Este é o primeiro acervo do **coletivo.dev.br**, a iniciativa do
[Ateliê DEV](https://atelie.dev.br) para contribuir com a sociedade através da
programação. A outra frente é o [Ensinamos](https://app.ensinamos.com.br), de
gestão escolar.

## O que existe

| Medida | Valor |
|---|---|
| Municípios no catálogo | 5.571 |
| Municípios com ao menos um símbolo | 4.788 (85,9%) |
| Itens publicados | 8.379 |
| Itens vetoriais (SVG) | 1.170 |

Números atualizados em `/cobertura`, sempre com numerador e denominador.

## Como o acervo é feito

1. **Enumeração, não raspagem de artigo**: Wikidata (`P1585` → `P94`/`P41`),
   categorias do Wikimedia Commons e, para lacunas, o site oficial do município.
2. **Fonte canônica + renditions**: guarda-se o arquivo original e derivam-se
   PNG 512 (fundo transparente) e JPG 512 (fundo branco). Nada é esticado.
3. **Procedência capturada, não escrita por modelo**: URL, autor, data e
   `sha256` vêm do arquivo baixado. Citação de modelo só vale se for substring
   literal do material guardado.
4. **Publicação idempotente**: cada item tem um sidecar `meta.json`; o catálogo
   é derivado. Interromper o processo não perde arquivo nem rebaixa o que já
   existe.

## Rodando

O ambiente é [devenv](https://devenv.sh) (Python 3.15, Node, `resvg`, `rclone`…):

```bash
devenv shell                      # entra no ambiente
uv run python -m simbolos --help  # CLI do pipeline (catalogo, publicar, fontes, r2…)
```

Site (Astro):

```bash
uv run python -m simbolos indice      # gera o índice de busca e a cobertura
cd site && npm install && npm run dev # http://localhost:4321/simbolos/
```

O build do site lê `site/public/api/v1/*.json` (gerado por `indice`) e
`site/src/data/itens.json` (gerado pelo mesmo comando).

## Estrutura

```
simbolos/     pipeline em Python (coleta, triagem, publicação, R2, visão)
data/         catálogo IBGE, catálogo triado, fontes originais, evidências
site/         site estático em Astro + DESIGN.md (direção visual)
infra/        configuração de infraestrutura (CORS do bucket)
PLAN.md       desenho completo, com números medidos e decisões
```

## Licenças, em três camadas

| Camada | Licença |
|---|---|
| Código | AGPL-3.0 (ver `LICENSE`) |
| Metadados (índice, cobertura, `meta.json`) | CC0 |
| Imagens | Licença da fonte, em SPDX, por arquivo |

Cada imagem carrega um de três baldes: `livre` (CC0, domínio público, CC BY),
`compartilha` (CC BY-SA) ou `oficial` (publicado pela própria prefeitura — **não**
é domínio público). O balde de cada item aparece na sua página e no `meta.json`.

## Independência

Projeto sem vínculo com governo, IBGE, prefeituras ou partidos. O símbolo é do
município; o acervo é um lugar melhor para encontrá-lo. Correção de atribuição e
contestação são parte do produto.

## Contribuir

O fluxo de contribuição está em construção. Lacunas conhecidas: os 27 símbolos
estaduais ainda não entraram, e 783 municípios não têm nenhum símbolo publicado.
