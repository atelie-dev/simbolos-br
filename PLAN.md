# Símbolos BR — Plano do projeto

> Serviço público, colaborativo e aberto para os brasões e bandeiras dos
> municípios e estados brasileiros: um acervo versionado, uma API/CDN de
> embed, pacotes para download e um fluxo de contribuição que qualquer
> pessoa consegue usar.

**Status:** rascunho para discussão (v0.1) · **Data:** 2026-11-07
**Semente:** `../brasoes-e-bandeiras-do-brasil` (Cristiano Mozena, MIT, 1 commit)
**Ambiente:** `devenv` pronto (Python 3.15, Node 26, resvg, ImageMagick, wrangler)

---

## 1. TL;DR

1. **O produto é a URL.** `https://simbolos.coletivo.dev.br/embed/v1/brasao/3550308.svg`
   tem que funcionar para sempre. Site, downloads e API existem para dar
   contexto e confiança a essa URL.
2. **Uma fonte canônica, renditions derivadas.** Ninguém contribui com três
   arquivos. Contribui-se com o melhor original (SVG de preferência); o
   pipeline gera PNG e JPG. Progresso é medido por *qualidade da fonte*, não
   por contagem de extensões.
3. **Licença em três camadas** — código, metadados e cada imagem. O `MIT` atual
   cobrindo 3.266 imagens sem procedência é o maior risco jurídico do projeto;
   resolvido por exclusão, não por promessa (§10.4).
4. **O dado semente precisa de auditoria antes de virar produto.** 32,6% dos
   arquivos novos são bandeiras gravadas na pasta de brasões; 3.266 arquivos não
   têm fonte; 340 linhas de atribuição não têm arquivo; 17 arquivos não têm
   atribuição.
5. **Infra custa < US$ 1/mês** (Cloudflare + R2). O gargalo é curadoria e
   licenciamento, não servidor — o plano é desenhado em torno disso.
6. **Fase 0 é auditoria e decisões, não código de site.** Publicar um acervo
   com procedência duvidosa como "CC0" custa mais caro do que atrasar duas
   semanas.
7. **Todo arquivo carrega sua própria história** — origem, se é original ou
   derivado e de quê, quem enviou, quem conferiu. Sem isso não há como corrigir,
   contestar ou atribuir corretamente.
8. **O acervo legado não entra.** Decidido: nada é publicado sem procedência
   própria. O arquivo atual tem 689 brasões provados (12,4%) — mas isso é o
   limite do método antigo, não do projeto.
9. **Cobertura vem de enumeração, não de PR.** A categorização do Commons expõe
   5.656 arquivos (teto de ~88% dos municípios). §13 planeja a coleta com
   procedência pronta e mede o rendimento real num spike de 60 municípios antes
   de escalar.

### 1.1 Decisões travadas (2026-11-07)

| Decisão | Escolha | Consequência no plano |
|---|---|---|
| Licença do código | **AGPL-3.0** no serviço, **MIT** nos pacotes cliente | §10.2; quem operar uma cópia alterada tem que publicar as alterações |
| Fontes CC BY-SA | **Aceitar**, com selo visível e filtro nos downloads | §10.3 e §4.6; a API expõe a licença por arquivo; existe pacote "somente livres" |
| Símbolo oficial publicado pela prefeitura | **Aceitar** `LicenseRef-simbolo-oficial-municipal`, sob 4 condições | §13.4; destrava `.gov.br`, T4 e o caminho vetorial; nunca rotulado "livre" nem "domínio público" |
| Os 3.266 sem procedência | **Segurar** até re-originar | §10.4 e §12; reescreve o roadmap (§14): coleta vira caminho crítico |
| Relação com o projeto anterior | **Do zero**, sem contato; inspiração, não linhagem | §10.5; nenhum arquivo dele é usado (verificado: 0 idênticos por hash); pacotes com nome novo (§5.3) |
| Domínio e marca | **`coletivo.dev.br`**, divisão aberta do `atelie.dev.br`; serviço em `/simbolos`; ativos em `simbolos.coletivo.dev.br` | §4.1; ADRs 017 e 018. Troca de host é variável de ambiente (`config.py`), não código |

---

## 2. Objetivo e não-objetivos

### Objetivo

Dar a qualquer pessoa e sistema uma forma confiável, gratuita e permanente de
referenciar o símbolo oficial de qualquer município ou estado brasileiro, com
procedência e licença explícitas, em resolução adequada para tela e documento.

### Não-objetivos (v1)

- Não é enciclopédia nem fonte de história da heráldica (linkamos fontes).
- Não é repositório de mapas, fotos, hinos ou dados socioeconômicos.
- Não tem conta de usuário, comentários, votação ou fórum.
- Não serve imagens arbitrárias nem faz upload público direto sem moderação.
- Não promete 100% de bandeiras: muitos municípios não têm bandeira oficial
  documentada. O denominador do progresso precisa excluir esses casos.

---

## 3. Ponto de partida (medido, não estimado)

Levantamento feito no repositório semente em 2026-11-07.

### 3.1 Acervo

| Métrica | Valor |
|---|---|
| Localidades no catálogo IBGE | 5.571 (5.570 municípios + DF) |
| Arquivos no acervo | 4.325 |
| Localidades com ≥ 1 arquivo | 4.325 (77,6%) |
| Localidades com mais de um formato | **0** |
| Arquivos versionados (1 único commit) | 3.266 JPEG 192×192 RGB |
| Arquivos não versionados | 1.059 |
| Tamanho da árvore / do `.git` | 204 MB / 61 MB |
| SVGs no acervo | 232 (5,4%) |
| Formatos presentes | jpg 3.640 · png 436 · svg 232 · gif 7 · webp 5 · jpeg 5 |

### 3.2 Cobertura por UF

`arq` = localidades com algum arquivo · `novos` = arquivos baixados do
Wikimedia (não versionados) · `band.` = desses novos, os que o nome do arquivo
identifica como bandeira · `svg` = arquivos vetoriais.

| UF | mun. | arq | % | novos | band. | svg |
|---|---:|---:|---:|---:|---:|---:|
| AC | 22 | 21 | 95,5 | 9 | 0 | 6 |
| AL | 102 | 78 | 76,5 | 28 | 14 | 9 |
| AM | 62 | 49 | 79,0 | 23 | 12 | 9 |
| AP | 16 | 10 | 62,5 | 5 | 1 | 4 |
| BA | 417 | 324 | 77,7 | 232 | 36 | 19 |
| CE | 184 | 144 | 78,3 | 57 | 30 | 4 |
| DF | 1 | 1 | 100,0 | 0 | 0 | 0 |
| ES | 78 | 64 | 82,1 | 25 | 4 | 3 |
| GO | 246 | 179 | 72,8 | 104 | 49 | 1 |
| MA | 217 | 111 | 51,2 | 77 | 44 | 8 |
| MG | 853 | 677 | 79,4 | 85 | 26 | 12 |
| MS | 79 | 49 | 62,0 | 23 | 17 | 2 |
| MT | 142 | 95 | 66,9 | 40 | 17 | 5 |
| PA | 144 | 99 | 68,8 | 47 | 18 | 12 |
| PB | 223 | 200 | 89,7 | 25 | 10 | 14 |
| PE | 185 | 124 | 67,0 | 96 | 41 | 8 |
| PI | 224 | 92 | 41,1 | 58 | 31 | 11 |
| PR | 399 | 306 | 76,7 | 159 | 55 | 20 |
| RJ | 92 | 92 | 100,0 | 18 | 4 | 15 |
| RN | 167 | 152 | 91,0 | 53 | 3 | 8 |
| RO | 52 | 44 | 84,6 | 13 | 6 | 1 |
| RR | 15 | 15 | 100,0 | 0 | 0 | 0 |
| RS | 497 | 467 | 94,0 | 58 | 10 | 15 |
| SC | 295 | 245 | 83,1 | 71 | 2 | 17 |
| SE | 75 | 47 | 62,7 | 31 | 6 | 5 |
| SP | 645 | 586 | 90,9 | 78 | 23 | 15 |
| TO | 139 | 54 | 38,8 | 38 | 15 | 9 |
| **Total** | **5.571** | **4.325** | **77,6** | **1.453** | **474** | **232** |

### 3.3 Defeitos de dados que o produto herda

| # | Defeito | Evidência | Impacto |
|---|---|---|---|
| D1 | **Bandeiras (e símbolos estaduais) gravados como brasões** | 474 de 1.453 arquivos novos (32,6%) — ex.: `2701605.png` é `Bandeira_de_Canapi_Alagoas.png`; **`RJ/3304557.svg` é a bandeira do estado, não o brasão do município do Rio** | Endpoint `/brasao/` serve o símbolo errado; erro grave, silencioso e que se propaga por embed |
| D2 | **Procedência desconhecida** | 3.266 JPEGs entraram em um único commit, sem fonte, autor ou licença | Não podem ser publicados como CC0/PD |
| D3 | **Licença declarada indevida** | `LICENSE` MIT cobre imagens de terceiros | Risco de takedown e de má-fé |
| D4 | **Atribuição incompleta e duplicada** | 340 linhas do CSV sem arquivo; 17 arquivos sem linha; 71 linhas duplicadas para os 1.042 arquivos | Requisito de CC BY/CC BY-SA não atendido; créditos repetidos |
| D5 | **Um formato por item, sempre** | 0 localidades com 2+ formatos | Objetivo "todos os formatos" não é upload, é pipeline |
| D6 | **192×192 sem excedente** | 3.266 JPEGs exatamente 192×192, sem vetor | Não serve impressão nem telas grandes |
| D7 | **Acervo sem bandeiras e sem estados** | 0 bandeiras; 0 símbolos estaduais | 27 estados × 2 = 54 itens a criar do zero |
| D8 | **Convenção de proporção conflitante** | Regra diz "192×192 exato" *e* "proporção preservada" — as duas não cabem juntas | Precisa de decisão explícita: conter + padding, nunca esticar |

> Observação importante: o parser de nomes não é infalível (existe
> `Bandeira, Brasão de Feira da Mata.png`). A contagem de 474 é piso, não teto —
> a auditoria da Fase 0 confirma arquivo por arquivo.

### 3.4 O que sobra para publicar

Com a decisão de não usar o acervo legado, o universo publicável no lançamento
passa a ser só o que o projeto baixou e atribuiu por conta própria:

| Grupo | Arquivos | Localidades | % do Brasil |
|---|---:|---:|---:|
| Brasões com atribuição completa | 689 | 689 | **12,4%** |
| Bandeiras com atribuição completa | 353 | 353 | 6,3% |
| **Total publicável (itens distintos)** | **1.042** | **1.042** | **18,7%** |
| Sem linha de atribuição (**retidos**) | 17 | 17 | — |
| Legado sem procedência (**retido**) | 3.266 | 3.266 | — |

Dos 689 brasões, **175 são SVG (25,4%)** — um terço a menos de trabalho do que
parece, e o acervo nasce com um quarto em vetor, que é a métrica que importa.

Consequências diretas:

- O lançamento é **pequeno e verificável**, não grande e duvidoso. A página
  inicial tem que transformar isso em argumento ("100% dos arquivos com fonte e
  licença declaradas"), não em desculpa.
- Os 17 arquivos sem atribuição também ficam retidos. A regra é uma só: sem
  procedência, sem publicação.
- **A caça a fontes vira o caminho crítico** (§12 e §13), não a construção do
  site. Um site bonito com 12% de cobertura não resolve o problema de ninguém.

Esses números descrevem o que o **método anterior** (raspar artigo da Wikipédia)
alcançou. A enumeração de categoria do Commons (§13.1) expõe 5.656 arquivos e um
teto de ~88% dos municípios: a fila abaixo é a lacuna do nosso scrape, não a
lacuna do Commons.

---

## 4. Superfície do produto

### 4.1 Rotas

**Hospedagem (decidido).** `coletivo.dev.br` é a divisão de código e dados abertos
do `atelie.dev.br`; o serviço de símbolos é o primeiro acervo dela.

| Host | Papel |
|---|---|
| `coletivo.dev.br` | portal da divisão (lista os acervos) |
| `coletivo.dev.br/simbolos` | este serviço |
| `simbolos.coletivo.dev.br` | ativos do acervo: `/embed/v1/...` e `/meta/v1/...` — host separado por segurança |
| `atelie.dev.br` | o ateliê; assina o projeto em `/sobre` |

Rotas do serviço (relativas a `/simbolos`):

| Rota | O que é |
|---|---|
| `/` | Landing: o que é, busca, cobertura, embed de exemplo, apoiar |
| `/consultar?q=` | Busca e navegação por código IBGE, município ou estado |
| `/estados` | Lista das 27 UFs com progresso |
| `/estados/{uf}` | Página do estado: brasão, bandeira, municípios, progresso |
| `/municipios/{cod_ibge}-{slug}` | Página canônica do município |
| `/m/{cod_ibge}` | Atalho → 301 para a canônica |
| `/cobertura` | Matriz UF × tipo × tier, lista de faltantes |
| `/baixar` | Pacotes por estado, por formato e completos |
| `/api/v1/...` | JSON estático (ver §5.2) |
| `/contribuir` | Guia, regras, hierarquia de fontes |
| `/contribuir/enviar` | Assistente de envio (Fase 3) |
| `/licencas` | Como funciona o licenciamento por arquivo |
| `/correcoes` | Política de correção, contestação e takedown |
| `/transparencia` | Custos reais, doações, saldo |
| `/sobre` | Quem mantém, independência, contato |

### 4.2 Landing (blocos, na ordem)

1. **Hero** — "Os símbolos de todos os 5.570 municípios do Brasil, em um só
   lugar." + busca grande + número de cobertura ao vivo.
2. **Use agora** — snippet copiável com preview ao vivo:
   seletor de município + tipo + formato → `<img src="…">`, `<picture>`,
   Markdown, HTML e CSS `mask`. O código aparece preenchido, não como exemplo
   genérico.
3. **Cobertura** — barra geral + matriz por estado (ver §4.5) + CTA
   "faltam N municípios em MA".
4. **Por que existe** — DANFSE, prefeituras, jornalismo, educação, apps.
5. **Contribuir** — três cartões: *tenho a imagem*, *conheço a fonte oficial*,
   *posso ajudar com dinheiro*.
6. **Apoiar** — PIX (copia-e-cola + QR) e GitHub Sponsors, com o custo mensal
   real em uma linha.
7. **Confiança** — licença por arquivo, procedência, aviso de não-vinculação
   com governo/IBGE, política de correção.
8. **Rodapé** — API, downloads, GitHub, changelog, status, contato.

### 4.3 Busca

Índice estático, sem backend. 5.571 registros ≈ 220 KB crus, ~60 KB brotli.

- Campos: `codigo`, `nome`, `uf`, `estado`, e uma string normalizada
  (sem acento, minúscula) — `"sao paulo sp"`.
- Casamento: código exato/prefixo → nome exato → prefixo de palavra →
  substring → Levenshtein ≤ 1 para nomes com ≥ 6 letras.
- Sem acento por padrão (`Sao Paulo` → `São Paulo`), ordenado por relevância e
  depois por UF.
- Estado na query devolve o estado *e* seus municípios, agrupados.
- Teclado: `↑ ↓ Enter`, `/` foca a busca.
- Estado da URL: `?q=` compartilhável; resultados renderizados no cliente.
- **Funil**: resultado vazio oferece "não encontramos — peça este símbolo",
  que abre o formulário de contribuição já preenchido com o código.

### 4.4 Página do município

- Brasão e bandeira lado a lado, com fundo xadrez para transparência.
- Nome, UF, código IBGE, link para o IBGE.
- Por formato: tamanho em bytes, dimensões, licença, autor, fonte, data.
- **Procedência visível**: "original da Prefeitura de X (2019)", "vetorizado
  por fulano a partir deste scan", "reduzido de versão maior", "recebido de
  beltrano em 07/11/2026, conferido por cicrano".
- Botões: copiar URL, copiar `<img>`, copiar Markdown, baixar.
- Selo de qualidade (`T1`…`T4`), selo de licença (`CC0`, `CC BY 4.0`, …) e selo
  de revisão (`não revisado` / `verificado`).
- "Ver linhagem" → linha do tempo com hashes e substituições.
- "Melhorar esta imagem" → contribuição pré-preenchida.
- Estado quando não existe: "Ainda não temos" + quanto custa ajudar.
- JSON-LD com `ImageObject` + `license` + `creditText`.

### 4.5 Cobertura — a métrica que não mente

Duas medidas separadas, ambas visíveis:

| Medida | Fórmula | Para que serve |
|---|---|---|
| **Cobertura** | `publicado / (total − inexistente)` | "já serve para a maioria?" |
| **Vetorial** | `tier ≥ T3 / publicado` | "serve para impressão?" |

Tiers por item:

| Tier | Definição |
|---|---|
| T0 | ausente |
| T1 | raster ≤ 256 px |
| T2 | raster ≥ 512 px |
| T3 | vetorial (SVG) |
| T4 | vetorial + fonte oficial verificada |

Estados de disponibilidade: `publicado`, `ausente`, `aguardando_procedencia`,
`inexistente` (documentado como sem símbolo oficial). Só `inexistente` sai do
denominador — e exige evidência registrada.

**`aguardando_procedencia` não é servido.** A decisão de segurar o legado vale
como regra geral: sem fonte e licença identificadas, o item existe na fila e no
backlog, não no CDN. O contador público "N aguardando procedência" é o retrato
honesto do trabalho que falta, e não uma vergonha a esconder.

### 4.6 Download

| Pacote | Conteúdo |
|---|---|
| `por-estado/{UF}-{formato}.zip` | um estado, um formato |
| `brasil-{formato}.zip` | todos, um formato (`svg`, `png`, `jpg`) |
| `brasil-tudo.zip` | todos os formatos + catálogo |
| `brasil-livre.zip` | **só** CC0 / domínio público / CC BY — o pacote de quem não pode lidar com ShareAlike |
| `danfse-192.zip` | JPEG 192×192 gerado pela receita homônima (não é herança do acervo antigo) |

Todo zip inclui `LEIA-ME.txt`, `ATRIBUICOES.csv`, `LICENCAS.csv`,
`PROVENIENCIA.csv` (uma linha por arquivo: origem, natureza, derivado de, quem
enviou, quem conferiu), `catalogo.json` e a versão do acervo (`v2026.11`).
Versões são imutáveis e ficam para sempre; `/baixar` sempre aponta para a última.

Filtro de licença em toda a superfície, com **três baldes** que não se misturam
(decisão travada):

| Balde | SPDX | Entra em `brasil-livre.zip`? |
|---|---|---|
| `livre` | `CC0-1.0`, `LicenseRef-dominio-publico`, `CC-BY-4.0` | sim |
| `compartilha` | `CC-BY-SA-4.0` | não (herda SA) |
| `oficial` | `LicenseRef-simbolo-oficial-municipal` | **nunca** |

`?licenca=livre` e `/baixar` usam esse enum. A página do item mostra o balde, não
só o identificador — quem lê "oficial" precisa entender que **não** é domínio
público.

### 4.7 Apoiar

- **PIX**: chave estática + BR Code copia-e-cola + QR renderizado no build
  (nada de terceiro no caminho). Sem valor sugerido — só transparência de custo.
- **GitHub Sponsors**: tiers simbólicos, sem contrapartida de produto (não
  vender destaque, não vender "verificação").
- `/transparencia`: custo do mês (domínio, storage, e-mail), recebido, saldo,
  e a regra de uso do dinheiro (infra primeiro, depois tempo de curadoria).

---

## 5. Contrato público (o que não pode quebrar)

### 5.1 Embed

```
https://simbolos.coletivo.dev.br/embed/v1/{brasao|bandeira}/{cod_ibge}.{svg|png|jpg}
```

- `cod_ibge` tem 7 dígitos para município e **2 dígitos para estado**
  (`35` = SP). Os espaços são disjuntos por construção.
- Resoluções fixas na v1: `png` 512×512 com fundo transparente, `jpg` 512×512
  com fundo branco, `svg` vetorial normalizado. Sem parâmetro de tamanho na v1
  — `/{cod}@192.jpg` ou `/embed/v2/.../{tamanho}` ficam para a v2, e é
  exatamente por isso que `v1` existe.
- Todos os três formatos existem para todo item publicado: a derivação garante
  isso. Formato inexistente = 404, nunca redirect.
- Código inválido ou não publicado = `404` com `Cache-Control: public,
  max-age=300` (cache negativo curto, para o upload novo aparecer rápido).
- Preferência de formato: sirva `svg` quando puder; `png` para transparência em
  raster; `jpg` para documentos e PDF (DANFSE).

Cabeçalhos:

```
Cache-Control: public, max-age=604800, stale-while-revalidate=604800, stale-if-error=604800
ETag: "<sha256 da rendition>"
Last-Modified: <data de publicação>
Content-Type: image/svg+xml | image/png | image/jpeg
X-Content-Type-Options: nosniff
Access-Control-Allow-Origin: *
Timing-Allow-Origin: *
```

### 5.2 API (estática, cacheável, sem chave)

```
/api/v1/estados.json
/api/v1/municipios.json            (~5.5k registros)
/api/v1/municipios/{cod_ibge}.json
/api/v1/catalogo.json              manifesto completo (licenças + hashes)
/api/v1/cobertura.json             estatísticas
/api/v1/esquema.json               JSON Schema dos anteriores
```

`catalogo.json` é a peça de integridade: permite a um consumidor verificar
sha256 de tudo que baixou e montar sua própria réplica. Cada entrada expõe o
mesmo `meta.json` público do acervo (origem, natureza, licença, linhagem) mais
os hashes das renditions — ou seja, a API não esconde nada que o repositório
não diga.

### 5.3 Pacotes

| Pacote | Papel | Licença |
|---|---|---|
| `@simbolos-br/simbolos` (npm) / `simbolos-br` (PyPI/Composer) | **Fino**: índice + construtor de URL + download sob demanda com cache local | MIT |
| `@simbolos-br/danfse` | **Gordo**: JPEG 192×192 embutidos, para PDF offline | MIT |
| `simbolos.get(uf, codigo)` | shim **opcional** de assinatura compatível com a lib anterior, para quem quer migrar sem tocar no código | MIT |

Decisão travada: **nome próprio**, sem herdar o namespace nem publicar atualização
nos pacotes existentes. O shim existe por conveniência de quem já usa uma API
parecida, não para reivindicar continuidade. Os pacotes são MIT; o serviço é
AGPL (§10.2) — quem consome a API não é afetado pela AGPL, só quem opera uma
cópia modificada do serviço.

---

## 6. Modelo de dados e proveniência

Cada item publicado carrega um `meta.json` que responde, sem consultar nada
externo: **de onde veio, quem trouxe, quem conferiu, que licença tem, se é
original ou derivado — e de quê**. Isso não é burocracia: é o que permite
publicar, corrigir, contestar e provar.

### 6.1 Estrutura

```
data/
  estados.json                 # 27: codigo(2), uf, nome, regiao, slug
  municipios.json              # 5.571: codigo(7), uf, nome, slug, nome_norm
  aliases.json                 # códigos extintos/renomeados -> canônico (301)
  fontes/v1/{tipo}/{cod}.{ext} # original baixado, byte a byte (gitignored, backup no R2)
  evidencias/pdf/{cod}.pdf     # ato oficial que instituiu o símbolo (gitignored)
  assets/                      # contribuição (a fazer): original + meta por asset
    3550308/
      brasao/
        fonte.svg              # arquivo canônico (extensão = tipo real)
        meta.json              # fonte da verdade (este documento)
      bandeira/
        fonte.png
        meta.json
dist/                          # build, nunca versionado
  embed/v1/{tipo}/{cod}.{svg,png,jpg}   # o que é servido (contrato público)
  meta/v1/{tipo}/{cod}.json             # sidecar: fonte da verdade do item
  catalogo.json                # agregado derivado dos sidecars
  artefatos.ndjson             # livro-razão de todo artefato já publicado
  cobertura.json
  indice-busca.json
```

### 6.2 `meta.json`

```json
{
  "schema": 1,
  "codigo_ibge": "3550308",
  "tipo": "brasao",
  "status": "publicado",

  "fonte": {
    "arquivo": "fonte.svg",
    "sha256": "9f2c1d…",
    "mime": "image/svg+xml",
    "bytes": 184320,
    "largura": 512,
    "altura": 618,
    "natureza": "original",
    "derivada_de": null,
    "ferramenta": null
  },

  "origem": {
    "canal": "prefeitura",
    "url": "https://www.prefeitura.sp.gov.br/…/brasao.svg",
    "titulo": "Brasão do Município de São Paulo",
    "autor": "Prefeitura de São Paulo",
    "publicado_em": "2019-03-12",
    "obtido_em": "2026-11-07",
    "ids": {
      "wikidata": "Q174",
      "commons": "File:Brasão de São Paulo.svg",
      "ato": "Lei Municipal 14.123/2019"
    }
  },

  "licenca": {
    "spdx": "CC0-1.0",
    "url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "atribuicao": "Prefeitura de São Paulo",
    "restricoes": []
  },

  "procedencia": { "estado": "completa" },

  "submissao": {
    "por": { "tipo": "github", "id": "fulano" },
    "em": "2026-11-07",
    "via": "pr",
    "issue": 42,
    "consentimento": { "versao": "1", "em": "2026-11-07" }
  },

  "revisao": {
    "por": { "tipo": "github", "id": "beltrano" },
    "em": "2026-11-08",
    "nivel": "verificado_oficial",
    "nota": "confere com o ato publicado no DOM"
  },

  "qualidade": { "tier": "T4", "notas": "vetor oficial" },

  "rendicoes": {
    "receita": "padrao-v1",
    "pipeline": "simbolos@0.1.0 resvg@0.49.0 imagemagick@7.1.2 oxipng@10.2.1 jpegoptim@1.5.6",
    "geradas_em": "2026-11-08"
  },

  "historico": [
    {
      "em": "2026-11-07", "acao": "criado",
      "por": { "tipo": "seed", "id": "cristianomzn" },
      "sha256": "a1b2c3…", "nota": "importado da semente"
    },
    {
      "em": "2026-11-08", "acao": "substituido",
      "por": { "tipo": "github", "id": "fulano" },
      "sha256_anterior": "a1b2c3…", "sha256": "9f2c1d…",
      "motivo": "vetor oficial em melhor resolução"
    }
  ]
}
```

**Estado da implementação (2026-11-08):** o sidecar que o pipeline grava hoje
implementa um **subconjunto** deste schema — sem `submissao`, `revisao`,
`historico`, `natureza` nem `ferramenta`. Os campos reais são:

| Campo | O que é |
|---|---|
| `codigo_ibge`, `uf`, `municipio`, `tipo` | identidade |
| `origem` | URL direta do upload no Commons |
| `titulo_commons` | `File:…`, derivado da URL na captura; é a chave da conferência |
| `licenca`, `balde`, `autor` | licença em camadas (§6.3) |
| `estado`, `formato_origem` | `publicado` / mime, ou `svg` |
| `sha256_origem`, `sha1_origem`, `bytes_origem` | identidade dos bytes capturados; o `sha1` é o que a API do Commons publica, então confere **sem baixar** |
| `capturado_em`, `captura_fonte` | quando os bytes foram capturados (`relogio` agora, `mtime` no preenchimento retroativo) |
| `fonte` | `{arquivo, bytes, sha256, sha1}` — só no raster; no SVG o publicado é a fonte, byte a byte |
| `rendicoes` | `{png, jpg[, svg]}` com bytes e sha256 |
| `urls` | as três URLs públicas |
| `verificacao` | `{em, estado, sha1_commons[, titulo_atual]}` — a última conferência |
| `guarda` | `{espelhos, risco, motivo}` — quantas casas independentes guardam o item |

`data/meta/v1/…` é a verdade e é versionada; `dist/` é saída e pode ser apagada.

### 6.3 Semântica dos campos

| Bloco | Campo | Papel |
|---|---|---|
| — | `status` | disponibilidade: `publicado` · `ausente` · `aguardando_procedencia` · `inexistente` |
| — | `procedencia.estado` | insumo do status: `completa` · `pendente` (`pendente` ⇒ `aguardando_procedencia`, nunca servido) |
| `fonte` | `sha256` | identidade do arquivo; é o que liga tudo (dedup, histórico, renditions) |
| `fonte` | `natureza` | **como este arquivo nasceu** (ver 6.4) |
| `fonte` | `derivada_de` | `{sha256}` do artefato pai no projeto, ou `{url}` quando o pai é externo |
| `fonte` | `ferramenta` | nome + versão do que converteu (`potrace 1.16`, `pdftocairo 25.02`, `Inkscape 1.3`) |
| `origem` | `canal` | `prefeitura` · `estado` · `wikimedia` · `acervo-legado` · `outro` |
| `origem` | `autor` | **titular do direito** — não é quem enviou; `null` só quando `canal = acervo-legado` |
| `origem` | `ids` | wikidata / commons / ato oficial: permitem reencontrar a fonte |
| `licenca` | `spdx` | `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `LicenseRef-dominio-publico`, `LicenseRef-simbolo-oficial-municipal`, `NOASSERTION`, `NONE` |
| `submissao` | `por` | **quem enviou** (ver 6.5) |
| `revisao` | `nivel` | `nao_revisado` · `revisado` · `verificado_oficial` |
| `historico` | — | append-only: toda substituição rastreável e reversível |

Três identidades que **nunca** se confundem: `origem.autor` (direito autoral),
`submissao.por` (quem trouxe) e `revisao.por` (quem conferiu). Misturar as três é
o erro que torna a atribuição de CC inútil.

### 6.4 Natureza do arquivo (a pergunta "foi gerado?")

| `natureza` | Significado | Efeito |
|---|---|---|
| `original` | obtido como está (download, scan, upload) | tier pela resolução |
| `exportado` | extraído de outro formato por ferramenta (PDF→PNG, CDR→SVG) | declarar `ferramenta` |
| `vetorizado` | traçado a partir de um raster (potrace, image trace) | tier T3, mas notas registram que não é o vetor oficial |
| `reconstruido` | redesenhado a partir de descrição/lei por uma pessoa | **obra nova do desenhista** → licença é dele, não do município |
| `recortado` | recorte/correção de outro arquivo | apontar `derivada_de` |
| `reduzido` | reduzido de uma versão maior | apontar `derivada_de` quando conhecido |
| `ampliado` | aumentado (upscale) | tier T1, marcado para substituição |
| `indeterminada` | não se sabe | usado só no legado; contador público deve tender a zero |

`reconstruido` é o caso juridicamente mais delicado: um brasão redesenhado por
um voluntário é obra do voluntário. Sem esse campo, o projeto atribuiria a
licença errada a uma obra protegida.

### 6.5 Identidade e privacidade

```json
"por": { "tipo": "github", "id": "fulano" }
"por": { "tipo": "formulario", "id": "sha256:8ac1…" }
"por": { "tipo": "seed", "id": "cristianomzn" }
"por": { "tipo": "importacao", "id": "lote-prefeituras-2027-01" }
"por": { "tipo": "anonimo", "id": null }
```

- Formulário **nunca** grava e-mail no repositório: grava `sha256` truncado do
  e-mail como identificador estável, e o contato fica fora do git.
- Nome público é opcional; sem opt-in, a submissão é anônima.
- `consentimento` registra a versão dos termos aceitos na hora do envio (LGPD:
  prova de consentimento, e permite migrar a base se os termos mudarem).
- `por` aparece na página do item e na página de contribuidores — crédito é
  parte do produto, não um extra.

### 6.6 O que fica no git (e o que não fica)

| Artefato | No git? | Por quê |
|---|---|---|
| arquivo canônico (`fonte.*`) | **sim** | é o bem revisável e forkável |
| `meta.json` | **sim** | muda por contribuição, diff pequeno e legível |
| renditions (png/jpg 512) | **não** | determinísticas: `sha256(fonte, receita, pipeline)` basta |
| hashes das renditions | gerado em `dist/catalogo.json` | integridade sem churn |
| `dist/artefatos.ndjson` | gerado | livro-razão de tudo já publicado |

Regra: **o git guarda o que uma pessoa decide; o build guarda o que uma máquina
deduz.** Assim um PR que troca um brasão mostra 2 arquivos, não 5, e o histórico
permanece legível.

`dist/catalogo.json` traz, por rendition:

```json
{ "sha256": "77aa…", "mime": "image/png", "bytes": 41233,
  "largura": 512, "altura": 512,
  "gerado_de": "9f2c1d…", "receita": "padrao-v1", "em": "2026-11-08" }
```

Qualquer consumidor consegue então responder localmente: "este PNG que eu baixei
é o derivado oficial deste SVG, gerado por esta receita" — e verificar o hash.

### 6.7 Regras de validação

- `fonte.sha256` tem que bater com o hash real do arquivo.
- `natureza` fora de `original` exige `derivada_de` **ou** `ferramenta`.
- `derivada_de.sha256` precisa existir no livro-razão (ou vir com `url`).
- `reconstruido` exige licença que aponte para o desenhista.
- `spdx` em `NOASSERTION`/`NONE` marca `procedencia.estado = "pendente"`, e o
  build deriva `status = "aguardando_procedencia"` — **não é servido**, não
  entra em pacote nenhum e não conta como cobertura. Fica visível como fila.
  Foi essa a decisão sobre os 3.266 (§10.4), e ela vale para todo mundo: uma
  exceção abriria a porta para a próxima.
- `submissao.por.tipo` e `revisao.por.tipo` em enum fechado.
- `historico` nunca é reescrito: só append; CI falha se um commit alterar linha
  antiga (detectado comparando com o JSON anterior).

---

## 7. Pipeline

### 7.1 Estágios

```
importar → validar → sanear → renderizar → hashear → publicar → indexar
   │          │         │          │           │         │         │
 migração   schema    SVG      resvg+IM     sha256      R2      catálogo,
 semente    + regras  limpeza  512/1024     + dHash    + purge  busca, zips
```

1. **Validar** (falha o build, nunca "avisa e segue")
   - código IBGE existe no catálogo e a UF bate;
   - magic bytes batem com a extensão e com o `mime` declarado;
   - SVG: parseia, tem `viewBox` (ou largura/altura), ≤ 1 MB depois do svgo,
     sem `<script>`, sem atributos `on*`, sem `<foreignObject>`, sem referência
     externa (`http`, `xlink:href` para fora, `url(http…)`);
   - raster: ≥ 256 px no lado menor para T2; < 96 px rejeitado;
   - **renderização limpa**: `resvg` com saída de erro não vazia = aviso
     obrigatório no PR. Um SVG com `path` inválido renderiza *incompleto* sem
     falhar — descoberto no acervo real (`RJ/3304557.svg`);
   - `meta.json` válido contra o schema, `spdx` na lista permitida, `origem.url`
     e `origem.autor` presentes — `null` só é aceito com
     `canal = acervo-legado`;
   - proveniência coerente (§6.7): hash confere, `natureza` justificada,
     `derivada_de` resolvível, `reconstruido` com licença do desenhista;
   - `LicenseRef-simbolo-oficial-municipal` exige `origem.canal = "prefeitura"`,
     domínio da própria prefeitura em `origem.url`, `coleta.metodo = "govbr"` e
     `revisao.nivel = "verificado_oficial"`; faltando qualquer um, o build
     rebaixa para `NOASSERTION` e o item vai para a fila — não publica;
   - `historico` é append-only (CI compara com a versão anterior e falha se
     uma linha antiga for reescrita);
   - duplicata: sha256 igual a outro item = erro; dHash com distância ≤ 4 de
     outro município = *aviso* (provável brasão errado, erro clássico de
     Wikipédia);
   - **denylist do legado**: se o `sha256` estiver em `data/_legado/indice.json`,
     o build exige confirmação da fonte primária antes de publicar (§10.4). Não
     é proibição — o mesmo original público pode gerar bytes iguais —, é
     confirmação obrigatória;
   - **tipo confirmado por visão**: `simbolos.visao.verificar` classifica a
     imagem; `tipo` tem que bater com o slot e `confianca ≥ 0,6`. Divergência vai
     para revisão com a descrição anexada (§13.12);
   - **sem marca d'água e com fundo limpo**: `marca_dagua = true` reprova o item;
     `fundo != limpo` manda para segmentação antes de publicar (§13.12).
2. **Sanear** — SVGO com preset conservador (sem mexer em `viewBox`), remoção
   de metadados do Inkscape, normalização de `width/height`.
3. **Renderizar** — `resvg` a 1024 px → downscale para 512 (anti-aliasing
   melhor); `contain` com 2% de respiro em canvas quadrado (**nunca esticar**);
   JPG achatado em branco, sRGB, quality 88, progressivo; `oxipng`/`jpegoptim`;
   sem EXIF/ICC.
4. **Hashear** — sha256 do binário, dHash 64 bits para deduplicação perceptual.
5. **Publicar** — upload content-addressed no R2 (pula o que já existe),
   atualiza ponteiros de alias, purge de cache em lote.
6. **Indexar** — `catalogo.json`, `cobertura.json`, índice de busca, sitemap,
   OG images.

Determinismo importa: mesmas entradas + mesmas versões de ferramenta = mesmos
hashes. As versões estão travadas no `devenv`.

### 7.2 CLI

```
simbolos coletar …       # commons, wikidata, commons-search, govbr, pdf (§13.9)
simbolos triar           # tipo, tier, licença, dedup, colisão de nome
simbolos revisar         # fila humana: CSV + página local
simbolos validar         # regras acima (roda em PR)
simbolos renderizar      # renditions em dist/render
simbolos publicar        # R2 + purge (--dry-run por padrão)
simbolos pacotes         # zips versionados
simbolos catalogo        # JSON da API + índice de busca + sitemap
simbolos cobertura       # relatório e matriz
```

### 7.3 CI

- **PR**: `validar` + dry-run + comentário automático (arquivos, tiers,
  licenças, avisos de duplicata). Preview do site com os arquivos do PR.
- **merge em `main`**: valida → renderiza → publica → purge → deploy do site.
- **tag mensal `vAAAA.MM`**: gera zips, GitHub Release, publica pacotes,
  arquiva o manifesto. Releases nunca são reescritas.

---

## 8. Stack

Escolhido para ser estático de ponta a ponta: sem banco, sem servidor de
aplicação, sem custo ocioso.

| Camada | Escolha | Por quê |
|---|---|---|
| Site | **Astro** (SSG) | 5.6k páginas pré-renderizadas, ~0 JS por padrão, MDX para páginas legais, ótimo Lighthouse |
| Busca | índice JSON + matcher próprio (~3 KB) | 5.5k linhas não justificam motor de busca |
| Imagens | **resvg** + ImageMagick + oxipng/jpegoptim | determinístico, rápido (24 ms/crest), sem browser headless |
| Pipeline | **Python 3.15** + uv + pydantic + Pillow | validação por schema, fácil de contribuir |
| Storage | **Cloudflare R2** | egress zero; o custo dominante de um CDN de imagens |
| CDN | Cloudflare (domínio próprio no bucket) | cache, purge por URL, WAF, analytics sem cookie |
| Site hosting | Cloudflare Pages | grátis, deploy por CI, preview por PR |
| Upload (Fase 3) | Workers + Turnstile + fila em Issues | sem admin UI para construir e manter |
| Ambiente | **devenv** | reprodutível; versões travadas = hashes estáveis |

> `r2.dev` público não serve para produção (sem cache e com rate limit). O
> bucket precisa de domínio próprio (`simbolos.coletivo.dev.br`) atrás do Cloudflare.

---

## 9. Segurança

O acervo aceita SVG de terceiros. SVG é executável — essa é a superfície de
ataque real do projeto.

| Vetor | Mitigação |
|---|---|
| SVG com `<script>` / `on*` / `<foreignObject>` | Rejeitado no `validar` + SVGO + allowlist de elementos no render |
| SVG servido de origem confiável | `simbolos.coletivo.dev.br` separado do site; `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox`; `nosniff` |
| Referência externa em SVG (tracking, SSRF) | Bloqueio de `http(s)://` e `url()` externo; nada de render server-side de URL |
| Upload malicioso / spam | Turnstile, limite de tamanho, moderação humana, sem publicação automática |
| Zip bomb / pixel flood | Limite de bytes e de dimensão antes de abrir com Pillow |
| Abuso de hotlink / egress | Cloudflare na frente, alerta de pico, rate limit de borda se necessário |
| Poisoning de dado (brasão errado) | dHash, revisão em PR, "denunciar este arquivo", purge rápido na correção |
| Dependência comprometida | lockfiles, `devenv.lock`, Dependabot, sem pós-install de terceiros |

---

## 10. Licenciamento e direito

### 10.1 O que a lei realmente diz

- **Lei 9.610/98, art. 8º, IV**: não são protegidos "os textos de tratados ou
  convenções, leis, decretos, regulamentos, decisões judiciais e demais atos
  oficiais". Um brasão instituído por lei municipal é, na prática, ato oficial —
  mas o alcance do dispositivo é sobre *textos*, não sobre arte, e não há
  jurisprudência pacífica para o desenho do brasão.
- **O desenho concreto é obra de alguém.** O vetor que um wikipedista traçou, o
  scan que uma prefeitura publicou, a arte que um ilustrador fez: cada um tem
  autor e licença própria.
- **CC BY-SA é ShareAlike.** Uma PNG derivada de um SVG CC BY-SA é adaptação e
  herda a licença. Isso tem que estar escrito, não implícito.
- **Lei municipal pode restringir uso** do símbolo (ex.: exigir autorização,
  vedar uso comercial ou publicitário) — restrição distinta de copyright.
- **Sui generis de banco de dados não existe no Brasil**, então organizar o
  acervo não cria direito sobre os arquivos.

### 10.2 As três camadas

| Camada | Licença | Status |
|---|---|---|
| Código do serviço | **AGPL-3.0-or-later** | decidido |
| Pacotes cliente (npm/PyPI/Composer) | **MIT** | decidido |
| Metadados e dataset (nomes, códigos, manifesto, estatísticas) | **CC0-1.0** | recomendado |
| Cada imagem | **a licença da fonte**, por arquivo, em SPDX | decidido |
| Renditions derivadas | herdam a licença da fonte | decidido |
| Pacotes (zip) | coleção: cada arquivo mantém sua licença | decidido |

AGPL no serviço e MIT nos pacotes é uma combinação coerente: a biblioteca que
alguém embute num produto fechado não impõe nada; o serviço que alguém opera
modificado tem que devolver as modificações. O acervo em si nunca é relicenciado
pelo projeto — a licença de cada imagem é a da fonte.

### 10.3 Política editorial de licença

- **Preferência:** domínio público / CC0 / ato oficial da prefeitura.
- **Aceito:** CC BY 4.0 (com atribuição exibida).
- **Aceito com marcação (decidido):** CC BY-SA 4.0 — selo visível no item, na
  API (`licenca.spdx`) e no embed documentado; filtro `?licenca=livre` na busca e
  na API; pacote `brasil-livre.zip` sem nenhum BY-SA; aviso de que derivados
  herdam ShareAlike. Sem isso, aceitar BY-SA silenciosamente seria pior do que
  recusar.
- **Aceito como categoria própria (decidido):**
  `LicenseRef-simbolo-oficial-municipal` (§13.4) — não é licença livre, não é
  domínio público e não entra em `brasil-livre.zip`. Aparece como balde
  `oficial`, com as quatro condições de captura registradas no `meta.json`.
  Serve para símbolo publicado pela **própria** prefeitura, nunca para
  reprodução de terceiro.
- **Não aceito:** "todas as imagens da internet", cópia sem fonte, marca d'água
  de terceiro, arte de banco de imagens, e qualquer arquivo cuja origem não
  possa ser capturada com URL + data + hash.
- **Cada arquivo** mostra: licença, autor, link da fonte, data de obtenção.
- **Contestação**: qualquer pessoa (inclusive a prefeitura) pede correção ou
  remoção por formulário; prazo de resposta publicado; remoção imediata em caso
  de dúvida razoável, decisão registrada depois.
- **Aviso permanente**: o projeto não é afiliado ao IBGE nem a qualquer governo;
  o uso do símbolo não implica endosso oficial.

### 10.4 Os 3.266 arquivos legados: não entram

Decisão travada: **nada do acervo legado é publicado.** Não por excesso de zelo,
mas porque procedência desconhecida sob `MIT` é exatamente o erro que o projeto
não pode repetir — e porque não há como provar a origem de um único arquivo
daquele conjunto.

O que fazemos com eles:

| O que | Onde | Por quê |
|---|---|---|
| **Não** os bytes | — | sem fonte, sem licença, sem publicação |
| Só o manifesto | `data/_legado/indice.json` | `{codigo: {sha256, bytes, largura, altura}}` — diz *quais* 3.266 municípios precisam de fonte, que é o backlog real |
| Denylist por hash | pipeline (§7.1) | se um PR trouxer bytes idênticos, o build pede confirmação da fonte primária |

O denylist é **aviso bloqueante, não proibição**: baixar o mesmo original público
que ele usou pode produzir bytes idênticos, e isso é legítimo. O que não pode é
um arquivo entrar sem que alguém diga de onde veio. O `sha256` transforma "acho
que é dele" em pergunta objetiva.

> A licença `LicenseRef-simbolo-oficial-municipal` **não reabre o legado**: a
> condição 4 de §13.4 exige URL de captura, e esses arquivos nunca tiveram uma.
> Aceitar símbolo oficial é aceitar símbolo com origem rastreável — o legado
> continua sem origem.

`indice.json` também resolve a priorização: os estados com mais itens no legado
são os que mais rápido aumentam a cobertura quando re-originados — e é isso que
a Fase 0 deve publicar como fila de trabalho, não como acervo.

### 10.5 Independência do projeto anterior

Decisão travada: começar do zero, sem contato e sem aviso — o projeto anterior
foi **inspiração, não linhagem**.

Isso é seguro porque foi verificado, não presumido: comparando os hashes dos
4.325 arquivos, **0 dos 1.059 baixados pelo nosso script é idêntico a algum dos
3.266 dele**. Os nossos vieram da API da Wikipédia, com URL e licença registradas
no `atribuicoes-wikimedia.csv`; os dele vieram de lugar nenhum registrado. Não há
obra derivada, não há obrigação de licença, não há o que atribuir.

Regras que decorrem disso:

- Nenhum arquivo, script ou dado dele é reutilizado. Os scripts de coleta são
  nossos e serão reescritos no repositório novo.
- Nenhum pacote é publicado nos namespaces dele; nomes próprios (§5.3).
- Nenhum texto sugere sucessão, endosso ou continuidade. Se um dia houver
  crédito, será como "inspiração" em `/sobre` — cortesia opcional, não obrigação,
  e nunca apresentada como origem dos dados.
- O `LICENSE` MIT que cobre as imagens dele continua sendo um problema dele. Não
  copiamos o erro: aqui nenhuma licença de projeto cobre imagem de terceiro
  (§10.2).

---

## 11. Contribuição

### 11.1 Escada de esforço (quanto menor, melhor)

| Nível | Quem | O que faz | Fase |
|---|---|---|---|
| 1 | qualquer pessoa | Formulário web: escolhe município, arrasta arquivo, informa link da fonte, aceita a licença | **2** |
| 2 | quem tem GitHub | PR com `fonte.svg` + `meta.json` (o bot gera o `meta.json` a partir de um formulário no PR) | 1 |
| 3 | prefeitura / arquivo público | Envia ZIP por e-mail/formulário; curador importa em lote | **1** |
| 4 | dev | Script, correção de pipeline, novo formato | 0 |

Com o legado fora, contribuir **é** o caminho de crescimento — não uma fase
posterior. Por isso o nível 1 sobe para a fase 2 e o import em lote (nível 3)
entra já na fase 1: uma prefeitura que manda um ZIP pode valer mais que cem PRs.

### 11.2 Hierarquia de fontes

1. Ato oficial / site da prefeitura / diário oficial (T4)
2. Arquivo público estadual, instituto histórico, universidade
3. Wikimedia Commons / Wikipédia **com licença e autor identificados**
4. Reproduções de terceiros — só com licença explícita

O acervo legado saiu da hierarquia: não é fonte, é dívida (§10.4).

O formulário pede o nível, não só a URL. Isso alimenta o selo de verificação.

### 11.3 Moderação

- Fila = Issues do GitHub (labels: `novo`, `correcao`, `licenca`, `duplicata`).
- Runbook com checklist de 5 minutos: código confere, licença declarada, imagem
  é o símbolo certo, qualidade aceitável, sem duplicata.
- SLA publicado: primeira resposta em 7 dias; correção de erro factual em 72 h.
- Pelo menos dois moderadores com permissão de merge (bus factor).

---

## 12. Migração (Fase 0, em detalhe)

Esta seção é o **bootstrap**: parte do que já baixamos para acertar catálogo,
proveniência e as regras de classificação. O volume, porém, vem da coleta por
enumeração (§13) — o passo 4 abaixo vira um subconjunto do coletor `commons`.

Não é "importar a semente": é **importar só o que tem procedência** e transformar
o resto em fila de trabalho. Ordem de execução — cada passo é verificável:

1. **Congelar a semente.** `git tag semente-2026-11` no repositório original.
   Ela é referência histórica, não fonte de dados.
2. **Catálogo IBGE novo.** Estados (2 dígitos) + municípios (7) + slugs +
   normalização sem acento + `aliases.json`. O JSON atual tem 5.571 entradas e
   serve de conferência.
3. **Índice do legado, sem os bytes.** Gerar `data/_legado/indice.json` com
   `{codigo: {sha256, bytes, largura, altura}}` para os 3.266. Nenhum arquivo é
   copiado (§10.4). Serve de backlog e de denylist.
4. **Importar os 1.059 baixados por nós** → `meta.json` para cada um:
   - tipo (`brasao`/`bandeira`) pelo nome no CSV + revisão humana dos ambíguos;
   - `origem.canal = "wikimedia"`, com `url`, `autor` e `licenca.spdx`
     (`CC-BY-SA-4.0` ou o que o CSV indicar) do próprio CSV;
   - `fonte.natureza = "original"`;
   - `submissao.por`: `{tipo:"importacao", id:"wikimedia-2026-11"}`, porque
     quem baixou foi o script — não inventar um humano;
   - `revisao.nivel = "nao_revisado"` até alguém conferir.
5. **Separar o que é o quê.** 353 bandeiras saem de `brasao/` para `bandeira/`;
   689 brasões ficam. Onde o artigo só tinha bandeira, o município volta a ser
   "faltante de brasão" — que é a verdade.
   Regra para **colisão de nome**: município e estado homônimos (Rio de Janeiro,
   São Paulo) fazem o matcher aceitar o símbolo estadual. Rejeitar arquivo cujo
   `sha256` seja igual ao do símbolo do próprio estado, e arquivo cujo nome
   contenha o nome do estado com `estado`/`state` e não contenha o do município.
6. **Fechar os buracos de atribuição.** 17 arquivos sem linha no CSV: buscar a
   URL de origem ou reter. 340 linhas sem arquivo: descartar. 71 linhas
   duplicadas: deduplicar antes de gerar `ATRIBUICOES.csv`.
7. **Reprocessar.** Os 175 SVGs viram T3 e geram PNG/JPG de 512. Ganho de
   qualidade sem nenhuma contribuição externa.
8. **Publicar o relatório de abertura** (`/cobertura` + `data/_auditoria/`):
   689 brasões, 353 bandeiras, 3.283 aguardando procedência, e a fila por
   estado ordenada por impacto. É a prova de honestidade e o backlog público.
9. **Só então** ligar o domínio.

Números de saída da Fase 0 com o bootstrap apenas: **1.042 itens publicados
(18,7%)**, sendo **689 brasões (12,4%)** e 175 vetores (25,4% dos brasões);
**3.283 itens na fila** (3.266 do legado + 17 sem atribuição); nenhum arquivo
publicado sem licença e fonte declaradas.

Com a coleta de §13 no mesmo marco, **4.353 municípios (78,1%)** já têm candidato
com evidência — medido, não estimado. O spike (§13.7) fechou a metade gratuita;
falta o piloto de `.gov.br` em escala para as 1.218 lacunas.

O que a Fase 0 **não** entrega: vetor. Cobertura sim, vetor não — ele depende de
PDF oficial e curadoria (§13.5).

---

## 13. Coleta e captação de fontes

O plano anterior assumia que a cobertura vinha de PRs. Os números abaixo mostram
que ela vem de **enumeração**: o Commons já tem um acervo categorizado que o
scrape por artigo nunca viu.

### 13.1 O que a categorização do Commons já entrega (medido em 2026-11-07)

`Category:Coats of arms of municipalities of {Estado}` existe para 24 UFs e
`Category:SVG coats of arms of municipalities of {Estado}` para 6. Contagem via
`prop=categoryinfo`:

| UF | municípios | arquivos na categoria | SVGs (subcategoria) | teto de cobertura |
|---|---:|---:|---:|---:|
| AC | 22 | 0 | 0 | 0 |
| AL | 102 | 96 | 0 | 96 |
| AP | 16 | 18 | 0 | 16 |
| AM | 62 | — | — | 0 |
| BA | 417 | 408 | 36 | 417 |
| CE | 184 | 168 | 24 | 184 |
| DF | 1 | — | — | 0 |
| ES | 78 | 98 | 0 | 78 |
| GO | 246 | 155 | 0 | 155 |
| MA | 217 | 110 | 0 | 110 |
| MG | 853 | 868 | 0 | 853 |
| MS | 79 | 58 | 0 | 58 |
| MT | 142 | 93 | 0 | 93 |
| PA | 144 | 103 | 0 | 103 |
| PB | 223 | 265 | 13 | 223 |
| PE | 185 | 140 | 42 | 182 |
| PI | 224 | 116 | 0 | 116 |
| PR | 399 | 373 | 0 | 373 |
| RJ | 92 | 122 | 24 | 92 |
| RN | 167 | 152 | 0 | 152 |
| RO | 52 | 56 | 0 | 52 |
| RR | 15 | 23 | 0 | 15 |
| RS | 497 | 613 | 46 | 497 |
| SC | 295 | 416 | 0 | 295 |
| SE | 75 | 79 | 0 | 75 |
| SP | 645 | 897 | 0 | 645 |
| TO | 139 | 44 | 0 | 44 |
| **Total** | **5.571** | **5.471** | **185** | **4.924 (88,4%)** |

`teto` = `min(arquivos + svgs, municípios)`: supõe que cada arquivo é um município
distinto, o que **não** é verdade (SP tem 897 arquivos para 645 municípios —
variantes do mesmo brasão). É teto, não promessa.

Três leituras que mudam o plano:

1. **O teto não é 12,4%.** Aquilo era o limite do método anterior (raspar artigo
   da Wikipédia com casamento por nome). Medido no spike, a união dos coletores
   cobre **4.353 municípios (78,1%)** — seis vezes o acervo atual.
2. **A cobertura é desigual, e o esforço deve ser desigual.** TO (44/139) e MA
   (110/217) estão longe; SP, MG, RS, SC já estão em ou acima de 100%.
3. **SVG é mais do que parecia, e menos do que precisamos.** A contagem por
   subcategoria (185) **subestimou três vezes**: os SVGs também vivem na
   categoria-mãe. O total real é **938 arquivos SVG**, cobrindo **577
   municípios (10,4%)**. Ainda longe dos 40% meta — vetor continua vindo de PDF
   oficial (§13.5) —, mas a estimativa anterior de 3,3% estava errada.

### 13.1.1 Resultado medido (2026-11-07)

Executado: Wikidata inteiro, Commons inteiro, piloto `.gov.br` com 5 municípios.
Relatório completo em `data/_spike/RELATORIO.md`.

| Medida | Municípios | % |
|---|---:|---:|
| Com brasão | **4.353** | **78,1%** |
| Com bandeira | 4.037 | 72,5% |
| Com brasão em SVG | 577 | 10,4% |
| Sem candidato nenhum | 1.218 | 21,9% |

| Fonte | Municípios com brasão | Ganho |
|---|---:|---|
| Wikidata `P94` | 3.850 | casamento exato por código IBGE |
| Commons (categorias) | 3.610 | casamento por nome de arquivo |
| **União** | **4.353** | Commons acrescenta **503** |

Licenças dos candidatos de brasão: **84,4% `livre`**, 14,7% `compartilha`,
0,9% `pendente`. Qualidade: 1,96 candidato por município; largura mediana dos
JPEG **282 px**, com **46,7% abaixo de 256 px**.

Bandeiras vêm 99,9% do Wikidata (`P41`): categoria de bandeira municipal no
Commons praticamente não existe. **Bandeira é problema de Wikidata, não de
Commons** — não gastar esforço no lugar errado.

### 13.2 Quatro coletores, em ordem de retorno

| Ordem | Fonte | O que entrega | Custo | Licença |
|---|---|---|---|---|
| 0 | **DNS determinístico** | domínio oficial de `{compacto}.{uf}.gov.br`; mediu **97%** dos 1.218 sem cobertura | 1 consulta DNS (sem HTTP) | — |
| 1 | **Commons por categoria** | 5.656 candidatos + `extmetadata` completo | ~130 requisições | explícita por arquivo |
| 2 | **Wikidata P94/P41/P1585** | mapa canônico município→arquivo; cobre estados; preenche buracos | ~112 requisições | herda do Commons |
| 3 | **Commons search** (`srnamespace=6`) | resto, por nome do município | médio | explícita |
| 4 | **`.gov.br` oficial** | lacunas + verificação oficial + PDF vetorial | 1 página por host (não 12) | `LicenseRef-simbolo-oficial-municipal` (§13.4) |

O coletor 0 existe porque o padrão de domínio municipal brasileiro é
surpreendentemente regular: `camaragibe.pe.gov.br`, `agudos.sp.gov.br`,
`belmonte.ba.gov.br`, `saopaulodasmissoes.rs.gov.br`. Testar candidatos por
**DNS** (sem tocar no servidor) resolveu 58 de 60 municípios sem cobertura. Isso
corta a descoberta de domínio do orçamento pago e responde à preocupação de
bloqueio de IP: consulta DNS não é acesso.

Propriedades confirmadas na API: `P1585` = código de município do IBGE,
`P94` = imagem do brasão, `P41` = imagem da bandeira. Exemplo real: Q174 (São
Paulo) → `Brasão da cidade de São Paulo.svg`.

`extmetadata` do Commons entrega `LicenseShortName`, `UsageTerms`,
`AttributionRequired`, `Copyrighted`, `Artist`, `Credit`, `Restrictions` e
`Categories` — ou seja, **a licença e o autor vêm prontos**, sem inferência.

Ordem de execução: 1 → 2 → 3, e só o que sobrar vai para 4. Isso corta a
varredura de `.gov.br` de 5.571 para talvez 800 hosts — seis vezes menos.

### 13.3 Prova, não promessa: o bloco `coleta`

Todo item guarda *como* foi achado, não só de onde veio:

```json
"coleta": {
  "metodo": "commons-categoria",
  "consultado_em": "2026-11-08T14:03:11Z",
  "consulta": {
    "endpoint": "https://commons.wikimedia.org/w/api.php",
    "parametros": { "action": "query", "prop": "imageinfo",
                    "titles": "File:Brasão de Eunápolis.svg",
                    "iiprop": "extmetadata|url|size" },
    "http_status": 200
  },
  "evidencia": {
    "campo": "Category:Coats of arms of municipalities of Bahia",
    "arquivo": "File:Brasão de Eunápolis.svg"
  },
  "extmetadata": {
    "LicenseShortName": "Public domain",
    "UsageTerms": "Public domain",
    "AttributionRequired": "false",
    "Artist": "Rodrigo Melo",
    "Credit": "Vetorizado por Eduardo José de Castro Coitinho Filho e revisado por mim",
    "Restrictions": ""
  },
  "resposta_sha256": "5c1e…"
}
```

Regras:

- A resposta bruta vai para `evidencias/<sha256>.json` no R2 (não no git); o
  hash fica no `meta.json`. Dá para reauditar a licença em 2032 mesmo se a
  página mudou.
- **Publicação automática** só quando `UsageTerms`/`LicenseShortName` existem,
  `Copyrighted` é `False` ou há licença CC reconhecida, e `Artist`/`Credit`
  resolvem. Qualquer campo faltando → fila de revisão humana.
- `AttributionRequired=true` gera obrigatoriamente `licenca.atribuicao`
  preenchida — o build falha se estiver vazia.

### 13.4 Símbolo oficial publicado pela prefeitura (decidido)

Um brasão no site da própria prefeitura tem **procedência** (URL, data, autor
institucional, hash) mas quase nunca tem **licença explícita**. Sem uma regra
para isso, a varredura `.gov.br` renderia zero publicável e o projeto ficaria
preso ao Commons: sem T4, sem verificação oficial e sem vetor.

**Decisão travada:** aceitar `LicenseRef-simbolo-oficial-municipal`, e só quando
as quatro condições valerem simultaneamente:

1. o domínio é da própria prefeitura (`.gov.br` ou subdomínio estadual oficial);
2. o arquivo representa o símbolo **daquele** município;
3. a página o identifica como símbolo oficial (brasão/bandeira do município);
4. a captura registra URL, data e `sha256`.

Base jurídica: o símbolo é instituído por ato oficial e a prefeitura é o próprio
titular — Lei 9.610/98, art. 8º, IV (§10.1). **Não é "domínio público"**: é uso
com origem institucional identificada. Fica no balde `oficial`, nunca em
`brasil-livre.zip` e nunca com o rótulo "livre".

Consequências que a decisão destrava:

| Antes | Depois |
|---|---|
| `.gov.br` rende 0 publicável | `.gov.br` vira a camada de lacuna e de verificação |
| T4 impossível (sem fonte oficial) | T4 passa a existir, com `revisao.nivel = verificado_oficial` |
| Vetor preso a ~3% do Commons | PDF oficial vira o caminho realista para 40% vetorial |
| Cobertura teto ~80% | Teto sobe para o que a varredura alcançar |

Contrapartidas que a decisão obriga:

- `/licencas` e a página do item explicam o balde `oficial` em linguagem clara —
  sem sugerir que o símbolo é livre.
- Termos de uso dizem que **o projeto não concede** autorização de uso; em alguns
  municípios o uso do símbolo é regulado por lei local.
- Opt-out publicado em `/coleta`: prefeitura pede e o item sai em 72 h.
- Nenhum arquivo `oficial` entra em pacote rotulado como livre, nem é oferecido
  como "sem restrições" na API.

### 13.5 O caminho para SVG: PDF oficial — mas da lei, não do manual de marca

SVG solto em site municipal é raro (< 5% estimado). O vetor existe dentro de PDF,
mas **a medição corrigiu o alvo**: manual de identidade visual é, na prática, o
manual da *marca da gestão*, que muda a cada administração.

Teste em `rioclaro.sp.gov.br/.../MANUAL_DE_IDENTIDADE_VISUAL.pdf` (53 páginas,
13,8 MB): `pdfimages -list` mostrou **19 de 53 páginas sem imagem raster**
(vetor puro) — bom sinal. Mas o S5, lendo as 74 mil letras do manual, respondeu
`pagina: null` com justificativa: nenhuma página apresenta a arte do brasão
sozinha. Conferido a olho na página 6 (a mais promissora da lista vetorial): é
uma **paleta de cores**, não o brasão. O manual é sobre "a marca da gestão Amor
Pela Cidade".

Conclusão: o modelo **recusou corretamente** quando o alvo não existia — que é o
comportamento que a regra de citação compra. E a classe documental certa é outra:

| Documento | Serve? |
|---|---|
| **Lei/decreto que institui o símbolo** (com anexo) | **sim** — o brasão costuma vir em anexo |
| Página "símbolos municipais" do site | sim |
| Almanaque, publicação histórica oficial | às vezes |
| Manual de identidade visual / manual da marca | **não** — traz a marca da gestão |

Pipeline, quando o PDF é da classe certa:

- Detectar vetor: `pdfimages -list` (página sem raster = provável vetor).
- Localizar: S5 lê o texto inteiro (1M de contexto) e devolve **página + citação
  literal**, restrito às páginas vetoriais.
- Extrair: `pdftocairo -svg -f N -l N` (mediu 4,5 MB de SVG, 167 `path`s, 0
  `<text>` na página testada).
- Classificar: `natureza: "exportado"`, `ferramenta: "pdftocairo 26.10.0"`,
  tier T3 (T4 se oficial e verificada).
- **Validar sempre**: PDF→SVG quebra `clipPath`, `mask` e `use`; render check
  obrigatório (§7.1) e SVGO depois.

Isso muda a busca: em vez de caçar "manual de identidade visual", procurar **a
lei que instituiu o brasão** — que também é a prova que falta para T4.

#### 13.5.1 Traçar raster é último recurso — e o SAM não vetoriza

SAM (Segment Anything) **segmenta**: devolve máscara de pixels, não caminho
vetorial. Vetorizar é outra etapa (`vtracer`, `potrace`). Confundir as duas faz
parecer que existe um atalho que não existe.

Medido: `vtracer` no `brasao.jpg` de Belmonte (o "melhor caso" de página oficial)
produziu **890 paths e 352 KB** para um brasão que, desenhado à mão, tem ~167
paths no nosso acervo. Pior: a marca d'água da fonte foi traçada **dentro** da
arte, e o texto saiu tremido. O resultado é reconhecível e inútil para impressão.

Conclusão: traço automático é **rendition de último recurso**, nunca "o vetor
oficial". Regras:

- só traçar a partir de raster ≥ 512 px (de 192 px o resultado é blocos);
- `natureza: "vetorizado"`, `ferramenta: "vtracer 0.6.15"`, com o `sha256` do
  raster como `derivada_de`;
- tier não sobe para T4; fica T3 com nota "vetorizado a partir de raster";
- nunca entra em pacote rotulado como vetor oficial.

Onde SAM (ou, mais leve, `rembg`) realmente serve é **antes** disso: isolar o
brasão de fundo sujo — foto, mockup, página escaneada. A visão já classifica
`fundo` (`limpo`/`foto`/`documento`), então o gatilho é objetivo: só vale
segmentar quando `fundo != limpo`. Para fundo limpo, segmentar é desperdício.

Ferramentas: `vtracer`, `potrace` e `rembg` estão no nixpkgs; SAM exige pesos e
PyTorch (via `uv`), então roda como job em lote — nunca no caminho da API.

#### 13.5.2 Vetorização com aprendizado: onde ajuda e onde engana

Primeiro a terminologia, porque ela muda a conversa: **rasterizar** é vetor→pixel
(é o que o `resvg` já faz, resolvido). O problema aqui é o inverso,
**vetorizar** — pixel→vetor.

Existem modelos de imagem→SVG: Im2Vec (2021), LIVE (2023), StarVector (SVG-LLM),
OmniSVG (2025, com controle em nível de parte). Fine-tuning por domínio é
tecnicamente possível. A tentação é treinar com coroas, escudos e animais
heráldicos — e é exatamente aí que o tiro sai pela culatra.

**Priori heráldico produz arte plausível, não arte fiel.** Um modelo que "sabe"
como é uma coroa mural vai *melhorar* a coroa de um scan ruim — inventando torres
que não existiam, endireitando um listel torto, trocando um detalhe. Para um
acervo que promete procedência, esse é o pior resultado possível: a citação é
verdadeira e a arte é inventada. É o mesmo risco da §10.4, com roupa nova.

Regra que decorre disso: saída de modelo generativo **nunca** é o ativo oficial.
No máximo vira `natureza: "reconstruido"`, com o raster como referência e aviso
visível — e mesmo assim só com revisão humana comparando lado a lado.

O que provavelmente rende mais, e não precisa de GPU:

| Caminho | Fidelidade | Custo | Observação |
|---|---|---|---|
| Buscar vetor oficial (lei/PDF) | total | humano, mas já em curso | §13.5 |
| **Biblioteca de partes + traço assistido** | total | baixo | escudo português/redondo, coroa mural de N torres, listel, paleta fixa |
| Segmentação + `vtracer` | baixa | baixo | só para `fundo != limpo` |
| Modelo imagem→SVG com priori heráldico | **incerta** | alto | precisa de benchmark antes de qualquer aposta |

A biblioteca de partes é o ponto subestimado: brasão municipal brasileiro segue
uma gramática pequena — escudo português, coroa mural de 3 a 5 torres, listel com
nome e datas, paleta limitada. Snap para template + ajuste humano vetoriza em
minutos o que o traço automático faz mal em segundos.

**Se quiser apostar no modelo, o benchmark é barato e decide sozinho.** Pegar 20
municípios que tenham raster **e** SVG oficial, gerar o vetor por três métodos
(traço clássico, modelo genérico, modelo com fine-tuning), rasterizar de volta e
comparar com o SVG oficial por IoU/SSIM e por diferença perceptual. Sem esse
número, "deep learning vetoriza melhor" é hipótese, não plano. E o critério de
aceitação não é "parece bonito": é passar no limiar **e** não inventar elemento
ausente na fonte.

Status: em avaliação. Não bloqueia nada — a cobertura vetorial continua vindo de
fonte oficial, e a meta de 40% não depende disso.

### 13.6 Arquitetura do coletor

- **Fila em SQLite** (`data/_fila/coleta.sqlite`), uma linha por alvo:
  `alvo → consultado → candidato → triado → revisado → publicado | rejeitado`.
  Reesumível: `kill -9` não perde nada, e cada fase é idempotente.
- **Polidez**: 1 req/s por host, no máximo 2 conexões por host, 5 workers
  globais; `robots.txt` respeitado com cache de 24 h; backoff exponencial;
  `maxlag=5` na API da Wikimedia.
- **User-Agent** com URL do projeto e contato — exigência da política da
  Wikimedia e boa prática em `.gov.br`.
- **Cache** content-addressed: nunca re-buscar em menos de 90 dias, salvo
  `--forcar`.
- **Orçamento**: Commons ~130 requisições; Wikidata ~112; descoberta de domínio
  1.218 consultas DNS (sem HTTP, sem crédito); `.gov.br` **1 página por host**
  (~1.180 fetches), não 12. Com 5 workers e 1 req/s por host: ~30 min.
- Muitos `.gov.br` bloqueiam IP estrangeiro; rodar de IP brasileiro.

### 13.7 Spike antes de escalar

Não vale gastar 30 horas de crawl em cima de estimativa. Amostra estratificada
de **60 municípios** (2 por UF: uma capital e uma cidade pequena), 1 dia de
trabalho, medindo:

| Medida | Para decidir |
|---|---|
| % com arquivo na categoria do Commons | teto real de cobertura |
| % desses que são SVG | se o vetor do Commons acabou mesmo |
| % com `P94` no Wikidata | se vale o coletor 2 |
| % com site `.gov.br` ativo | tamanho real da varredura 4 |
| % com brasão na home/`/o-municipio`/`/simbolos` | rendimento do crawl |
| % com PDF contendo vetor | rendimento do caminho SVG |
| distribuição de licenças | % que passa no filtro `?licenca=livre` |

Os números deste documento são hipóteses medidas em parte; o spike fecha o
resto. Só depois dele se define o alcance do crawl completo.

**Estado em 2026-11-07:** a metade gratuita foi executada inteira (Wikidata +
Commons), o piloto `.gov.br` rodou em 5 municípios e a descoberta de domínio por
DNS foi medida (58 de 60). Resultado em `data/_spike/RELATORIO.md`. O que falta
medir: rendimento da página de símbolos em escala (1.218), custo real por chamada
no Firecrawl (o contador não se moveu), quantos PDFs oficiais rendem vetor, e
quanto a heurística de extração resolve sem LLM.

### 13.8 Ética e opt-out

- Nada de página autenticada, `robots.txt` proibido ou CAPTCHA contornado.
- Não rastrear domínio que não seja da própria prefeitura (nem portal de notícia,
  nem empresa que fez o site).
- Página pública `/coleta` explica o que é rastreado, com que frequência, e
  oferece **opt-out** para qualquer prefeitura — atendido em 72 h, com o item
  retirado do acervo.
- Crawl de `.gov.br` não é "scraping de dado pessoal": só imagem institucional,
  sem formulário, sem login, sem path de servidor.

### 13.9 CLI

```
simbolos coletar commons   [--uf BA | --tudo]
simbolos coletar wikidata  [--uf BA]
simbolos coletar commons-search --faltantes
simbolos coletar govbr     --somente-faltantes [--limite N]
simbolos coletar pdf       --url … | --fila
simbolos triar             # tipo, tier, licença, dedup, colisão de nome
simbolos revisar           # relatório humano (CSV + página local)
simbolos evidencias exportar
```

### 13.10 Efeito no plano

| Antes | Depois |
|---|---|
| Importar 1.059 arquivos baixados | Coleta medida: **4.353 municípios (78,1%)** |
| Lançamento com 12,4% | Lançamento com **78,1%** (medido, não estimado) |
| "Caça a fontes" em M3 | Coleta em **M0**; M3 vira vetorização e verificação oficial |
| Vetor 25,4% | **10,4%** de cobertura vetorial (577 municípios); PDF oficial é a alavanca |
| `.gov.br` como fonte primária | `.gov.br` para **1.218 lacunas** e T4: piloto deu 5/5 domínio, 2/5 ativo, **0/5 vetor** |

O piloto `.gov.br` fechou a questão: site oficial entrega **procedência e
oficialidade**, quase nunca vetor. O melhor caso (Belmonte/BA, página
`/simbolos`) entregou um `brasao.jpg`. Então `.gov.br` não é caminho de
cobertura — é caminho de T4 e de lacuna.

A decisão de não usar o acervo legado custa **tempo de curadoria**, não
cobertura: em três minutos de API o acervo passou de 689 para 4.353 municípios.

### 13.11 Sabiá/S5: papel, regra e resultado medido

Saldo: **R$ 675,09**; depois de 3 requisições, **R$ 675,08** (R$ 0,01 no total,
com 17,5k tokens em cache). Custo desprezível na prática.

Modelos disponíveis: `sabia-4` (128k), **`S5` (1M de contexto)**, `S5-br-sp`
(1M), `S5-nano` (256k), `sabia-4-thinking`, `sabiazinho-4`. `S5` não aceita
`temperature=0` — não há saída determinística, e é por isso que a verificação
abaixo não é opcional.

Chave: ambiente **`simbolos-br`** no 1Password, variável `MARITACA_API_KEY`,
materializada por `create_local_env_file` num arquivo `0600` **fora do repo**
(`/tmp/opencode/simbolos-br.env`). Nunca entra no git.

**Resultado do teste (2 páginas, 2 acertos):**

| Página | Extração | Verificação |
|---|---|---|
| Belmonte `/simbolos` | `/userfiles/image/brasao.jpg` + citação literal | **200 image/jpeg** |
| Agudos `/cidade/simbolo` | thumb de 47 KB (original 143 KB) + citação da **Lei nº 264** | **200 image/jpeg** |

O ativo de Agudos foi conferido a olho: é o brasão, com o listel
"1897 AGUDOS 1898".

**Uma correção que o teste impôs:** minha heurística de regex afirmou que a
página de Agudos não tinha brasão. Estava errada — o HTML traz `Bras&atilde;o`, e
o regex por `bras` não atravessa entidade HTML. **Heurística precisa de parser de
HTML, não de regex em texto cru.** O LLM achou o que o regex perdeu.

**A regra que torna o uso seguro:** `trecho_que_prova` é obrigatório e precisa
ser **substring literal** do HTML guardado (normalizando entidades e tags). Sem
citação verificada, `aceito = false` — mesmo que o modelo declare confiança 0,99.
É o que transforma o LLM em **extrator de citação**, e não em fonte de fato. Está
implementado em `simbolos/maritaca.py` (`_presente` + `aceito`).

Limite observado: `ato_oficial` voltou `null` em Agudos mesmo com a lei na
página — o modelo colocou a lei dentro do trecho. O ato oficial precisa de um
passe próprio; a citação continua sendo a prova.

**Custo real:** 1.218 páginas ≈ **alguns reais**, não os R$ 50–75 estimados.

O que **não** fazer continua igual: usar como fonte de fatos sobre heráldica, ou
pedir para "completar" um `meta.json`. As duas coisas produzem dado plausível e
falso, que é o único tipo de erro que este projeto não consegue detectar depois.

Arquitetura: **heurística primeiro, LLM no fallback** — com parser de HTML de
verdade (selectolax/BeautifulSoup), não regex. O modelo entra quando a página é
um CMS quebrado, e aí a citação verificada é o que autoriza o dado.

**CLI (Typer).** Como a chamada é frequente, ela tem comando próprio:

```
simbolos maritaca modelos                          # lista modelos + contexto
simbolos maritaca saldo                            # saldo e uso do periodo
simbolos maritaca extrair --url … | --arquivo …    # extracao com citacao
simbolos maritaca perguntar --sistema p.txt --arquivo c.txt --json
simbolos maritaca lote --entrada urls.txt --saida out.jsonl [--limite N]
```

`lote` retoma de onde parou (relê o JSONL), faz 1 req/s e acumula o custo na
tela. `perguntar` é a chamada crua — serve para experimentos como o do PDF, sem
escrever código novo a cada pergunta.

**Chamada robusta.** O `S5` às vezes gasta todo o orçamento de saída em
raciocínio e devolve `content: null` com `finish_reason: "length"`. O cliente
dobra o orçamento e repete; se ainda vier vazio ou JSON inválido, troca para
`sabia-4`. Sem isso, uma extração em lote perderia páginas silenciosamente.

**Custos medidos:**

| Chamada | Tokens | Custo |
|---|---|---|
| Belmonte (17,8 KB de HTML) | 4.448 in / 1.384 out | R$ 0,0057 |
| Agudos (101,8 KB) | 19.180 in / 751 out | R$ 0,0115 |
| Manual PDF (74 mil letras) | 10.599 in / 3.912 out | R$ 0,0151 |

**A/B de provedores (3 páginas: 2 com brasão, 1 sem).** Nesta amostra, o que
separa não é acerto — é custo e citação:

| Modelo | Acertos | Tokens de saída | Custo medido |
|---|---|---|---|
| `deepseek/deepseek-chat` | 3/3 | 304 | não reportado pela API |
| `neuralwatt/deepseek-v4.1-flash` | 3/3 | 3.518 | **US$ 0,0012** |
| `neuralwatt/glm-5.3` | **2/3** | 3.424 | US$ 0,0062 |
| `maritaca/S5` | 3/3 | 1.206 | R$ 0,0238 (~US$ 0,0044) |

O 2/3 do GLM 5.3 foi falha de **citação**, não de URL: ele devolveu um ativo que
responde 200, mas o trecho citado não foi encontrado no HTML — e o portão
recusou. É o portão funcionando, não o modelo errando à toa.

**Custo vem da resposta, não de tabela.** O Neuralwatt devolve, por requisição:

```json
"cost": { "request_cost_usd": 0.000146,
          "cache_savings_usd": 0.0,
          "allowance_remaining_usd": 3.803131 }
```

Isso está ligado em `Resposta.custo_reportado` e tem precedência sobre a
estimativa por tabela. Maritaca reporta em BRL (`billing/usage`), Neuralwatt em
USD por request; **DeepSeek não reporta custo nenhum** — só `usage`, então o
preço dele continua "a confirmar" e não entra em soma de orçamento.

**Raciocínio é a maior parte da saída.** Na chamada do GLM 5.3 Flash, 262 dos
363 tokens de saída eram `reasoning_tokens`. Ou seja: o teto alto não é só para
"caber a resposta" — é para caber o raciocínio que o modelo faz antes dela. E o
preço cobra isso.

Conclusão prática: **orçamento de saída alto por padrão, mas modelo de raciocínio
só onde ele é necessário.** A cobrança é por token gerado, não por token
reservado — então um teto de 8.000 é seguro e não custa nada se o modelo parar
antes. O que custa é o modelo gastar milhares de tokens de raciocínio para achar
um `<img src>`. Regra:

- **página única** → `neuralwatt/deepseek-v4.1-flash` (padrão de extração; 3/3 a
  US$ 0,0012 nos 3 casos, e também enxerga imagem);
- **documento longo / várias páginas / ambiguidade real** → S5 ou GLM 5.3, com
  teto de 8.000–16.000;
- sempre gravar `finish_reason`, `reasoning_tokens` e custo por item, e tratar
  `length` como truncamento — não como resposta.

**DeepSeek direto está descontinuado.** A rota é `neuralwatt/deepseek-v4.1-flash`;
os créditos antigos do provedor direto não são mais usados. Se o saldo do
Neuralwatt acabar, é lá que se recarrega — não se volta para a API direta.

**Descontos de fila (o que mais importa num crawl).**

| Opção | Desconto | Como | Latência |
|---|---|---|---|
| Neuralwatt `-flex` | ~30% | sufixo no modelo | imediata |
| Maritaca `service_tier: flex` | **50%** | campo no corpo | imediata, 429 se a fila encher |
| Maritaca batch | **50%** | `/api/batches` + `/api/files` | até 24h |
| Prompt cache (ambos) | 75% na entrada (90% em S5) | automático, prefixo idêntico | — |

Descontos **não se multiplicam**: cache incide sobre os tokens em cache, o tier
sobre o resto. E `flex`, batch e off-peak são mutuamente exclusivos.

O `flex` está ligado por `--flex`: no Neuralwatt vira sufixo de modelo, na
Maritaca vira `service_tier`. O cliente trata 429 com backoff exponencial (a doc
manda fazer isso) e, se o modelo não tiver variante, volta sozinho para o normal.

**Medição em 10 páginas reais** (`data/_spike/custo-10-paginas.json`):

| Rota | Aceitos | Custo | Tempo |
|---|---|---|---|
| `maritaca/S5` + flex | 6/10 | **R$ 0,04185** | 52 s |
| `neuralwatt/deepseek-v4.1-flash` + flex | 7/10 | **US$ 0,000924** | 40 s |

O custo da Maritaca é o faturado (delta de `billing/usage`), não estimativa. A
diferença é de **~8×** por página, e o modelo barato ainda aceitou mais.

Extrapolando: 1.000 páginas ≈ **US$ 0,09** no Neuralwatt flex, contra ~R$ 4,20 na
Maritaca. O crawl inteiro das 1.218 lacunas custa centavos — o custo deixou de
ser restrição do projeto.

**Batch na prática.** O lote de teste com 1 requisição ficou `in_progress` por
mais de 20 minutos. Ou seja: o batch tem a mesma metade de preço do flex, mas
latência real de horas. Como o flex é síncrono e imediato, **batch não se
justifica** para este workload — só faria sentido se o volume fosse grande o
bastante para importar com horas de espera e o flex estivesse recusando.

**Prompt cache.** É automático, sem parâmetro. Hoje o prefixo cacheável é só o
prompt de sistema (~200 tokens), porque o documento vem depois e muda a cada
página. O ganho real apareceria no fluxo que faz **duas perguntas na mesma
página** (`achar_ato` e `extrair`): se as duas usassem o mesmo prompt de sistema
e o documento viesse antes da pergunta, a segunda chamada pegaria o documento em
cache. Hoje elas usam system prompts diferentes, então não há prefixo comum —
reestruturar isso é otimização pendente, não urgente (o custo já é centavos).

### 13.12 Verificação visual: a camada que faltava

Havia 8.534 candidatos de brasão e **nenhum jeito automático** de saber se a
imagem é o símbolo certo. dHash acha duplicata; não acha erro. O `S5` é texto —
não vê imagem.

Dois modelos do Neuralwatt têm visão, e os dois acertaram 4/4. O mais barato é
`deepseek-v4.1-flash` — que já é o padrão de extração, então **um modelo só faz
as duas coisas**:

| Modelo | Acertos | Custo por imagem | Visão |
|---|---|---|---|
| `neuralwatt/deepseek-v4.1-flash` | **4/4** | **US$ 0,000014** | sim |
| `neuralwatt/glm-5.3-flash` | 4/4 | US$ 0,000036 | sim |

Isso corrige uma suposição minha: eu tinha tratado visão como exclusiva do GLM
5.3 Flash. Não é — o V4.1 Flash vê igual e custa 2,5× menos.

| Imagem | Esperado | Obtido |
|---|---|---|
| Agudos/SP brasão | brasao | **brasao** |
| Belmonte/BA bandeira | bandeira | **bandeira** |
| Belmonte/BA brasão | brasao | **brasao** |
| Camaragibe/PE logo | logo | **logo** |

As descrições vieram específicas — na bandeira de Belmonte: "campo branco com
quadrantes verdes em X (cruz de Santo André), brasão ao centro com coroa mural,
montanha, sol, cacau e listel 'BELMONTE 1891-1961'". Não é sorte: é leitura.

Isso entra no pipeline como portão de tipo, em §7.1:

- todo candidato passa por `simbolos.visao.verificar`;
- `tipo` tem que bater com o slot (`brasao` em `/brasao`, `bandeira` em
  `/bandeira`) e `confianca ≥ 0,6`;
- divergência vai para a fila de revisão, com a descrição do modelo anexada;
- pega o erro que o nome não pega: bandeira gravada como brasão, símbolo
  estadual no lugar do municipal, logo da gestão no lugar do brasão.

A visão também classifica **`marca_dagua`** e **`fundo`** (`limpo`/`foto`/
`documento`), e isso virou portão de qualidade:

- `marca_dagua = true` → item não é publicado: vai para a fila com motivo
  `marca_dagua`. O `brasao.jpg` de Belmonte reprovou assim — o arquivo "oficial"
  tem a marca d'água da fonte traçada por cima;
- `fundo != limpo` → candidato a segmentação (`rembg`/SAM) antes de virar
  rendition, não a publicação direta.

Medido: Belmonte `marca_dagua=true, fundo=limpo` (reprovado por marca d'água);
Agudos `marca_dagua=false, fundo=limpo` (aprovado).

#### 13.12.1 Modelo de decisão (System One): o encaixe certo para o portão

Pesquisado e testado. "System One" é uma classe de modelo **discriminativo**
(TypeSafe Jev, Cloudflare Clef): recebe `state` + perguntas tipadas e devolve
**probabilidade para cada resposta permitida** — sem gerar texto, sem amostragem,
cobrado só por token de entrada. No Neuralwatt: `POST /v1/systemone`, modelo
`clef-flash` (aceita até 8 imagens por requisição).

Medido nas mesmas 19 imagens:

| Rota | Aceitos | Concordância de tipo | Custo/imagem | Tokens de saída |
|---|---|---|---|---|
| `clef-flash` (systemone) | 15/19 | — | **US$ 0,00008** | **0** |
| `deepseek-v4.1-flash` (chat) | 16/19 | 17/19 | US$ 0,000019 | 200–800 |

Três coisas que o teste mostrou:

1. **Não é mais barato.** É ~4× mais caro por imagem, porque imagem conta como
   token de entrada e a entrada do `clef-flash` custa mais que a do
   `deepseek-v4.1-flash`. Em valores absolutos, continua centavos.
2. **É mais confiável.** Probabilidade calibrada em vez de JSON gerado; sem
   `finish_reason: length` por raciocínio, que foi a causa de 5 falsos negativos
   no portão por chat (o modelo gastou 800 tokens pensando e devolveu vazio).
3. **Discorda em 2 de 19** — inclusive num caso em que o chat viu marca d'água e
   o `clef-flash` não. Divergência só se resolve com conjunto rotulado à mão.

**Divisão de trabalho que decorre disso:**

- **`clef-flash` decide** — é brasão? bandeira? logo? tem marca d'água? fundo
  limpo? Uma passada, probabilidades, determinístico. É o portão.
- **chat descreve** — lê o listel, diz o município, escreve a descrição que vai
  para a página do item. O `clef-flash` não gera texto, então não serve aqui.

Ressalvas: `clef-flash` está em preview e o cadastro novo está fechado; o
endpoint `/v1/systemone` não aparece no índice público de docs (a referência
existe em `portal.neuralwatt.com/docs/api/systemone`, que foi onde achamos o
formato). Se sair do ar, o portão volta para o chat com o orçamento corrigido.

**Conjunto rotulado pelo usuário (5 divergências).** Rótulos em
`data/_spike/rotulos.json`.

| Caso | Verdade | clef | chat |
|---|---|---|---|
| Colina/SP | brasão com texto ao lado (recortável) | **✓** | ✗ (logo) |
| Brejolândia/BA | **imagem em branco** | ✗ (logo) | ✗ (outro) |
| Camutanga/PE | sem marca d'água | **✓** | ✗ (inventou marca) |
| Cedro/PE | fundo preto (não limpo) | ✗ | **✓** |
| Aratuba/CE | fundo limpo | **✓** | ✗ |

**clef-flash 3/5, chat 1/5.** O chat inventou marca d'água num brasão limpo —
falso positivo que descartaria ativo bom. Já o clef errou o fundo preto do Cedro
e não viu que a imagem da Brejolândia era branca.

**Nem modelo nem modelo: o defeito estrutural é determinístico.** A Brejolândia
tem 4000×2022 com desvio-padrão **0,00** — branco puro. Um check de
`ImageStat` pega isso sem LLM, e agora é o primeiro filtro do portão:

- `vazia` (desvio < 2) → rejeita, motivo `imagem_vazia`;
- `pequena` (lado menor < 160) → **não rejeita**, vira `tier: T1` (o acervo já
  aceita T1; tamanho é qualidade, não validade);
- `precisa_recorte` (proporção > 2,2) → sinaliza brasão com texto ao lado, como
  Colina.

Ordem dos motivos de rejeição: `imagem_vazia` > `marca_dagua` > tipo errado.

E uma constatação que muda a urgência: na última verificação, **3 dos 19 links
já estavam mortos** (2 conexão recusada, 1 HTTP 404). Catálogo é lista de URLs de
terceiros; publicar o arquivo é o que impede o acervo de apodrecer.

Custo: ~1.100 tokens de entrada e ~500 de saída por imagem. Nas 8.534 imagens,
alguns milhares de tokens de imagem — a confirmar no primeiro lote, porque
imagem é cobrada diferente de texto.

```
simbolos visao --url https://…/brasao.jpg
```

### 13.14 Resultado do crawl de leis (39 municípios, medido)

Rota: domínio por DNS → home → páginas candidatas → LLM (ato + símbolo) com
citação verificada.

| Medida | Resultado |
|---|---|
| Domínio resolvido | 37/39 (95%) |
| Com página candidata | 35/39 (90%) |
| **Com símbolo aceito** | **17/39 (44%)** |
| Com ato verificado | 1/39 (3%) |
| Com PDF | 0 |
| Custo | US$ 0,0307 → **US$ 0,0008/município** |

**O coletor é melhor achando brasão do que achando lei.** Quase metade dos
municípios sem cobertura tem o brasão publicado no próprio site — Cajati, Colina,
Brejolândia, Cabaceiras do Paraguaçu, Camutanga, Cedro, Belmonte. Já o ato que
instituiu o símbolo aparece em 3%: a lei raramente está na página, e quando está
é um PDF ou um sistema de legislação à parte.

Projeção para as 1.218 lacunas: **~536 brasões adicionais por ~US$ 1**. A
cobertura sairia de 78,1% para ~87%. Isso muda a prioridade: o crawl oficial não
é caminho para T4, é caminho de **cobertura**.

**Velocidade.** O primeiro lote rodou a 71 s por município; depois de sondagem em
paralelo, recorte de texto e concorrência entre municípios, ficou em **10–18 s**
para quem tem página. Três causas do atraso original: sondagem de 8 caminhos em
série com timeout de 25 s, prompt com a página inteira, e nenhuma concorrência.

**Contraindicação medida:** paralelismo 6 ficou *mais lento* que 3 (108 s contra
23 s para 6 municípios). Com 12 chamadas simultâneas o provedor enfileira e a
latência individual explode. O padrão agora é 3; para escalar de verdade, fila
persistente com concorrência adaptativa, não mais threads.

### 13.16 Catálogo triado: de 12 mil candidatos a um item por município

`simbolos triar` escolhe **um** candidato por município/tipo e grava
`data/_catalogo/catalogo.json`.

Regra de escolha: vetor antes de raster, depois licença, depois resolução, depois
canal. `pendente` não entra na disputa enquanto houver alternativa — é filtro,
não peso. Entre `livre` e `compartilha`, o vetor ganha: qualidade é o produto, e o
balde da licença aparece no item e no filtro.

| Medida | Resultado |
|---|---|
| Municípios com algum item | **4.790 de 5.571 (86,0%)** |
| Com brasão | 4.353 (78,1%) |
| Com bandeira | 4.037 (72,5%) |
| Com os dois | 3.600 |
| Brasão vetorial | **577 (13,3% dos brasões)** |
| Precisam de confirmação visual | 915 |
| Com mais de um candidato | 3.151 |

Baldes: `livre` 7.101, `compartilha` 1.220, `pendente` 69. Formatos escolhidos:
SVG 1.178, PNG 3.477, JPEG 3.575, GIF/WebP 159.

**A visão roda por risco, não em tudo**: só 915 dos 8.390 itens precisam de
confirmação (candidato casado por nome ou por página, ou com aviso). Os 7.475
restantes vêm de `P94`/`P41`, que já declaram o tipo. Custo do portão inteiro:
**menos de US$ 0,10**.

O que o catálogo ainda **não** é: arquivo publicado. Falta baixar o escolhido,
gerar as renditions (512 PNG/JPG), gravar o `meta.json` com procedência e servir
em `/embed/v1/...`. Sem isso, o catálogo é uma lista de URLs de terceiros — e
metade delas pode sair do ar.

### 13.17 Publicação local: o contrato de URL funcionando

`simbolos publicar --local` baixa o escolhido, valida, renderiza e grava a árvore
de embed. Teste em 30 municípios de SP:

| Medida | Resultado |
|---|---|
| Itens | 57 (brasão + bandeira) |
| Publicados | **57/57** |
| Tamanho | 8,7 MB |
| Média por item | 156 KB (svg + png 512 + jpg 512) |
| Projeção para 8.390 itens | **~1,25 GB** |
| Tempo | 57 s (limitado por polidez de 1 req/s na Wikimedia) |

Verificado servindo o diretório:

```
/embed/v1/brasao/3501608.png -> 200 image/png      205 KB
/embed/v1/brasao/3501608.jpg -> 200 image/jpeg      63 KB
/embed/v1/brasao/3501608.svg -> 200 image/svg+xml  221 KB
```

Regras de rendition: SVG renderizado a 1024 e reduzido a 512 (anti-aliasing
melhor); PNG com fundo transparente; JPG com fundo branco; `contain` com 2% de
respiro, **nunca esticando**.

Três defeitos que o teste expôs, todos de operação e não de desenho:

1. **429 da Wikimedia** por baixar rápido demais — metade dos itens falhou.
   Corrigido com intervalo por host (1 req/s em `upload.wikimedia.org`), backoff
   exponencial e respeito a `Retry-After`. Passou de 28/57 para 57/57.
2. **`resvg` fora do PATH** fazia todo SVG falhar com erro obscuro. Agora há
   preflight que falha alto: sem `resvg`, nada de SVG é publicado.
3. **SVG é conteúdo executável**: todo SVG passa por validação antes de ir para o
   CDN (sem `<script>`, `on*`, `<foreignObject>` ou referência externa).

**Prompt do `clef` versionado.** `PERGUNTAS` é dado, não código; ganhou
`PERGUNTAS_VERSAO` e o resultado registra `perguntas_versao`. Isso permite
evoluir as perguntas (ex.: "é brasão com texto ao lado, recortável?") e comparar
no conjunto rotulado antes de trocar o padrão.

### 13.15 Data Ocean: fora de escopo

O Data Ocean integra bases **estatísticas e administrativas** (IBGE/Censo, CNPJ
da Receita, DATASUS, INEP, INMET, TSE, ComexStat) com consulta em linguagem
natural e `data_ocean` na API. Nenhuma delas contém brasão, bandeira, imagem ou
ato de instituição de símbolo.

Serve para o *site* ("quantos habitantes tem X", série de chuva, IDEB da escola),
não para o acervo. Fica registrado como decisão: **não usar** enquanto a página
de município não tiver bloco de contexto socioeconômico — e, quando tiver, é
conteúdo, não acervo.

---

## 14. Roadmap

Esforço assumindo 1 pessoa a ~10 h/semana. Fases 2 e 3 podem ser paralelizadas
com alguém de front-end.

| Fase | Entrega | Esforço | Critério de saída |
|---|---|---|---|
| **M0 — Fundação e coleta** | devenv ✅, esqueleto do repo, catálogo IBGE, schema de proveniência + bloco `coleta`, **spike de 60 municípios**, coletores 1–2, `_legado/indice.json`, ADRs 001–013 | 2–3 sem | spike medido e publicado; candidatos com `meta.json` completo; zero arquivo sem licença e fonte; relatório de abertura no ar |
| **M1 — Acervo publicável** | crawl `.gov.br` das lacunas, extração PDF→SVG, pipeline completo, R2 + CDN + headers + purge, `/embed/v1`, API JSON, docs | 3–4 sem | ≥ 70% de cobertura publicada; 3 renditions por item; cache hit > 95%; `?licenca=livre` funcionando |
| **M2 — Site público + contribuição** | landing, busca, páginas, cobertura, downloads, pacotes, **formulário de envio + fila em Issues + runbook** | 4–5 sem | Lighthouse ≥ 95; busca < 50 ms p95; pessoa não técnica envia em < 3 min pelo celular; moderação em < 5 min |
| **M3 — Vetor e verificação** | PDFs oficiais em lote, verificação de prefeituras, vetorização com parceiros | contínuo | **≥ 40% vetorial**; T4 crescente; fila de procedência zerada |
| **M4 — Ecossistema** | v2 com tamanhos e webp/avif, espelhos (IPFS/torrent), integrações DANFSE, verificação por prefeituras | depois | primeira integração de terceiro publicada |

Três mudanças de ordem por causa da coleta:

- **A coleta entra em M0**, não em M3: sem ela o produto lança com 12% e o site
  não tem o que mostrar.
- **M1 ganha o crawl `.gov.br` e o PDF→SVG**, porque é lá que estão as lacunas e
  o vetor.
- **M3 deixa de ser "caça a fontes"** (resolvida por enumeração) e passa a ser
  vetor + verificação oficial, que é o que não se automatiza.

**O que eu cortaria da v1:** contas de usuário, mapa, comentários, i18n, tema
escuro configurável, variantes de tamanho, upload sem moderação, banco de dados.
Tudo isso é reversível de acrescentar; dívida de licença não é.

---

## 15. Custos e sustentabilidade

| Item | Custo mensal |
|---|---|
| Domínio `.com.br` | ~R$ 40/ano |
| Cloudflare (CDN, Pages, Workers no free tier) | US$ 0 |
| R2 — ~10 GB (acervo + renditions + zips) | ~US$ 0,15 |
| R2 — egress | US$ 0,00 |
| GitHub (Actions em repo público) | US$ 0 |
| E-mail / formulário (Cloudflare Email Routing) | US$ 0 |
| **Total** | **< US$ 1/mês** + domínio |

Isso é o argumento mais forte da campanha de doação: **uma doação de R$ 50 paga
o projeto por anos**. A página `/transparencia` publica isso em número, não em
promessa.

O que o dinheiro *não* compra: prioridade, destaque, remoção de concorrente,
selo de "oficial". Está escrito na política.

---

## 16. Métricas

| Dimensão | Métrica | Baseline (hoje) | Meta 12 meses |
|---|---|---|---|
| Acervo | cobertura de brasões (excl. `inexistente`) | **12,4%** (689) | **85%** |
| Acervo | cobertura total (brasão + bandeira) | 18,7% (1.042) | 90% |
| Acervo | vetorial (T3+) entre brasões | **25,4%** (175) | **≥ 40%** |
| Acervo | T4 verificado oficial | 0 | 500 |
| Acervo | balde `oficial` (LicenseRef) | 0 | 800 |
| Acervo | procedência completa | 100% por definição | 100% (não negociável) |
| Acervo | fila de procedência | 3.283 | 0 |
| Coleta | municípios com evidência completa | 689 | 5.500 |
| Uso | requisições de embed/dia | 0 | 10k |
| Uso | downloads/mês | 0 | 500 |
| Uso | instalações npm + PyPI/mês | 0 | 1k |
| Comunidade | contribuidores distintos | 1 | 50 |
| Comunidade | tempo mediano de merge | — | < 7 dias |
| Confiança | latência de correção factual | — | < 72 h |
| Operação | cache hit ratio | — | > 95% |
| Operação | p95 TTFB do embed | — | < 150 ms |

A cobertura deve saltar para **78,1%** já em M0/M1 — medido no spike, porque vem
de enumeração e não de contribuição. Os 12 meses servem para **fechar a cauda**
(1.218 municípios) e para o vetor, que é o único número que exige trabalho humano
por item.

Estado medido da coleta (2026-11-07): 4.353 municípios com brasão, 4.037 com
bandeira, 577 com vetor; 84,4% dos candidatos no balde `livre`.

Se o spike (§13.7) medir menos de 60% no Commons, o gargalo é `.gov.br` — 800
hosts em vez de 5.571 — e o alvo de cobertura muda junto. O de vetor, não: ele
depende de PDF oficial e curadoria em qualquer cenário.

Métrica de vaidade que **não** vamos usar: número de arquivos. Um SVG oficial
vale mais que dez JPEGs upscalados.

---

## 17. Riscos

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Contestação de licença em arquivo publicado | baixa | alto | nada entra sem fonte; denylist do legado; takedown em 72 h; `historico` prova a linhagem |
| Acervo pequeno desencoraja adoção | alta | médio | lançar com 100% de procedência e dizer isso na home; import em lote desde M0 |
| SVG malicioso servido no domínio | média | alto | origem separada, allowlist + SVGO, CSP, `nosniff`, upload moderado |
| Dado errado se espalha (embed em milhares de páginas) | média | alto | dHash, revisão, purge rápido, changelog, "corrigido em" |
| Burnout de moderação | alta | médio | fila em Issues, runbook, dois moderadores, SLA realista |
| Dependência de uma pessoa | alta | alto | docs, ADRs, CI/CD automatizado, segundo mantenedor |
| Percepção de que o projeto "copiou" o anterior sem creditar | média | baixo | 0 arquivos em comum (verificável); nenhuma menção a sucessão; crédito de inspiração opcional em `/sobre` |
| Coleta bloqueada (403, robots, IP estrangeiro) | média | médio | rodar de IP brasileiro, UA identificado, cache de 90 dias, backoff; a lacuna fica no backlog em vez de virar erro |
| Evidência de licença muda ou desaparece na origem | média | médio | snapshot bruto no R2 + hash no git; a licença reauditável mesmo se a página mudar |
| Contestação de que símbolo oficial exige autorização de uso | média | alto | `LicenseRef` marcado (nunca "domínio público"), takedown em 72 h, opt-out em `/coleta` |
| Crawl `.gov.br` vira carga para sites pequenos | baixa | médio | 1 req/s por host, 2 conexões, 5 workers, só página pública, janela noturna |
| PDF→SVG sai quebrado (clip/mask) | alta | baixo | render check obrigatório (§7.1); se falhar, cai para raster e volta para a fila |
| Abuso de hotlink / pico de egress | baixa | baixo | R2 sem egress, alerta, rate limit de borda |
| Mudança de código IBGE (fusão/criação de município) | certa (anual) | baixo | `aliases.json` + 301, refresh anual do catálogo |
| Confusão com "oficial" | média | médio | aviso de não-vinculação, sem branding de governo, selo de verificação separado |

---

## 18. Decisões ainda abertas

As de arquitetura e licença já foram travadas (§1.1). Sobram estas, menores, que
podem ser resolvidas na M0.

1. **Escopo de bandeiras**: só municipais, ou municipais + estaduais + nacional?
   — *recomendo municipais e estaduais na v1; nacional depois, como `76`.*
2. **Domínio e marca**: `simbolos.br` está livre? Alternativas:
   `simbolosbr.org.br`, `brasoes.br`. Nome do pacote (`@simbolos-br/*`)? —
   *verificar disponibilidade antes de qualquer código.*
3. **Contribuição no lançamento**: formulário já na M2 ou só PR? — *com a coleta
   em M0, o formulário pode esperar até M2 sem prejuízo de cobertura; ele serve
   para correção e para a cauda, não para o volume inicial.*
4. **Identidade do contribuidor**: crédito público por padrão (login/nome) ou
   anônimo por padrão com opt-in? — *recomendo anônimo por padrão e crédito por
   opt-in, para não desestimular prefeituras e servidores públicos.*
5. **Quem assina o PIX**: pessoa física, CNPJ ou coletivo? Define a
   transparência possível (§15) e a emissão de recibo. — *decidir antes da
   landing ir ao ar.*

---

## Anexo A — Glossário

| Termo | Significado |
|---|---|
| **Brasão** | escudo/heráldica oficial do município ou estado |
| **Bandeira** | pavilhão oficial; muitos municípios não têm uma documentada |
| **DANFSE** | Documento Auxiliar da NFS-e; exige o brasão do município do prestador |
| **Localidade** | 5.570 municípios + o DF (5.571 entradas no catálogo IBGE) |
| **Rendition** | arquivo derivado da fonte canônica (PNG/JPG/WebP em dado tamanho) |
| **Tier** | faixa de qualidade da fonte (T0 ausente … T4 vetorial oficial) |
| **Alias** | código IBGE extinto/renomeado que redireciona para o canônico |

## Anexo B — ADRs a escrever na M0

1. `001-licenca-em-tres-camadas.md`
2. `002-fonte-canonica-e-renditions.md`
3. `003-estrategia-de-cache-do-embed.md`
4. `004-r2-e-cloudflare-como-infra.md`
5. `005-repositorio-unico-vs-dados-separados.md`
6. `006-tiers-e-metrica-de-cobertura.md`
7. `007-proveniencia-e-linhagem-por-arquivo.md`
8. `008-politica-de-identidade-e-credito.md`
9. `009-nao-reutilizar-o-acervo-legado.md`
10. `010-independencia-do-projeto-anterior.md`
11. `011-coleta-por-enumeracao-e-evidencia.md`
12. `012-licenca-de-simbolo-oficial-publicado.md`
13. `013-pdf-oficial-como-fonte-vetorial.md`
14. `014-llm-nunca-escreve-proveniencia.md`
15. `015-portao-de-tipo-por-visao.md`
16. `016-vetorizacao-generativa-so-com-benchmark.md`
17. `017-dominio-e-arquitetura-de-marca.md`
