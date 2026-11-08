<!-- Context: project-intelligence | Project: simbolos-br | Version: 1.0 | Updated: 2026-11-08 -->

# Living Notes — Símbolos BR

> Estado atual, próximo passo, dívidas e armadilhas. Complementa `PLAN.md` (design)
> e `decisions-log.md` (por quê). Atualizar ao fim de cada bloco de trabalho.

## O que é

Acervo aberto dos brasões e bandeiras dos municípios e estados brasileiros, com
procedência e licença por arquivo, URLs de embed estáveis e pacotes para download.
É o **primeiro acervo do `coletivo.dev.br`**, a divisão de código e dados abertos
do `atelie.dev.br`.

| Host | Papel |
|---|---|
| `coletivo.dev.br` | portal da divisão |
| `coletivo.dev.br/simbolos` | este serviço |
| `simbolos.coletivo.dev.br` | ativos: `/embed/v1/{brasao\|bandeira}/{cod}.{svg,png,jpg}` e `/meta/v1/...` |
| `atelie.dev.br` | o ateliê; assina o projeto em `/sobre` |

Um host **por serviço** para os ativos, e não um `cdn.` compartilhado com
prefixo: o custom domain do R2 liga um host a um bucket, e o bucket é por
serviço (`simbolos-br-cdn`). O próximo acervo entra em `saude.coletivo.dev.br`
com o bucket dele, sem Worker e sem mexer neste. Configurável por `SITE_BASE` /
`CDN_BASE` / `SERVICO_PATH` em `simbolos/config.py` e no `devenv.nix`.

## Estado em 2026-11-08

| Etapa | Situação |
|---|---|
| Catálogo IBGE | pronto: 27 UFs, 5.571 municípios (`data/municipios.json`) |
| Coleta Wikidata + Commons | pronta: 4.353 brasões (78,1%), 4.037 bandeiras (72,5%) |
| Triagem | pronta: `data/_catalogo/catalogo.json` (4.790 municípios com item) |
| Crawl de sites oficiais | piloto em 39 municípios: 44% com símbolo, 3% com ato |
| Publicação local | **concluída**: 8.369 de 8.390 (11 falhas: 3 `svg_inseguro`, 4 `render`, 4 `svg_sem_raiz`), 1,3 GB |
| Sidecars + URLs | 8.379 sidecars em `dist/meta/v1`; 8.379 itens com URL |
| R2 | **no ar**: `simbolos-br-cdn` (público) e `simbolos-br-acervo` (privado) |
| Upload (`simbolos r2` / `acervo`) | implementado e verificado com 6 objetos |
| Domínio `coletivo.dev.br` | **ativo** no Cloudflare; `simbolos.coletivo.dev.br` (CNAME proxiado para `public.r2.dev`) serve o bucket com CSP/nosniff |
| Token Cloudflare | Pages, R2 custom domain, Zone settings, Zone Config e Cache Purge: todos liberados |
| Site | **local**: landing, `/consultar`, `/cobertura`, `/sobre`, 5.571 municípios, 27 estados; portal na raiz em `portal/` |
| Deploy (Pages) | **no ar**: `coletivo.dev.br` (portal) e `/simbolos` (acervo), projeto `coletivo`, deploy manual |
| Repositório | público em `github.com/atelie-dev/simbolos-br` (branch `main`), AGPL-3.0 + README; `.env` fora do índice |
| Pacotes npm/PyPI/Composer | não começaram |

Números do catálogo: brasão 4.353, bandeira 4.037, os dois 3.600, vetorial 577
(13,3% dos brasões), 915 itens precisam de confirmação visual, 3.151 com mais de
um candidato. Baldes: livre 7.101, compartilha 1.220, pendente 69.

## Próximo passo, em ordem

1. **Terminar a publicação** (`simbolos publicar`) e rodar `simbolos urls` para
   carimbar as URLs no catálogo final. A publicação é retomável e mescla o
   catálogo, então pode ser interrompida à vontade. Depois do lote, nesta ordem:
   `publicar` de novo (grava os sidecars de todos os itens a partir do catálogo,
   com `sha256_origem` real), `simbolos fontes` (rebaixa os originais para
   `data/fontes/`, confere o hash e marca divergência) e só então `simbolos urls`.
2. **Portão de visão** nos 915 itens que precisam (`simbolos visao`, motor
   `decisao`), e nos achados do crawl oficial.
3. **Upload para o R2** (`simbolos r2` e `simbolos acervo`) depois de `urls`, e o
   redirect `/m/{cod}`. CDN e cabeçalhos já no ar em
   `simbolos.coletivo.dev.br`; falta só o `acervo` (backup) depois do `fontes`.
4. **Site** (Astro, estático): landing, busca, páginas de município, cobertura,
   downloads. O `/sobre` credita o Ateliê, informa AGPL no código e licença por
   arquivo no acervo.
5. **Pacotes** fino (índice + URL) e gordo (192 px para DANFSE).

## Dívidas conhecidas

| Item | Impacto | Prioridade |
|---|---|---|
| Nenhum teste automatizado | regressão silenciosa no pipeline | alta |
| `publicar` sem paralelismo | ETA ditado por 1 req/s + render sequencial | média |
| 69 itens `pendente` sem alternativa de licença | ficam fora dos downloads livres | baixa |
| Triagem não usa `dHash` | erro de brasão trocado só cai na visão | baixa |

## Armadilhas (custaram tempo de verdade)

- **`python3` não existe no PATH** desta máquina. Sempre `uv run python …`.
- **`resvg` só existe dentro do `devenv shell`**. `publicar` tem preflight e falha
  alto; rodar fora do devenv não publica SVG.
- **Wikimedia responde 429** se baixar rápido. Intervalo de 1 req/s por host,
  backoff exponencial e `Retry-After` — está em `publicacao.baixar`.
- **HTML traz entidade** (`Bras&atilde;o`): regex em texto cru não acha "brasão".
  Usar parser ou normalizar entidades antes.
- **`incategory:` em `list=search` retorna 0** para arquivos sem `srnamespace=6`;
  para listar categoria use `list=categorymembers&cmtype=file`.
- **Wikidata `P41`/`P94` às vezes guarda URL** (`Special:FilePath/…`) em vez de
  título; normalizar com `wikidata.titulo_normalizado`.
- **`S5` gasta o orçamento de saída em raciocínio** e devolve `content: null` com
  `finish_reason: length`. O cliente dobra o teto e repete; tratar `length` como
  truncamento, nunca como resposta.
- **Catálogo não é acervo**: 3 dos 19 links do piloto já estavam mortos. Só a
  publicação (arquivo próprio) impede o acervo de apodrecer.
- **Rendition não é fonte.** Até 2026-11-08 o `publicar` gravava só PNG/JPG de 512
  e descartava os bytes originais — em 2.781 itens a fonte era maior que 460 px,
  então o acervo guardava a versão menor e jogava a boa fora. Agora o original vai
  para `data/fontes/v1/{tipo}/{cod}.{ext}` e o registro carrega `fonte.arquivo` +
  hash; `simbolos fontes` rebaixa a safra antiga, confere o hash e manda divergência
  para `fontes/conflito/` (nunca sobrescreve em silêncio).
- **`dist/catalogo.json` é derivado, não fonte.** A verdade por ativo é o sidecar
  `dist/meta/v1/{tipo}/{cod}.json`, escrito junto com as renditions. Antes, um
  lote interrompido deixava milhares de arquivos sem registro e a retomada
  rebaixava tudo (só existia o catálogo, escrito no fim). Agora a retomada lê
  sidecar → catálogo → renditions em disco, e o catálogo é gravado a cada 200
  itens por `tmp.replace()` (atômico).
- **`/tmp` desta máquina é zram (RAM, 62 GB).** Nada que prove procedência pode
  morar lá: o PDF do ato oficial vai para `data/evidencias/pdf/`.

## Questões abertas

| Questão | Status |
|---|---|
| Quem assina o PIX (PF, CNPJ, coletivo) | aberto |
| Crédito de contribuidor: anônimo por padrão? | recomendado, não decidido |
| Nomes dos pacotes (`@coletivo/…`) | aberto |
| Continuar o crawl oficial nos 1.218 restantes | recomendado (~536 brasões por ~US$ 1) |
| Registrar `coletivo.dev.br` e checar marca na classe de software | pendente |
| Rendition 192 px para DANFSE | desenhada, não implementada |

## Registro de marcas/modelos (para não redescobrir)

- **Maritaca**: `S5` (1M ctx), `sabia-4`, `sabiazinho-4`, `S5-br-sp`, `S5-nano`.
  `service_tier: "flex"` = 50% de desconto, síncrono, pode dar 429.
  Batch (`/api/batches` + `/api/files`) = 50%, mas um lote de 1 requisição ficou
  >20 min em `in_progress`. Cache de prompt: automático, 75% (90% nos S5).
- **Neuralwatt**: `glm-5.3`, `glm-5.3-flash`, `deepseek-v4.1-flash` (+ `-flex`
  ~30%), `clef-flash` (modelo de decisão), `kimi-k3`, `qwen3.6`, `nw-*`.
  Reporta `cost.request_cost_usd` e `allowance_remaining_usd` por requisição.
  `clef-flash` só funciona em `POST /v1/systemone` (não em `/chat/completions`).
- **DeepSeek direto**: descontinuado no projeto; a rota é via Neuralwatt.
- **Custo medido**: 10 páginas saíram por US$ 0,0009 (Neuralwatt flex) contra
  R$ 0,0419 (S5 flex). Portão de visão custa ~US$ 0,00008 por imagem.
