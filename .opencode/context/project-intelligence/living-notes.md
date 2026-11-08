<!-- Context: project-intelligence | Project: simbolos-br | Version: 2.1 | Updated: 2026-11-08 -->

# Living Notes — Símbolos BR

> Estado atual, próximo passo, dívidas e armadilhas. Complementa `PLAN.md` (design)
> e `decisions-log.md` (por quê). Atualizar ao fim de cada bloco de trabalho.

## O que é

Acervo aberto dos brasões e bandeiras dos municípios e estados brasileiros, com
procedência e licença por arquivo, URLs de embed estáveis e pacotes para download.

É o **primeiro acervo do `coletivo.dev.br`**, a iniciativa do **Ateliê DEV** para
contribuir com a sociedade através da programação. A outra frente é o
**Ensinamos** (`app.ensinamos.com.br`), de gestão escolar para escolas públicas.

| Host | Papel |
|---|---|
| `coletivo.dev.br` | portal da iniciativa (Símbolos + Ensinamos) |
| `coletivo.dev.br/simbolos` | este serviço |
| `simbolos.coletivo.dev.br` | ativos: `/embed/v1/{brasao\|bandeira}/{cod}.{svg,png,jpg}` e `/meta/v1/...` |
| `atelie.dev.br` | o ateliê |

Um host **por serviço** para os ativos, e não um `cdn.` compartilhado com prefixo:
o custom domain do R2 liga um host a um bucket, e o bucket é por serviço
(`simbolos-br-cdn`). O próximo acervo entra em `saude.coletivo.dev.br` com o
bucket dele, sem Worker. Configurável por `SITE_BASE` / `CDN_BASE` /
`SERVICO_PATH` em `simbolos/config.py` e no `devenv.nix`.

## Estado em 2026-11-08

| Etapa | Situação |
|---|---|
| Catálogo IBGE | pronto: 27 UFs, 5.571 municípios (`data/municipios.json`) |
| Coleta Wikidata + Commons | pronta: 4.353 brasões, 4.037 bandeiras |
| Triagem | pronta: `data/_catalogo/catalogo.json` (4.790 municípios com item) |
| Publicação | **concluída**: 8.369 de 8.390 (11 falhas), 1,3 GB |
| Sidecars no R2 | 8.379 com `urls` e cache de 1 h — **desatualizados**: ainda sem os campos de D21 |
| Fontes originais | 7.209 rasters em `data/fontes` (1,3 GB), 0 divergências, backup no bucket privado |
| Procedência | **conferida**: 8.379 de 8.379 iguais por `sha1` no Commons, em 3 min e 168 requisições, sem baixar arquivo (D21) |
| Sidecars locais | em `data/meta/v1` (verdade versionável), com `sha1_origem`, `capturado_em`, `verificacao` e `guarda` |
| Guarda | 68 itens de risco alto (69 `pendente`, 1 vetorial), 8.311 baixos; `data/risco.json` |
| R2 | `simbolos-br-cdn` 1,32 GB (público) + `simbolos-br-acervo` 1,30 GB (**sem domínio**) = 2,62 GB, 26% do free tier |
| Site | **no ar**: landing, `/consultar`, `/cobertura`, `/sobre`, 5.571 municípios, 27 estados, portal na raiz |
| URLs | limpas, sem barra (`build.format: "file"`) e com `link rel=canonical` |
| Deploy | Pages projeto `coletivo`, `coletivo.dev.br` + `www`, deploy manual |
| Repositório | público em `github.com/atelie-dev/simbolos-br`, AGPL-3.0, 6 commits + FUNDING |
| Apoio | GitHub Sponsors ativo; PIX com chave UUID e sem `txid` |
| Pacotes npm/PyPI/Composer | não começaram |

Números públicos: 8.379 itens, 4.788 municípios cobertos (85,9%), 1.170 itens
vetoriais. Vetorial por tipo: 573 municípios com brasão em SVG, 597 com bandeira
em SVG, 364 com os dois. Baldes (contados nos sidecars): livre 7.096,
compartilha 1.214, pendente 69.

## Próximo passo, em ordem

1. **Git como armazém** (decisão do mantenedor, falta executar): versionar
   `data/meta/` (34 MB), o livro-razão de upload e os 1.170 vetores; renditions
   ficam fora porque são derivadas. É o que torna `vetor_versionavel` verdade.
2. **Portão de visão** nos 915 itens que precisam (`simbolos visao`, motor
   `decisao`), e nos achados do crawl oficial.
3. **`/baixar`**: pacotes por estado e formato, `brasil-livre.zip` (só balde
   livre) e `danfse-192.zip`. É a última rota do plano que falta no site.
4. **`/m/{cod}`** como redirect: `_redirects` do Pages aceita só 2.100 — precisa
   Bulk Redirects na zona ou Worker.
5. **Crawl oficial** nos 1.218 municípios restantes (~536 brasões por ~US$ 1).
   Todo item que ele trouxer nasce sem espelho — `verificar-fonte` já sabe dizer
   isso pelo campo `origem`.
6. **Símbolos dos estados**: os 27 nunca entraram na coleta; a página do estado
   diz isso explicitamente.
7. **`/transparencia`**: já existe número — domínio, 2,62 GB de R2, egress zero,
   e os 68 itens sem cópia independente.
8. **CI**: ligar o Pages ao GitHub exige gerar o índice no build (depende do
   catálogo e dos PNGs) — decisão à parte.

## Dívidas conhecidas

| Item | Impacto | Prioridade |
|---|---|---|
| Teste só na política de guarda (13 casos) | pipeline ainda sem cobertura | alta |
| 1.170 vetores só em `dist/` e no R2 | `dist` é descartável; é o passo 1 acima | alta |
| `publicar` sem paralelismo | ETA ditado por 1 req/s + render sequencial | média |
| 69 itens `pendente` sem alternativa de licença | ficam fora dos downloads livres; 68 são risco alto | média |
| Triagem não usa `dHash` | erro de brasão trocado só cai na visão | baixa |
| `itens.json` (5,6 MB) e `malha/` (9 MB) no git | repositório cresce; são derivados | baixa |

## Armadilhas (custaram tempo de verdade)

**Pipeline / dados**

- **`python3` não existe no PATH.** Sempre `uv run python …`.
- **`resvg` só existe dentro do `devenv shell`**; `publicar` tem preflight.
- **Wikimedia responde 429** se baixar rápido: 1 req/s por host + backoff +
  `Retry-After`, em `publicacao.baixar`.
- **HTML traz entidade** (`Bras&atilde;o`): normalizar antes de procurar "brasão".
- **`incategory:` em `list=search` retorna 0** sem `srnamespace=6`; para listar
  categoria use `list=categorymembers&cmtype=file`.
- **Wikidata `P41`/`P94` às vezes guarda URL**; normalizar com
  `wikidata.titulo_normalizado`.
- **`S5` gasta o orçamento em raciocínio** e devolve `content: null` com
  `finish_reason: length`; tratar `length` como truncamento.
- **Catálogo não é acervo**: 3 dos 19 links do piloto já estavam mortos.
- **Rendition não é fonte**: o original fica em `data/fontes/v1/…`, com hash;
  `simbolos fontes` rebaixa a safra antiga e manda divergência para `conflito/`.
- **`dist/catalogo.json` é derivado**: a verdade é o sidecar
  `dist/meta/v1/{tipo}/{cod}.json`; retomada lê sidecar → catálogo → disco.
- **`/tmp` é zram (RAM)**: PDF de ato oficial vai para `data/evidencias/pdf/`.
- **PIX: o BR Code carrega a chave em texto claro.** Chave por e-mail vira e-mail
  público; usar UUID. Campo 62 = `txid`; omitir = "não informado". O CRC cobre
  **todo** o payload, inclusive o cabeçalho `6304` do campo 63.
- **Commons publica `sha1`, não `sha256`** — e a API devolve hex. Conferir
  procedência com sha256 obriga a rebaixar o arquivo; com sha1 custa uma
  requisição por 50 títulos (`verificar-fonte`: 8.379 em 3 min).
- **Título do Commons deriva da URL de upload, e a URL muda quando o arquivo é
  renomeado.** Título que não resolve **não** é sumiço: cair para
  `list=allimages&aisha1=<sha1>` antes de concluir.
- **`capturado_em` da safra antiga vem do `mtime` do arquivo guardado** — é a
  hora real da gravação, não a da execução; `captura_fonte` distingue `mtime` de
  `relogio` para ninguém confundir as duas depois.
- **Fatiar a malha**: o item de cada célula é `[codigo, slug, aneis]`; o teste
  par-ímpar sobre todos os anéis resolve MultiPolygon e furo.

**Site / deploy**

- **`import.meta.env.BASE_URL` vem sem barra final** ("/simbolos"): concatenar
  direto gera `/simbolosapi/...`. Use `BASE` de `src/lib/urls.ts`.
- **Astro descarta o espaço entre texto e tag em linhas separadas**: "do\n<a>"
  vira "do<a>". Usar `{" "}`. Sintoma: "livreCC0-1.0", "doatelie.dev.br".
- **`build.format: "folder"` gera 308 para a barra no Pages**: use
  `format: "file"` e `trailingSlash: "never"`; a raiz (`/simbolos/`) é exceção.
- **`wrangler pages project create` precisa de `--force`** na primeira vez
  (o wrangler 4.156 delega Pages→Workers e falha); depois, nunca mais.
- **Pages não cria o registro DNS do domínio**: anexar deixa `pending` para
  sempre, sem erro. Criar CNAME proxiado para `<projeto>.pages.dev`.
- **`Permissions-Policy: geolocation=()` bloqueia a própria página**: o botão
  "onde estou" depende de `geolocation=(self)`.
- **Resolver local guarda NXDOMAIN**: domínio novo parece morto por minutos.
  Verificar com `curl --doh-url https://cloudflare-dns.com/dns-query`.
- **`fetch(..., {cache: "force-cache"})` serve índice velho** até o `max-age`;
  para dados que mudam a cada publicação, deixar revalidar.
- **`_headers` só vale na raiz do deployment**; o `empacotar_site.py` copia
  `portal/` para lá justamente por isso.

## Questões abertas

| Questão | Status |
|---|---|
| Crédito de contribuidor: anônimo por padrão? | recomendado, não decidido |
| Nomes dos pacotes (`@coletivo/…`) | aberto |
| Continuar o crawl oficial nos 1.218 restantes | recomendado (~536 brasões por ~US$ 1) |
| Remover o CEP (campo 61) do BR Code | opcional; menos dado pessoal no QR |
| Nome no BR Code é "FABIO DBATISTA"; trocar por nome comercial | depende do PSP |
| Rendition 192 px para DANFSE | desenhada, não implementada |

## Registro de marcas/modelos (para não redescobrir)

- **Maritaca**: `S5` (1M ctx), `sabia-4`, `sabiazinho-4`, `S5-br-sp`, `S5-nano`.
  `service_tier: "flex"` = 50%, síncrono, pode dar 429. Batch = 50%, mas um lote
  de 1 requisição ficou >20 min em `in_progress`.
- **Neuralwatt**: `glm-5.3`, `glm-5.3-flash`, `deepseek-v4.1-flash` (+`-flex`),
  `clef-flash` (decisão, só em `POST /v1/systemone`), `kimi-k3`, `qwen3.6`.
- **DeepSeek direto**: descontinuado no projeto.
- **Custo medido**: 10 páginas US$ 0,0009 (Neuralwatt flex) vs R$ 0,0419 (S5
  flex); visão ~US$ 0,00008/imagem.
