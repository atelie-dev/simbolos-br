<!-- Context: project-intelligence | Project: simbolos-br | Version: 2.7 | Updated: 2026-11-09 -->

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

## Estado em 2026-11-09

| Etapa | Situação |
|---|---|
| Catálogo IBGE | pronto: 27 UFs, 5.571 municípios (`data/municipios.json`) |
| Coleta Wikidata + Commons | pronta: 4.353 brasões, 4.037 bandeiras |
| Triagem | pronta: `data/_catalogo/catalogo.json` (4.790 municípios com item) |
| Publicação | **concluída**: 9.236 itens publicados, 12 sem embed por SVG recusado |
| Sidecars no R2 | 9.236 regravados, 13,6 MB, 0 falhas |
| Fontes originais | 1,6 GB em `data/fontes` (rasters + versões anteriores), backup no bucket privado |
| Procedência | **conferida**: 9.236 de 9.236 itens com data de verificação |
| Crawl `.gov.br` | **concluído**: 1.218 municípios, 0 falha de LLM, 403 URLs únicas de símbolo em 368 municípios, US$ 0,20 (D24) |
| AAM (Amazonas) | **concluído**: 62 municípios, 15 símbolos novos, 2 rejeitados pela visão, US$ 0,009 (D28) |
| SECULT-AL | **descartado**: as 102 páginas de município existem, mas todas as imagens apontam para o domínio morto `cultura.al.gov.br`; só sobreviveram miniaturas de 128 px no Wayback (D29) |
| Commons por categoria | **varredura nacional**: 581 itens em 26 UFs (560 na varredura + 21 em AL), 61 recusados pela visão (D29, D31) |
| Biblioteca da AAM | **descartada**: 126 documentos (95 notas técnicas, 27 FPM, 2 revistas, 2 cartilhas), zero sobre símbolo (D28) |
| Atos oficiais | 11 itens em 8 municípios com lei confirmada e link da página; linha "Ato oficial" no card só quando existe (D28) |
| Sidecars locais | em `data/meta/v1` (verdade versionável), com `sha1_origem`, `capturado_em`, `verificacao`, `ato` e `guarda` |
| Acervo versionado | 1.209 SVGs (293 MB) em `data/vetores` + livro-razão (3,3 MB) em `data/ledger` (D22) |
| Guarda | 347 itens de risco alto (348 `pendente`, 279 fora do Commons), 8.889 baixos; vetor tem `espelhos: [commons, git]` |
| R2 | `simbolos-br-cdn` (público) + `simbolos-br-acervo` (**sem domínio**) = 2,62 GB, 26% do free tier |
| Site | **no ar**: landing, `/consultar`, `/cobertura`, `/sobre`, `/contribuir`, 5.571 municípios, 27 estados, portal na raiz |
| Relatos | `/simbolos/contribuir` → Worker + Turnstile + GitHub App: issue com `aguardando-confirmacao`, nada automático (D27) |
| URLs | limpas, sem barra (`build.format: "file"`) e com `link rel=canonical` |
| Deploy | Pages projeto `coletivo`, `coletivo.dev.br` + `www`, deploy manual |
| Repositório | público em `github.com/atelie-dev/simbolos-br`, AGPL-3.0, `.git` de 96 MB (287 MB de SVG comprimem), FUNDING |
| Apoio | GitHub Sponsors ativo; PIX com chave UUID e sem `txid` |
| Pacotes npm/PyPI/Composer | não começaram |

Números públicos: 9.236 itens, 5.130 municípios cobertos (92,1%), 4.579 com
brasão, 4.657 com bandeira. Vetorial por tipo: 573 municípios com brasão em SVG,
636 com bandeira em SVG, 1.209 itens vetoriais. Baldes (contados nos sidecars):
livre 7.557, compartilha 1.331, pendente 348.

## Fontes avaliadas e o veredito

| Fonte | O que é | Veredito |
|---|---|---|
| SECULT-AL | 102 páginas de município com brasão e bandeira | **morta**: todas as imagens apontam para `www.cultura.al.gov.br`, que redireciona para a home; só há miniaturas de 128 px no Wayback (D29) |
| simbolosmunicipais.com.br | "acervo histórico" de uma empresa de Brasília | **cópia**: um brasão era byte-idêntico ao Commons, outro tinha marca d'água da Simbolopedia (MBI), que vende as versões limpas (D29) |
| VDR Bandeiras | loja com 5.952 produtos, um por município | **não é fonte**: arte própria em ~1.302×836, sem licença; serve de mapa de existência |
| Memorial dos Símbolos | site pessoal (webnode) com página por município | **esqueleto**: o Rio de Janeiro tem 92 entradas e só 6 imagens; o resto é `desconhecido.png` |
| Câmara de São José do Hortêncio | símbolos oficiais da câmara | **melhor arte que o Commons**: 799×536 contra 317×302, mesma composição; motivou o `simbolos trocar` (D30) |

## Próximo passo, em ordem

1. **Portão de visão** nos 915 itens antigos marcados `precisa_visao`: o tipo já
   passou pela v2, falta confirmar identidade e qualidade.
2. **`/baixar`**: pacotes por estado e formato, `brasil-livre.zip` (só balde
   livre) e `danfse-192.zip`. É a última rota do plano que falta no site.
3. **`/m/{cod}`** como redirect: `_redirects` do Pages aceita só 2.100 — precisa
   Bulk Redirects na zona ou Worker.
4. **Símbolos dos estados**: os 27 nunca entraram na coleta; a página do estado
   diz isso explicitamente.
5. **`/transparencia`**: já existe número — domínio, ~2,7 GB de R2, egress zero,
   e os 345 itens de risco alto.
6. **Moderação dos relatos**: a fila é o GitHub; falta rotina para ler
   `aguardando-confirmacao`, aplicar e fechar citando o commit.
7. **Lei no sistema da câmara**: o `leis` procura na prefeitura e achou 10 atos
   em 1.218 municípios (0,8%). A câmara é onde a lei municipal costuma estar, e
   o site da AAM dá a URL dela para os 62 do AM — piloto barato.
8. **CI**: ligar o Pages ao GitHub exige gerar o índice no build (depende do
   catálogo e dos PNGs) — decisão à parte.

## Dívidas conhecidas

| Item | Impacto | Prioridade |
|---|---|---|
| Teste só na política de guarda (16 casos) | pipeline ainda sem cobertura | alta |
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
  `data/meta/v1/{tipo}/{cod}.json`; retomada lê sidecar → catálogo → disco.
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
- **`dist` é saída; a verdade mora em `data/`.** Sidecar em `data/meta/v1` é
  versionado; `dist/meta` não existe mais.
- **Purge do CDN é desnecessário no host do R2**: o custom domain responde
  `cf-cache-status: DYNAMIC`, ou seja, o edge não cacheia. Quem guarda o
  `max-age` de 1 h é o **browser** — trocar o contrato do `meta.json` pede
  versão nova (`meta/v2`), não purge.
- **Este repositório tem `core.autocrlf=input`.** Sem `.gitattributes`, git
  converte CRLF em LF no índice e o arquivo de um clone **deixa de bater com o
  `sha256` do sidecar** — o acervo diz "byte a byte" e não é. `data/vetores` está
  como `binary`; `data/meta` e `data/ledger` como `-text`. Conferir com
  `git cat-file blob :arquivo | sha256sum` contra `sha256sum arquivo`.
- **`publicar` não carimba `urls`.** A ordem é `publicar` → `simbolos urls` →
  `r2`. Pular o `urls` deixa o sidecar público sem as três URLs, e o consumidor
  precisa baixar o catálogo inteiro para descobrir onde o arquivo está (aconteceu
  com os 258 importados do crawl).
- **`wrangler deploy` do Worker falha calado quando a saída passa por pipe**: o
  terminal mostra só "Logs were written to …", e o erro real (build, por
  exemplo) está no log. Depois de cada deploy, conferir se apareceu
  "Uploaded … / Deployed …"; se não, ler o log.
- **O Worker é `.js` puro.** Uma anotação TypeScript (`const X: Record<…> = {}`)
  quebra o build com "Expected ; but found :" e o script antigo continua no ar —
  o teste de comportamento é o que revela.
- **`data/vetores` e `dist/embed` têm o mesmo conteúdo por construção.** Quem
  manda é `data/vetores`; `simbolos vetores` recusa sobrescrever sem `--forcar` e
  manda o divergente para `data/vetores/conflito/`.
- **Toda requisição HTTP passa por `rede.py`** — não use `httpx` direto. A
  polidez é por host (1 req/s no padrão): seis prefeituras diferentes em
  paralelo estão certas, seis no mesmo servidor dão 403. O `leis` sonda
  caminhos em série justamente por isso.
- **`robots.txt`: 5xx bloqueia, 404 libera** (RFC 9309). Tratar os dois igual
  erra para um dos lados — e o lado errado é o que quebra a confiança.
- **O UA precisa de contato que exista** (`contato@atelie.dev.br`). O anterior
  apontava para repositório e domínio inexistentes, o que justifica o bloqueio.
- **Página de "símbolos" não cita a lei.** Em AL: 66 páginas, 18 com imagem e
  **0 com ato** — o texto institucional tem ~500 caracteres e não menciona Lei
  nem Decreto, e `achar_ato` devolve `tem_ato: false` corretamente. O crawl é
  caçador de **símbolo**, não de lei; a cadeia lei → PDF → vetor não sai daqui.
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
- **Página de símbolo da prefeitura quase nunca cita a lei.** 1.218 municípios
  processados → 10 atos (0,8%) e **0 PDF**. A norma mora no sistema da câmara,
  não na página que mostra a bandeira; procurar ali é outra coleta.
- **Site de associação de municípios não é acervo de símbolo.** A biblioteca da
  AAM tem 126 documentos (95 notas técnicas, 27 FPM) e **nenhum** fala de
  símbolo. O que a AAM tem de ouro é a página de cada município: imagem,
  prefeitura, câmara, telefone, e-mail. O nome do menu não diz o conteúdo —
  conferir antes de planejar coleta.
- **Dado coletado e não exibido é dívida invisível.** O `ato` estava no
  `leis.jsonl` desde o crawl, com trecho e página, e nunca chegou ao sidecar nem
  ao card: existia e não servia para nada. Derivado que ninguém lê não é ativo.
- **`triar` reconstrói o catálogo do zero** a partir dos jsonl de candidatos.
  Rodar depois de `importar` ou `aam` **apaga** esses itens, que não estão em
  jsonl nenhum. Para preencher lacuna sem perder nada, use `completar`
  (aditivo): ele só toca no tipo que falta.
- **O portão de visão não lia SVG.** `visao.carregar` mandava `image/svg+xml`
  para o modelo, que devolvia `tipo: None` e recusava todo vetor — o melhor
  formato do acervo era o único que o gate nunca aprovava. Agora rasteriza com
  `resvg` antes de perguntar (`visao._rasterizar`).
- **Página de secretaria estadual pode estar viva com imagem morta.** A SECULT-AL
  tem 102 páginas de município, cada uma com `<img>` apontando para
  `www.cultura.al.gov.br`, domínio que hoje redireciona para a home. Conferir o
  `src`, não só o HTML: o texto existe, o arquivo não.
- **Acervo de terceiro pode ser cópia de catálogo pago.** O
  `simbolosmunicipais.com.br` mistura arquivos do Commons (um brasão era
  byte-idêntico) com prévias marcadas da Simbolopedia (MBI, mbi.com.br), que
  vende as versões limpas. Sem licença e sem autor declarado: nunca é fonte.
- **O `.env` é um FIFO do 1Password e para de servir quando a máquina é
  bloqueada.** O sintoma na saída é inconfundível: **100% de rejeição e custo
  US$ 0,0000**. Foi o que aconteceu no meio da varredura nacional, com o
  mantenedor dormindo: 159 recusas falsas, todas refeitas. Rodada longa não pode
  depender desse FIFO — a entrega de segredo para execução unattended está em
  aberto (ver Questões abertas). Se a FIFO morrer no meio, recriar com a
  ferramenta do 1Password (`create_local_env_file`) e refazer o que falhou.
  Desde 2026-11-09, `completar` e `trocar` **param** com `visao.CredencialAusente`
  quando a chave some (antes de começar ou no meio da rodada), em vez de contar
  recusa falsa.
- **`imageinfo` às vezes vem sem `mime`**, e o original era gravado como `.bin`;
  o `publicar` então não sabia se validava SVG ou abria raster. O conteúdo é a
  verdade: farejar com PIL (`completar._mime_real`) e `simbolos reparar` para
  consertar o que já entrou.

## Questões abertas

| Questão | Status |
|---|---|
| Crédito de contribuidor: anônimo por padrão? | recomendado, não decidido |
| Nomes dos pacotes (`@coletivo/…`) | aberto |
| Continuar o crawl oficial nos 1.218 restantes | recomendado (~536 brasões por ~US$ 1) |
| Remover o CEP (campo 61) do BR Code | opcional; menos dado pessoal no QR |
| Nome no BR Code é "FABIO DBATISTA"; trocar por nome comercial | depende do PSP |
| Rendition 192 px para DANFSE | desenhada, não implementada |
| Segredo para rodada longa e unattended | **aberto**: o `.env` é FIFO do 1Password e morre com a máquina bloqueada. O aborto seguro já existe (`visao.CredencialAusente`); falta a entrega que sobrevive ao bloqueio. Candidato: ler a FIFO uma vez no início e exportar para o processo, ou `op run` com service account. Nunca gravar segredo no repositório |

## Registro de marcas/modelos (para não redescobrir)

- **Maritaca**: `S5` (1M ctx), `sabia-4`, `sabiazinho-4`, `S5-br-sp`, `S5-nano`.
  `service_tier: "flex"` = 50%, síncrono, pode dar 429. Batch = 50%, mas um lote
  de 1 requisição ficou >20 min em `in_progress`.
- **Neuralwatt**: `glm-5.3`, `glm-5.3-flash`, `deepseek-v4.1-flash` (+`-flex`),
  `clef-flash` (decisão, só em `POST /v1/systemone`), `kimi-k3`, `qwen3.6`.
- **DeepSeek direto**: descontinuado no projeto.
- **Custo medido**: 10 páginas US$ 0,0009 (Neuralwatt flex) vs R$ 0,0419 (S5
  flex); visão ~US$ 0,00008/imagem.
