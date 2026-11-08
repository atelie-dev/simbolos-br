<!-- Context: project-intelligence | Project: simbolos-br | Version: 2.0 | Updated: 2026-11-08 -->

# Technical Domain — Símbolos BR

## Stack

| Peça | Escolha |
|---|---|
| Linguagem | Python 3.15 (uv) |
| CLI | Typer + Rich |
| Ambiente | devenv (nixpkgs-unstable) |
| Imagem | resvg (SVG→PNG) + Pillow (composição) |
| LLM | Maritaca (S5) e Neuralwatt (deepseek-v4.1-flash, glm-5.3, clef-flash) |
| Dados | HTTP APIs públicas (IBGE, Wikidata, Commons, sites `.gov.br`) |
| Site | Astro 7 estático, servido pelo Cloudflare Pages |
| Geo | malha municipal do IBGE fatiada em células + `segno` para o QR do PIX |
| Arquivos | Cloudflare R2: `simbolos-br-cdn` (público) e `simbolos-br-acervo` (privado) |

## Comandos

```bash
devenv shell                  # resvg, poppler, python, node estão aqui dentro

uv run python -m simbolos catalogo         # 5.571 municípios + 27 UFs
uv run python -m simbolos wikidata         # P1585 -> P94/P41 + imageinfo
uv run python -m simbolos commons          # categorias do Commons (todas as UFs)
uv run python -m simbolos spike            # rendimento na amostra estratificada
uv run python -m simbolos triar            # um candidato por município -> catálogo
uv run python -m simbolos publicar         # baixa + renderiza + dist/embed/v1
uv run python -m simbolos fontes           # rebaixa e arquiva o original em data/fontes
uv run python -m simbolos urls             # carimba URLs públicas no catálogo
uv run python -m simbolos r2               # sobe embed/ + meta/ para simbolos-br-cdn
uv run python -m simbolos acervo           # backup privado em simbolos-br-acervo
uv run python -m simbolos indice           # índice de busca + resumo do site
uv run python -m simbolos centros          # coordenada da sede de cada município (Wikidata)
uv run python -m simbolos malha            # malha municipal do IBGE em células de 1°
uv run python -m simbolos pix              # valida o BR Code e gera o QR do PIX
uv run python -m simbolos pix --sem-txid   # recria o código sem o campo 62 (txid)

# site (Astro estático) e montagem do deploy
cd site && npm install && npm run dev       # http://localhost:4321/simbolos/
cd site && npm run build && cd ..
uv run python scripts/empacotar_site.py     # deploy/ = portal na raiz + simbolos/
wrangler pages deploy deploy --project-name coletivo --branch main
uv run python -m simbolos leis --uf SP --limite 6   # crawl de sites oficiais
uv run python -m simbolos visao --url …    # portão de visão (motor decisao|chat)

uv run python -m simbolos maritaca saldo --provedor neuralwatt
uv run python -m simbolos maritaca provedores
uv run python -m simbolos maritaca extrair --url … [--flex]
```

## Layout

```
simbolos/          pacote (config, catalogo, nomes, modelos, commons, wikidata,
                   triagem, publicacao, leis, visao, maritaca, provedores, cli)
data/
  estados.json, municipios.json      catálogo IBGE (versionado)
  _coleta/                           JSONL bruto (gitignored, regenerável)
  _catalogo/catalogo.json            um item por município/tipo
  _spike/                            relatórios e conjuntos rotulados
dist/                                publicação local (gitignored)
  embed/v1/{brasao|bandeira}/{cod}.{svg,png,jpg}
  meta/v1/{brasao|bandeira}/{cod}.json   sidecar por ativo: a verdade do item
  catalogo.json                      agregado derivado dos sidecars
data/evidencias/pdf/                 PDF do ato oficial (gitignored; backup no R2)
data/fontes/v1/{brasao|bandeira}/{cod}.{ext}   original byte a byte (gitignored)
PLAN.md                              design completo
portal/                              portal do domínio (raiz): index.html, portal.css, _headers
site/                                Astro estático (base `/simbolos`)
  DESIGN.md                          direção visual — lei para toda a UI
  src/styles/tokens.css              cor, raio, sombra, movimento
  src/lib/urls.ts                    BASE/CDN e contrato de URL
  src/lib/dados.ts                   índice, itens e cálculo de tier
  src/components/Busca.astro         busca sem backend (índice sob demanda)
  src/components/SimboloCard.astro   cartão de brasão/bandeira (ou estado vazio)
  src/pages/index.astro              landing (§4.2)
  src/pages/consultar.astro          busca (§4.3)
  src/pages/cobertura.astro          matriz UF × tipo × tier
  src/pages/sobre.astro              quem mantém, licenças, custos
  src/pages/municipios/[slug].astro  5.571 páginas (§4.4)
  src/pages/estados/[uf].astro       27 páginas de UF
  src/data/itens.json                detalhe por item (build-only, 5,6 MB)
  src/data/destaques.json            capitais sorteadas na landing (24)
  src/data/pix.json                  BR Code validado (chave UUID, sem txid)
  public/api/v1/*.json               gerado por `simbolos indice` (antes do build)
  public/api/v1/malha/{lat}_{lon}.json  malha do IBGE fatiada (836 células, ~10 KB cada)
  public/pix-qr.svg                  QR do PIX, gerado no build por `simbolos pix`
  public/fonts/*.woff2               Bricolage Grotesque + Source Sans 3
deploy/                              gerado por scripts/empacotar_site.py (gitignored)
infra/r2-cdn-cors.json               CORS do bucket público (aplicado via wrangler)
.opencode/context/project-intelligence/  este pacote
```

## Pipeline

```
catálogo IBGE → coleta (Wikidata/Commons) → triagem → publicação → CDN
                                    ↘ crawl .gov.br (lacunas + ato oficial)
portão de visão (clef-flash) e checagens determinísticas em cada etapa
```

## Contrato público

```
GET https://simbolos.coletivo.dev.br/embed/v1/{brasao|bandeira}/{cod}.{svg|png|jpg}
GET https://simbolos.coletivo.dev.br/meta/v1/{brasao|bandeira}/{cod}.json
GET https://coletivo.dev.br/simbolos/api/v1/{municipios|resumo|centros}.json
GET https://coletivo.dev.br/simbolos/api/v1/malha/{lat}_{lon}.json
```

- `cod_ibge` = 7 dígitos (município) ou 2 (estado).
- Todos os três formatos existem para todo item publicado; formato ausente = 404.
- `meta.json` é autossuficiente: traz `urls` e a procedência; cache de 1 h.
- No R2: `Cache-Control` e `Content-Type` por objeto, metadados
  `sha256`/`licenca`/`cod-ibge`/`tipo`, e CORS (`infra/r2-cdn-cors.json`).
  No host `simbolos.coletivo.dev.br`, Transform Rule aplica `nosniff`,
  `referrer-policy` e CSP `sandbox` nos `.svg`.
- No Pages: URLs sem barra (`format: "file"`), `canonical` em toda página,
  `_headers` na raiz do deployment.
- Secrets nunca no repo: `.env` vem do 1Password (ambiente `simbolos-br`) e é
  carregado por `python-dotenv` em `simbolos/__init__.py`. Está no `.gitignore`.

## Repositório

Público em `git@github.com:atelie-dev/simbolos-br.git` (branch `main`), sob
AGPL-3.0 (`LICENSE`), com `.github/FUNDING.yml` apontando o GitHub Sponsors. O
`.env` é montado pelo 1Password e está fora do índice; `dist/`, `data/fontes/`,
`data/_coleta/`, `site/dist/`, `deploy/` e `node_modules/` também.
O site depende de `site/public/api/v1/*.json`, `site/src/data/*.json` e
`site/public/pix-qr.svg`, todos gerados e versionados para o build funcionar sem
o acervo binário.

## Infra Pages

| Item | Valor |
|---|---|
| Projeto | `coletivo` (produção na branch `main`) |
| Conteúdo | `deploy/` = portal na raiz + `simbolos/` (montado por `scripts/empacotar_site.py`) |
| Deploy | `wrangler pages deploy deploy --project-name coletivo --branch main` |
| Domínios | `coletivo.dev.br` e `www.coletivo.dev.br` |
| URLs | `build.format: "file"`: `/simbolos/consultar`, sem barra e sem `.html`; a barra responde 308 para a limpa. Cada página tem `link rel="canonical"` |
| DNS | CNAME proxiado para `coletivo.pages.dev` — o Pages **não** criou o registro sozinho |
| Headers | `portal/_headers` (é o único que vale: o Pages lê só o da raiz). `Permissions-Policy` libera `geolocation=(self)` — o botão "onde estou" depende disso |

**Criação do projeto (uma vez):** `wrangler pages project create coletivo --production-branch main --force`.
O `--force` é necessário porque o wrangler 4.156 delega `pages` para Workers e a
delegação falha com "Missing entry-point to Worker script". Depois de o projeto
existir, os comandos seguintes rodam direto no Pages — **não** repetir `--force`.

## Infra R2

| Item | Valor |
|---|---|
| Conta Cloudflare | Coletivo.dev |
| Bucket público | `simbolos-br-cdn` ← `embed/v1/…`, `meta/v1/…` |
| Bucket privado | `simbolos-br-acervo` ← `fontes/v1/…`, `evidencias/pdf/…` |
| Variáveis | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_R2_ENDPOINT`, `CLOUDFLARE_R2_ACCESS_KEY_ID`, `CLOUDFLARE_R2_SECRET_ACCESS_KEY` (`.env` do 1Password) |
| Livro-razão | `data/_cache/r2-cdn.json` e `r2-acervo.json` — pula por `sha256` |
| URL pública | `https://simbolos.coletivo.dev.br/embed/v1/…` (custom domain do bucket, ativo) |

**Zona `coletivo.dev.br`:** ativa desde 2026-11-08 (NS `coby`/`elly` do
Cloudflare). `simbolos.coletivo.dev.br` é CNAME proxiado para `public.r2.dev`,
gerenciado pelo R2 — **um host por serviço**, porque o custom domain liga um host
a um bucket e o bucket é por serviço. Transform Rule
`http_response_headers_transform` aplica `nosniff` + `referrer-policy` em todo o
host e CSP `sandbox` nos `.svg`. `cdn.coletivo.dev.br` foi removido, e a dev URL
`r2.dev` está desligada.

## Convenções de código

- Português nos nomes de domínio (`brasao`, `bandeira`, `codigo_ibge`), inglês nas
  bibliotecas. Docstrings em português, curtas.
- Modelos Pydantic em `modelos.py`; nada de dicionário solto atravessando etapas.
- Pipeline idempotente e retomável: cada etapa relê o que já existe e mescla.
- Nada de constante de domínio no código: `config.py` + ambiente.
- `ruff` limpo antes de cada commit; `ruff format` como formatador.
- **Em Astro, texto seguido de tag em outra linha perde o espaço**: usar `{" "}`
  (senão sai "livreCC0-1.0" ou "doatelie.dev.br").

## O que ainda não existe

- Testes automatizados (maior dívida).
- `/baixar` (pacotes por estado e formato) e `/transparencia`.
- `/m/{cod}` como redirect (precisa Bulk Redirects ou Worker).
- Purge automático no publish.
- Símbolos dos 27 estados na coleta.
- CI no Pages (depende de gerar o índice no build).
