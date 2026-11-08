# Spike de coleta — resultado medido

**Data:** 2026-11-07 · **Escopo:** coleta Wikidata + Commons completa; piloto
`.gov.br` com 5 municípios. Nenhuma estimativa: os números abaixo saíram da API.

## Método

| Coletor | Como | Requisições | Tempo |
|---|---|---|---|
| Wikidata | 1 consulta SPARQL (`P1585` → `P94`/`P41`) | 1 | **2,8 s** |
| Commons (imageinfo) | 7.867 arquivos em lotes de 50 | ~158 | **2 min 54 s** |
| Commons (categorias) | 24 categorias de brasão + 6 de SVG | ~30 | minutos |
| `.gov.br` (piloto) | Firecrawl: busca + scrape | 5 buscas + 6 scrapes | minutos |

## Resultado no catálogo inteiro (5.571 municípios)

| Medida | Municípios | % |
|---|---:|---:|
| **Com brasão** | **4.353** | **78,1%** |
| Com bandeira | 4.037 | 72,5% |
| Com brasão em SVG | 577 | 10,4% |
| **Sem nenhum candidato** | **1.218** | **21,9%** |

De onde vem cada um:

| Fonte | Municípios com brasão | Observação |
|---|---:|---|
| Wikidata `P94` | 3.850 | casamento **exato** por código IBGE |
| Commons por categoria | 3.610 | casamento por nome de arquivo |
| **União** | **4.353** | Commons acrescenta **503** que o Wikidata não tem |

Bandeiras: 4.033 vêm do Wikidata (`P41`); as categorias do Commons acrescentam
**4**. Categoria de bandeira municipal praticamente não existe — bandeira é
problema de Wikidata, não de Commons.

## Licença (candidatos de brasão)

| Balde | Candidatos | % |
|---|---:|---:|
| `livre` (CC0 / domínio público / CC BY) | 7.200 | 84,4% |
| `compartilha` (CC BY-SA) | 1.255 | 14,7% |
| `pendente` (sem licença legível) | 79 | 0,9% |

**84% do acervo é utilizável sem ShareAlike.** O filtro `?licenca=livre` vai ser
útil, mas não é o caso majoritário — bom sinal para adoção.

## Qualidade

- 8.534 candidatos de brasão para 4.353 municípios: **1,96 por município**
  (variantes). A triagem precisa escolher um, não empilhar.
- Formatos: JPEG 3.921 · PNG 3.511 · SVG 938 · GIF 156 · WebP 6 · PDF 2.
- JPEG: largura mediana **282 px**; **1.830 de 3.921 (46,7%) abaixo de 256 px**
  → metade do acervo raster é T1, não T2.
- 342 arquivos com tipo presumido pela categoria (nome não diz se é brasão ou
  bandeira) — fila de revisão humana.

## Amostra estratificada (53 municípios, 2 por UF)

| Medida | Resultado |
|---|---|
| Com brasão | 40 (75,5%) |
| Com bandeira | 41 (77,4%) |
| Com brasão SVG | 10 (18,9%) |

A amostra confirma o catálogo (75,5% vs 78,1%). A diferença no SVG (18,9% vs
10,4%) é variância de amostra pequena, não contradição.

## Piloto `.gov.br` (5 municípios sem cobertura)

| Município | Domínio | Página de símbolos | Ativo | Formato |
|---|---|---|---|---|
| Camaragibe/PE | ✅ | — | logo com slogan | PNG |
| Agudos/SP | ✅ | `/cidade/simbolo` | não isolado | — |
| Belmonte/BA | ✅ | `/simbolos` | `brasao.jpg` | **JPEG** |
| Almeirim/PA | ✅ | `/o-municipio/historia` | `logo-pm-*.png` | PNG |
| São Paulo das Missões/RS | ✅ | — | **falha de rede** | — |

| Agregado | |
|---|---|
| Domínio oficial encontrado | **5/5** |
| Página de símbolos ou seção | **3/5** |
| Ativo de brasão identificado | **2/5** |
| **Vetor (SVG)** | **0/5** |
| Falha de rede (`ERR_TUNNEL_CONNECTION`) | **1/5** |

O melhor caso possível — Belmonte, página `/simbolos`, rótulo "Brasão" — entrega
**JPEG**. Fonte oficial resolve procedência e T4; **não** resolve vetor.

Sobre custo: o contador de créditos do Firecrawl **não se moveu** (1.334 antes e
depois de 11 chamadas). Não foi possível medir custo por chamada; confirmar no
painel antes de rodar em escala.

## Descoberta de domínio por DNS (medido em 2026-11-07)

Amostra aleatória (semente fixa) de **60 municípios** entre os 1.218 sem
cobertura. Três padrões testados por resolução DNS, **sem nenhuma requisição
HTTP**:

1. `{compacto}.{uf}.gov.br` (ex.: `saopaulodasmissoes.rs.gov.br`)
2. `{slug}.{uf}.gov.br` (com hífens)
3. `www.{compacto}.{uf}.gov.br`

| Resultado | |
|---|---|
| Domínio resolvido | **58/60 (97%)** |
| Sem resolução | 2/60 |

O padrão `{compacto}.{uf}.gov.br` respondeu por todos os acertos da amostra.
Consequências:

- **Descoberta de domínio sai do orçamento pago.** Nenhum crédito, nenhuma
  requisição ao servidor, nenhum risco de bloqueio de IP.
- O Firecrawl passa a ser usado só para **buscar a página**, e uma por host.
- Resolver DNS não prova que o site é da prefeitura nem que está no ar — a
  verificação de conteúdo continua obrigatória.

## Extração com Sabiá/S5 (medido em 2026-11-07)

Modelo `S5` (1M de contexto), chave do ambiente `simbolos-br` no 1Password.
Implementado em `simbolos/maritaca.py`; comando `python -m simbolos extrair --url …`.

| Página | Extração | Ativo verificado |
|---|---|---|
| Belmonte/BA `/simbolos` | `/userfiles/image/brasao.jpg`, citação literal | **200 image/jpeg** |
| Agudos/SP `/cidade/simbolo` | thumb 47 KB (original 143 KB), citação da Lei nº 264 | **200 image/jpeg** |

Os dois ativos foram conferidos: o de Agudos é o brasão com listel
"1897 AGUDOS 1898".

**O que o teste ensinou:**

1. **A heurística de regex estava errada, não a página.** Agudos tem
   `Bras&atilde;o` no HTML; regex por `bras` não atravessa entidade HTML.
   Heurística precisa de parser de HTML.
2. **A citação verificável é o que autoriza o dado.** `trecho_que_prova` tem que
   ser substring literal do HTML guardado; sem isso, `aceito=false` mesmo com
   confiança 0,99 declarada.
3. **`ato_oficial` precisa de passe próprio.** Em Agudos a lei estava na página
   (o modelo citou "Lei nº 264" dentro do trecho), mas o campo voltou `null`.
4. **Custo insignificante:** 3 requisições = R$ 0,01 (17,5k tokens em cache).
   1.218 páginas ≈ alguns reais, não dezenas.
5. **`S5` não aceita `temperature=0`** — não há determinismo; a verificação por
   citação substitui o determinismo.

## PDF oficial: manual de marca não serve (medido em 2026-11-07)

Teste em `rioclaro.sp.gov.br/.../MANUAL_DE_IDENTIDADE_VISUAL.pdf`: 53 páginas,
13,8 MB, 74 mil caracteres.

| Etapa | Resultado |
|---|---|
| Páginas sem imagem raster (provável vetor) | **19 de 53** |
| S5 lendo o texto inteiro, buscando a arte do brasão sozinha | `pagina: null`, confiança 0,92 |
| Citação | nenhuma (recusou em vez de inventar) |
| Conferência visual da página vetorial mais promissora (p. 6) | **paleta de cores**, não o brasão |
| `pdftocairo -svg` na página 20 (a que cita o brasão) | 4,5 MB, 167 `path`s, 0 `<text>` — mas é um mockup de aplicação |

**Conclusão:** manual de identidade visual é o manual da *marca da gestão*, que
muda a cada administração. O brasão aparece como elemento dentro da marca, não
como arte isolada. A classe documental certa é a **lei que institui o símbolo**
(com anexo) — que também é a prova que falta para T4.

O comportamento do modelo está correto: quando o alvo não existe, ele devolve
`null` com justificativa, em vez de escolher uma página qualquer.

## Data Ocean: não se aplica

Integra bases estatísticas (IBGE/Censo, Receita/CNPJ, DATASUS, INEP, INMET, TSE,
ComexStat). Não há símbolo, imagem ou ato de instituição nessas bases. Serve para
conteúdo do site, não para o acervo. Registrado como fora de escopo (§13.12).

## A/B de provedores e verificação visual (2026-11-07)

Extração com citação verificada, 3 páginas (2 com brasão, 1 sem):

| Modelo | Acertos | Tokens de saída | Custo medido |
|---|---|---|---|
| `deepseek-chat` | 3/3 | 304 | não reportado |
| `neuralwatt/deepseek-v4.1-flash` | 3/3 | 3.518 | US$ 0,0012 |
| `neuralwatt/glm-5.3` | 2/3 | 3.424 | US$ 0,0062 |
| `maritaca/S5` | 3/3 | 1.206 | R$ 0,0238 |

Custo do Neuralwatt sai da própria resposta (`cost.request_cost_usd`,
`allowance_remaining_usd`), não de tabela. DeepSeek não reporta. O 2/3 do GLM foi
falha de citação (URL respondia 200, trecho não estava no HTML) — o portão
recusou, como deve.

Raciocínio domina a saída: 262 de 363 tokens no GLM 5.3 Flash eram
`reasoning_tokens`. Por isso o teto de saída tem que ser alto — e por isso ele
cobra.

Visão (`glm-5.3-flash` via Neuralwatt), 4 imagens com resposta conhecida:

| Imagem | Esperado | Obtido | Confiança |
|---|---|---|---|
| Agudos/SP brasão | brasao | brasao | — |
| Belmonte/BA bandeira | bandeira | bandeira | 0,95 |
| Belmonte/BA brasão | brasao | brasao | — |
| Camaragibe/PE logo | logo | logo | — |

**4/4**, com descrições específicas (cruz de Santo André, coroa mural, listel
"BELMONTE 1891-1961"). Isso vira portão de tipo no pipeline: imagem só é aceita
no slot `brasao`/`bandeira` se a visão confirmar e a confiança for ≥ 0,6.

Arquivos: `data/_spike/ab-provedores.json`, `data/_spike/visao-glm-flash.json`.

## Custo real em 10 páginas (2026-11-08)

| Rota | Aceitos | Custo | Tempo |
|---|---|---|---|
| `maritaca/S5` + `service_tier: flex` | 6/10 | R$ 0,04185 (faturado) | 52 s |
| `neuralwatt/deepseek-v4.1-flash` + `-flex` | 7/10 | US$ 0,000924 (reportado) | 40 s |

Diferença de ~8× por página. 1.000 páginas ≈ US$ 0,09 no Neuralwatt flex.

Descontos confirmados na doc: flex 50% (síncrono, 429 possível), batch 50%
(assíncrono até 24h), cache 75% na entrada e 90% nos modelos S5 — e eles **não
se multiplicam**.

Batch de teste com 1 requisição ficou `in_progress` por mais de 20 minutos:
mesmo desconto do flex, com latência de horas. Flex ganha.

## Conclusões que mudam o plano

1. **A cobertura vem de graça e é maior do que a estimativa.** 78,1% em ~3
   minutos de API, sem crawl e sem crédito. O gargalo nunca foi o `.gov.br`.
2. **O `.gov.br` vale por procedência, não por volume.** 2/5 ativo, 0/5 vetor.
   Rodar em 1.218 municípios serve para fechar lacuna e subir T4 — não para
   multiplicar cobertura.
3. **Vetor continua sendo PDF.** Nenhum dos 5 sites entregou SVG; o caminho é
   manual de identidade visual e lei que institui o símbolo (§13.5).
4. **Metade do raster é pequeno.** T1 domina; o objetivo de qualidade não é
   "ter imagem", é "ter imagem ≥ 512 px ou vetor".
5. **Bandeira é Wikidata, não Commons.** Não perder tempo com categoria de
   bandeira municipal.
