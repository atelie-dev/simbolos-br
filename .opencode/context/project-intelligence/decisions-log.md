<!-- Context: project-intelligence | Project: simbolos-br | Version: 2.7 | Updated: 2026-11-08 -->

# Decisions Log — Símbolos BR

> Cada decisão com o porquê e o que foi rejeitado. Não reabrir sem fato novo.
> O plano completo está em `PLAN.md` (§1.1 lista as travadas).

## D1 — Não reutilizar o acervo legado (2026-11-07)

**Decisão:** os 3.266 JPEG 192×192 do repositório anterior não entram — nem com
aviso de procedência pendente. Só o manifesto (`sha256` + dimensões) é preservado,
como backlog e denylist.

**Por quê:** procedência desconhecida sob MIT é exatamente o erro que o projeto
não repete. Sem URL de captura, não há como cumprir a regra de licença.

**Rejeitado:** publicar marcados como "procedência pendente" — abriria exceção
para 3.266 arquivos e para o próximo lote.

## D2 — Independência do projeto anterior (2026-11-07)

**Decisão:** começar do zero, sem contato e sem aviso; inspiração, não linhagem.

**Por quê:** verificado por hash — **0 dos 1.059 arquivos baixados do Wikimedia é
idêntico** a algum dos 3.266 dele. Não há obra derivada nem obrigação de licença.

**Consequência:** pacotes com nome próprio, nenhum namespace herdado, nenhum
texto sugerindo sucessão. Crédito de inspiração, se houver, é cortesia em
`/sobre`, nunca origem dos dados.

## D3 — Licença em camadas (2026-11-07)

**Decisão:** AGPL-3.0 no serviço, MIT nos pacotes cliente, CC0 nos metadados,
**licença da fonte por imagem** (SPDX), renditions herdam a licença da fonte.
CC BY-SA aceito com selo e filtro `?licenca=livre`. Símbolo oficial publicado
pela própria prefeitura aceito como `LicenseRef-simbolo-oficial-municipal`, sob
quatro condições cumulativas (domínio da prefeitura, símbolo daquele município,
página identificando como oficial, captura com URL + data + hash).

**Por quê:** a licença de cada imagem nunca é do projeto; o que o projeto pode
licenciar é o código e os metadados.

**Rejeitado:** rotular tudo como CC0/domínio público. `LicenseRef` nunca é
apresentada como "livre" nem entra em `brasil-livre.zip`.

## D4 — Fonte canônica + renditions derivadas (2026-11-07)

**Decisão:** contribui-se com **um** original (SVG preferido); o pipeline gera
PNG 512 e JPG 512. Progresso é medido por qualidade da fonte, não por contagem de
extensão.

**Por quê:** zero municípios tinham mais de um formato no acervo inicial; pedir
três arquivos por município produz inconsistência.

## D5 — URL de embed estável, cache com purge (2026-11-07)

**Decisão:** `/embed/v1/{brasao|bandeira}/{cod}.{ext}` é contrato permanente.
Resoluções fixas na v1 (512); tamanhos só na v2 (é por isso que `v1` existe).

**Por quê:** o produto é a URL. Corrigir conteúdo exige purge, não mudança de
caminho.

## D6 — Coleta por enumeração, não por scrape de artigo (2026-11-07)

**Decisão:** Wikidata `P1585`→`P94`/`P41` + categorias do Commons + DNS
`{municipio}.{uf}.gov.br`; LLM só como fallback de extração, com citação
verificável.

**Por quê:** o scrape por artigo rendia 689 brasões; a união medida rendeu 4.353
(78,1%) em ~3 min de API, com casamento exato por código IBGE.

**Rejeitado:** proxy para "acessar a Wikimedia sem restrição". O limite é
solicitação de uma instituição sem fins lucrativos; o caminho é pedir menos
(thumburl 1024) e pedir limite maior se o projeto crescer.

## D7 — LLM nunca escreve procedência (2026-11-07)

**Decisão:** URL, autor, número de lei, data e licença são **capturados**
(HTTP 200 + `sha256` do snapshot). O modelo pode citar; a citação tem que ser
substring literal do material guardado, senão `aceito=false`.

**Por quê:** um número de lei inventado envenena o acervo de um jeito que
nenhuma revisão posterior desfaz.

## D8 — Portão de visão por modelo de decisão (2026-11-08)

**Decisão:** `clef-flash` via `POST /v1/systemone` (probabilidades, zero token de
saída) para classificar tipo/marca d'água/fundo. O chat (`deepseek-v4.1-flash`)
fica para **descrição** (lê listel, escreve texto), não para o portão.

**Por quê:** no conjunto rotulado, clef acertou 3/5 e o chat 1/5; o chat
**inventou marca d'água** num brasão limpo. Além disso, `clef` não sofre
truncamento por raciocínio.

**Complemento determinístico** (nenhum modelo pega): imagem vazia por desvio
padrão < 2; tamanho vira `tier`, não rejeição; proporção > 2,2 sinaliza recorte.

## D9 — Domínio e arquitetura de marca (2026-11-08)

**Decisão:** `coletivo.dev.br` como divisão de código e dados abertos do
`atelie.dev.br`; serviço em `/simbolos`; embed em `cdn.coletivo.dev.br`
(host revisto em D14).

**Por quê:** o ateliê assina o cuidado, o coletivo assina o aberto. O domínio
precisa ser decidido **antes** do primeiro embed público, porque trocar host
depois exige redirect permanente para sempre.

**Rejeitado:** `simbolos.dev.br` (estreito para outros acervos),
`mutirao.dev.br` (mais distintivo, menos descritivo), subdomínio do ateliê
(identidade emprestada, migração custosa).

## D10 — Vetorização generativa só com benchmark (2026-11-08)

**Decisão:** modelo imagem→SVG com priori heráldico é hipótese, não plano. Antes,
biblioteca de partes + traço assistido. Traço automático é rendition de último
recurso, marcado `natureza: vetorizado`.

**Por quê:** priori heráldico produz arte plausível, não fiel — e inventar uma
torre num brasão com citação verdadeira é o pior resultado possível. Medido:
`vtracer` no melhor caso oficial gerou 890 paths, com a marca d'água da fonte
traçada dentro da arte.

## D11 — O catálogo é derivado; a verdade é o sidecar por ativo (2026-11-08)

**Decisão:** cada item publicado grava `dist/meta/v1/{tipo}/{cod}.json` junto com
as renditions. O `catalogo.json` passa a ser agregado derivado, gravado a cada
200 itens por `tmp.replace()` (atômico). A retomada lê, nesta ordem: sidecar →
catálogo → renditions em disco. Item recuperado só do disco é marcado
`reconstruido: true` e `sha256_origem: null`; quando um catálogo com a
procedência completa reaparece, ele atualiza o sidecar.

**Por quê:** o lote publicado chegou a 5.394 pares em disco com **10 registros**
no catálogo, porque a escrita era única no fim. Um reboot custaria 5.384
downloads — cerca de uma hora e mais cinco mil requisições à Wikimedia, a mesma
fonte que já nos limita a 1 req/s.

**Rejeitado:** escrever o catálogo inteiro a cada item (8 mil × ~150 KB de JSON
reescritos por item, e um kill no meio trunca o arquivo) e guardar só arquivos em
disco sem metadado (perde origem e licença, que são o motivo de o acervo existir).

**Consequência:** é o `meta.json` do §6.2 em versão mínima, no lugar que a
publicação já usa (`dist/meta/v1/{tipo}/{cod}.json`). Quando o fluxo de
contribuição existir, `data/assets/{cod}/{tipo}/meta.json` passa a ser o original
e o sidecar do `dist` o derivado. O upload ao R2 sobe `embed/` **e** `meta/`.

## D12 — O original fica; a rendition é derivada (2026-11-08)

**Decisão:** o arquivo de origem, byte a byte, vai para
`data/fontes/v1/{tipo}/{cod}.{ext}`, e o registro guarda `fonte.arquivo`,
`fonte.bytes` e `fonte.sha256`. No SVG não há duplicação: o `.svg` publicado é a
fonte. `simbolos fontes` rebaixa a safra publicada antes desta mudança; hash
diferente do `sha256_origem` não sobrescreve nada — grava em `fontes/conflito/` e
marca `fonte_divergente`.

**Por quê:** a safra já publicada tinha 2.781 itens com fonte maior que 460 px, e
o pipeline descartava o original depois de reduzir — o acervo ficava com a
versão pior e sem como refazer. É o mesmo erro do catálogo, um nível abaixo, e
com o agravante de que links morrem (3 de 19 no piloto).

**Rejeitado:** usar `thumburl` de 1024 como "fonte" — é derivado de terceiro, não
o que o município publicou, e não permite re-renderizar em v2 nem provar o que
foi capturado.

**Custo medido:** 4.937 rasters (os 863 SVGs são pulados), ~950 MB e ~1 h 20 a
1 req/s.

## D13 — Dois buckets, nome por serviço (2026-11-08)

**Decisão:** `simbolos-br-cdn` (público: `embed/`, `meta/`) e
`simbolos-br-acervo` (privado: `fontes/`, `evidencias/`). O nome carrega o
serviço, não a marca: `coletivo` é o guarda-chuva e vai receber outros acervos.

**Por quê:** o domínio customizado de um bucket R2 expõe **tudo** o que está
dentro. Guardar fonte original e PDF de lei no mesmo bucket do embed tornaria o
arquivo privado um download público. Com zero objetos a separação é gratuita;
depois de 1 GB, é migração. E o nome por serviço evita que o primeiro acervo dê
nome ao guarda-chuva dos próximos.

**Rejeitado:** `coletivo-cdn`/`coletivo-acervo` (amarra o bucket à marca e não
diz o conteúdo), bucket único com prefixos "privados" (a proteção dependeria de
Worker, não de ausência de rota).

**Complemento:** o upload é idempotente por `sha256` num livro-razão local;
`Cache-Control` de 7 dias com `stale-while-revalidate` nas imagens e 1 h nos
sidecars. A dev URL `r2.dev` foi desligada quando o domínio próprio entrou — o
contrato é o host do serviço (D14), não a URL de teste.

## D14 — Um host por serviço no CDN, não prefixo em host compartilhado (2026-11-08)

**Decisão:** os ativos ficam em `https://simbolos.coletivo.dev.br/embed/v1/...`,
com o bucket `simbolos-br-cdn` servido por um custom domain próprio. Não há
prefixo de projeto no caminho, e não existe host `cdn.coletivo.dev.br`.

**Por quê:** o custom domain do R2 liga **um host a um bucket**, e o bucket é por
serviço. Prefixo no caminho (`cdn.coletivo.dev.br/simbolos-br/…`) exigiria, no
segundo acervo, ou um bucket público compartilhado — contrariando a convenção
`simbolos-br-*` — ou um Worker roteando por prefixo em toda requisição de imagem.
Com host por serviço, o próximo acervo entra em `saude.coletivo.dev.br` com o
bucket dele, sem tocar neste e sem componente novo no caminho.

**Rejeitado:** `cdn.coletivo.dev.br/simbolos-br/…` (26 mil objetos reenviados e
namespace mutável comum); `simbolos.cdn.coletivo.dev.br` (dois níveis: fora do
wildcard do Universal SSL); Worker de roteamento (um componente a mais para
resolver um problema que o DNS já resolve).

**Consequência:** a URL é mais curta que a alternativa com prefixo e o nome do
serviço aparece no host. `cdn.coletivo.dev.br` foi removido e a dev URL `r2.dev`
desligada. Como o R2 permite vários custom domains por bucket, uma migração
futura pode manter os dois hosts em paralelo antes de desligar o antigo.

## D15 — Direção visual: artesania editorial (2026-11-08)

**Decisão:** Bricolage Grotesque (display) + Source Sans 3 (texto), base creme
quente com **um** accent terracota, raio 14 px em cartão, sombra suave em duas
camadas, movimento 180 ms. Registrado em `site/DESIGN.md`, que passa a ser lei
para toda tela. Selos (licença, tier, revisão) são semânticos e nunca usam o
accent.

**Por quê:** o acervo precisa parecer feito à mão por quem se importa, não
gerado. "O ateliê assina o cuidado; o coletivo assina o aberto" é a frase que
decide cada dúvida de tela.

**Rejeitado:** direção "arquivo público" (Fraunces + verde institucional, só
borda) por soar repartição; direção "instrumento" (mono, densa, turquesa) por
afastar prefeitura e jornalista. Ambas foram desenhadas e comparadas no mesmo
conteúdo antes da escolha.

**Implementação:** Astro estático com `base: /simbolos`, CSS com tokens (sem
framework), fontes autohospedadas em `public/fonts` e busca client-side que só
baixa o índice (5.598 entradas, 92 KB gzip) quando a pessoa interage.

## D16 — Um deployment para portal e acervo (2026-11-08)

**Decisão:** o projeto `coletivo` no Pages publica uma árvore só: `portal/` na
raiz e `site/dist` em `simbolos/`. O `scripts/empacotar_site.py` monta isso e
barra se passar de 20 mil arquivos (limite do Pages Free).

**Por quê:** o Pages publica na raiz do domínio; não existe "montar em
subcaminho". Duas árvores separadas exigiriam um Worker roteando toda requisição
— mais uma peça no caminho de cada imagem.

**Rejeitado:** subdomínio por acervo (`simbolos.coletivo.dev.br` já é o host de
ativos, e o site ficaria sem endereço próprio); dois projetos Pages + Worker.

**Consequência:** portal e acervo compartilham limite de arquivos. Hoje 6.447 de
20 mil (32%); o próximo passo que mais consome arquivo é o `/m/{cod}` estático.

## D17 — URL sem barra, com canonical (2026-11-08)

**Decisão:** `build.format: "file"` e `trailingSlash: "never"`; cada página tem
`link rel="canonical"`. A raiz do serviço (`/simbolos/`) é a única exceção — ali
`index.html` é o diretório.

**Por quê:** o Pages canonicaliza diretório com barra e responde 308 em toda URL
sem ela. Com `pasta/index.html`, cada link interno pagava um redirect; com
`arquivo.html`, `/simbolos/consultar` responde 200 e a barra é que redireciona.

**Rejeitado:** aceitar a barra como canônica (obrigaria a reescrever todos os
links e o CTA); `_redirects` (2.100 entradas, e o problema era o formato, não o
destino).

## D18 — Point-in-polygon com malha fatiada (2026-11-08)

**Decisão:** o botão "onde estou" usa a malha municipal do IBGE (qualidade
mínima) fatiada em **836 células de 1°**, cada uma com código, slug e anéis. O
cliente baixa a célula do ponto (e as vizinhas) e faz teste par-ímpar.

**Por quê:** o cruzamento por sede mais próxima erra em município pequeno cercado
por outro (Águas de São Pedro dentro de Piracicaba). Baixar o GeoJSON inteiro
(3,4 MB) para um clique é absurdo; a célula média tem 10,7 KB e a maior 23,4 KB.

**Rejeitado:** geocodificação reversa em serviço de terceiro (manda a posição do
usuário para fora e cria dependência); centroides como solução final (ficam como
fallback para mar, represa e falha de simplificação).

**Consequência:** 836 arquivos e 9,1 MB a mais no repositório; `simbolos malha`
refaz em segundos quando o IBGE atualizar.

## D19 — Vetorial é por tipo, não por município (2026-11-08)

**Decisão:** o índice carrega `bv` e `fv` (brasão e bandeira vetoriais) em vez de
um único `tier`; busca e lista de estados marcam `●ᵛ` / `◆ᵛ`; a cobertura tem
colunas separadas e os números 573 (brasão) e 597 (bandeira).

**Por quê:** o selo antigo acendia com **qualquer** um dos dois vetorial. Um
município com brasão em SVG e bandeira em raster aparecia como "vetor", o que é
meia-verdade — e a diferença é grande (AP: 19% brasão contra 56% bandeira).

**Rejeitado:** manter "vetor" com tooltip explicando (tooltip não existe no
celular); mostrar dois selos textuais por linha (ruído na lista).

## D20 — PIX com chave UUID, sem txid, QR no build (2026-11-08)

**Decisão:** a chave é um UUID; o BR Code é gerado/validado por `simbolos pix`,
que confere o CRC16 antes de gravar; o QR é gerado no build com `segno` e servido
como SVG estático; o `txid` (campo 62) é omitido.

**Por quê:** o BR Code carrega a chave em texto claro — com e-mail, publicar o
copia-e-cola entrega o e-mail a qualquer scraper. `txid` fixo faz alguns bancos
tratarem o segundo pagamento como repetição; omitir o campo é o "não informado"
do padrão. E o QR gerado localmente evita que a chave passe por terceiro.

**Rejeitado:** chave por e-mail (privacidade); `txid` com `***` textual (omitir é
equivalente e mais curto); serviço de QR de terceiro (a chave sairia do domínio).

**Armadilha registrada:** o CRC cobre o payload inteiro, inclusive o cabeçalho
`6304` do campo 63 — errar isso gera código que o banco recusa sem explicação.

## D21 — Procedência conferível sem rebaixar o acervo (2026-11-08)

**Decisão:** o sidecar carrega `sha1_origem` (o hash que a API do Commons
publica), `bytes_origem`, `capturado_em`/`captura_fonte` e `titulo_commons`, e o
comando `simbolos verificar-fonte` compara cada item em lotes de 50 títulos,
classificando em **igual**, **divergente**, **renomeado** e **sumiu**. O campo
`guarda` diz quantas casas independentes têm o item, e `simbolos risco` publica
o relatório em `data/risco.json`.

**Por quê:** o `sha256` não serve para conferir com a origem — o Commons publica
**sha1**, não sha256. Sem o sha1 no sidecar, a única forma de saber se os bytes
mudaram era rebaixar 1,3 GB (o que o `fontes` fazia, a 1 req/s). Com ele, a
conferência dos 8.379 itens custou **3 min 7 s e 168 requisições**, sem baixar um
arquivo. Resultado da primeira rodada: 8.379 iguais, 0 divergentes, 0 sumidos.

**Rejeitado:** rebaixar tudo para conferir (1,3 GB e ~2 h); guardar só o sha256
(não comparável à origem); classificar risco por tamanho ou por licença em vez de
por existência de cópia independente (licença não é cópia).

**Regra de risco (escolha do mantenedor):** **vetor é sempre baixo** — o SVG
publicado é a fonte, byte a byte, e vai para o git; **raster segue a regra
estrita** e é alto quando fica sem espelho. `espelhos` continua factual (hoje só
`commons`), e o motivo `vetor_versionavel` registra a dívida enquanto os vetores
não estiverem de fato no git.

**Consequência:** os sidecars saíram de `dist/meta/v1` para `data/meta/v1` —
`dist` é saída e pode ser apagada, e a procedência não se regenera sem rebaixar.
Isso alinha a implementação ao que o §6.6 do `PLAN.md` já mandava: `meta.json` no
git. Números da primeira rodada: 68 itens de risco alto (69 `pendente`, dos quais
1 é vetorial), 8.311 baixos; 1.170 vetores com o motivo `vetor_versionavel`.

**Armadilha registrada:** o título do Commons é derivado da URL de upload, e a
URL muda quando o arquivo é renomeado. Por isso título que não resolve **não** é
sumiço — a conferência cai para `list=allimages&aisha1=`, que acha os mesmos
bytes sob o nome novo.

## D22 — O acervo versionado é a fonte, não um backup (2026-11-08)

**Decisão:** `data/vetores/v1/{tipo}/{cod}.svg` (1.170 arquivos, 287 MB) e o
livro-razão `data/ledger/r2-{cdn,acervo}.json` entram no git. A publicação passa
a tentar o arquivo local **antes** da rede (`publicar_item` → `ler_fonte_local`),
e `simbolos vetores --restaurar` devolve os SVGs para `dist`. Renditions
continuam fora do git.

**Por quê:** sem isso o repositório não republica nada — um clone precisaria
rebaixar 1,6 GB do Commons, e os links de origem já morrem (3 de 19 no piloto).
Com o acervo versionado, o fluxo de um fork é clonar → `simbolos vetores
--restaurar` → `simbolos publicar` → `simbolos r2`, sem rede para os 8.379 já
publicados. Verificado num diretório vazio: `publicar_item` devolve
`captura_fonte: "arquivo"` tanto para raster quanto para SVG.

**Rejeitado:** guardar também as renditions (1,1 GB derivados, e cada mudança de
`LADO` acrescentaria 1,1 GB ao histórico para sempre); Git LFS (free tier de 1 GB,
e só os raster têm 1,3 GB); um segundo repositório para os vetores (mais um lugar
para sincronizar, sem ganho — são 287 MB ao lado de 12,7 MB de metadados).

**Consequência:** o motivo `vetor_versionavel` virou `vetor_versionado` e o
`guarda` do vetor passou a listar `git` entre os espelhos — o risco baixo agora
repousa num fato, não numa decisão. Como `data/_catalogo/catalogo.json` já era
versionado, `publicar` funciona mesmo com `dist/` apagada.

**Armadilha registrada:** `data/vetores` e `dist/embed` têm o mesmo conteúdo por
construção. Se divergirem, quem manda é `data/vetores`; `simbolos vetores` recusa
sobrescrever sem `--forcar` e manda o divergente para `data/vetores/conflito/`.

## D23 — Crawl educado: robots, intervalo por host e link vivo (2026-11-08)

**Decisão:** toda requisição HTTP passa por `simbolos/rede.py`, que aplica
intervalo **por host** (1 req/s no padrão), recuo exponencial em 429/503 e
respeito ao `Retry-After`. O `leis` lê `robots.txt` por host (cache de processo:
5xx ou falha bloqueia tudo, 4xx libera) e sonda os caminhos **em série**. O
User-Agent passa a `simbolos-br/0.1 (+https://coletivo.dev.br/simbolos;
contato@atelie.dev.br)`. `verificar-fonte` ganha o ramo de link para origem fora
do Commons.

**Por quê:** `_sondar_caminhos` abria até **8 GETs simultâneos no mesmo servidor**
e `coletar_lote` rodava 3 municípios em paralelo. Site municipal com WAF responde
403, e um projeto que vai pedir dados às prefeituras não pode chegar bloqueado.
O UA anterior apontava para `github.com/simbolos-br/simbolos-br` e
`contato@simbolos.br` — nem repositório, nem domínio existem.

**Rejeitado:** manter o paralelismo pelo tempo (o bloqueio custa mais que os
segundos); ignorar `robots.txt` e culpar o WAF (má-fé); UA genérico ou anônimo
(bloqueio justificado).

**Consequência:** a política é por host, não global — seis prefeituras diferentes
em paralelo não incomodam ninguém, seis no mesmo servidor sim. Sonda medida:
1 município em 80 s e US$ 0,000042, com domínio resolvido por DNS, `robots.txt`
lido e 1 página analisada.

**Armadilha registrada:** `robots.txt` inacessível por **5xx** deve bloquear
(RFC 9309); por **404**, liberar. Tratar os dois igual erra para um dos lados — e
o lado errado é o que quebra a confiança.

## D24 — Crawl oficial concluído: 403 símbolos, teto de 10 no LLM (2026-11-08)

**Resultado medido:** 1.218 municípios sem cobertura Wikidata/Commons, 1.218
processados, **zero falha de LLM** na última passada. 2.104 páginas analisadas,
**719 ocorrências de símbolo → 403 URLs únicas** (180 repetem, no máximo 3×),
**368 municípios com símbolo (30%)**. 10 atos de lei reconhecidos, **0 PDFs**.
Custo total US$ 0,20 (duas passadas) e 5h de parede.

**Desfecho dos municípios:** 988 com home lida, 106 barrados por `robots.txt`,
97 com domínio não resolvido, 24 com erro de home, 3 com falha de DNS. Os 203
que o crawl não visita são limite estrutural (robots e padrão de domínio), não
retrabalho.

**Teto do provedor:** a 24 chamadas simultâneas, 39% das páginas voltavam sem
resposta; a 10, 0%. O número não vem de documentação — vem de um experimento
natural: AL rodou a 3 sem falha e todas as UFs a 24 falharam entre 35% e 51%.

**Consequência:** a cobertura do acervo sai de 4.788 para 5.156 municípios
(92,5%), **se** os 403 forem importados. Eles entram como `balde: pendente` e
`origem` fora do Commons, portanto `risco: alto` — a única cópia é o R2.

**Dívida registrada:** o `extrair` já devolvia `tipo` (brasao/bandeira) e o
coletor descartava. Corrigido para as próximas safras; nesta, 141 das 403 URLs
não têm pista de tipo nem no nome do arquivo e dependem do portão de visão.

## D25 — O crawl não publica; o importador classifica (2026-11-08)

**Decisão:** `simbolos importar` lê `data/_coleta/leis.jsonl`, deduplica por URL,
baixa uma vez com a polidez de sempre, roda o portão de visão com o **município
no `state`** (para decidir tipo *e* identidade, não só "é brasão"), guarda o
original em `data/fontes` e escreve o candidato no catálogo com
`balde: pendente` e `licenca: NOASSERTION`. Quem renderiza é `publicar`.

**Por quê:** o crawl guarda URL, não arquivo, e não diz sob qual chave publicar.
Sem o tipo, o catálogo não sabe se é `brasao` ou `bandeira`; sem o arquivo, a
publicação teria que rebaixar tudo de novo. E afirmar `livre` em 403 arquivos de
site de prefeitura é promessa que o projeto não pode sustentar — o `pendente` é o
que permite publicar sem mentir.

**Rejeitado:** publicar direto do crawl (sem arquivo, sem tipo, sem gate);
inferir tipo só pelo nome do arquivo (65% de cobertura, e no teste de 5 itens a
visão divergiu do palpite); marcar como livre por "símbolo oficial não é
protegido" (é decisão jurídica, não de engenharia).

**Consequência:** os importados entram com `guarda` alto e três motivos —
`origem_fora_do_commons`, `licenca_pendente`, `nao_verificado` — e ficam fora dos
pacotes livres. A visão custou US$ 0,0001 por imagem.

**Armadilha registrada:** o mesmo arquivo aparece em várias páginas do mesmo
município (719 ocorrências para 403 URLs). Deduplicar por URL antes de importar,
senão o acervo ganha centenas de itens que são o mesmo arquivo.

## D26 — Rejeição é registro, não apagamento (2026-11-09)

**Decisão:** `simbolos rejeitar` marca o item no catálogo e põe o sidecar em
`estado: rejeitado`; `publicar` e o índice ignoram rejeitados; `r2
--limpar-rejeitados` apaga as três renditions e o sidecar do CDN, e o purge tira
do edge. O original fica em `data/fontes` como evidência do que foi recusado.

**Por quê:** a revisão visual do mantenedor confirmou 4 dos 5 erros de tipo e
todos os lockups. E `fundo_limpo` era **calculado e ignorado** na decisão — o
sinal existia e não valia nada, que é pior que não existir.

**Portão v2:** desempate explícito no `tipo` ("pano retangular com escudo ao
centro é bandeira; o escudo dentro do pano não faz dele brasão"),
`tem_marca_dagua` passa a cobrir selo/prêmio **ao lado** da arte, e brasão exige
`fundo_limpo` — bandeira não, porque pano é retangular por natureza e exigir
fundo limpo reprovava bandeira limpa. A importação passa a guardar
`perguntas_versao`, `fundo_limpo`, `marca_dagua`, `precisa_recorte` e
`rejeitar_motivo`.

**Rejeitado:** apagar arquivo e histórico (o acervo registra o que recusou e por
quê); exigir fundo limpo de bandeira.

**Consequência:** rejeitados Toritama, Materlândia, Vertentes e São Gabriel
(brasão) — 4.951 → 4.947 municípios cobertos. O v2 acerta o tipo em Toritama e
Vertentes e classifica Cavalcante como logo, mas **ainda não pega selo ao lado**
(Buritis); os 84 brasões em paisagem seguem publicados, com `precisa_recorte`
registrado para o recorte futuro.

**Armadilha registrada:** `r2` só sobe o que o catálogo lista, então rejeitar não
tira nada do CDN; e o edge guarda png/jpg por 7 dias (`cf-cache-status: HIT` com
`age` alto). Apagar do R2 sem **purge** deixa o arquivo servindo. A zona
`coletivo.dev.br` está ativa agora e o purge responde 200 — o 403 antigo era de
zona pendente, não de permissão.

## D27 — Canal de relatos: máquina propõe, humano decide (2026-11-09)

**Decisão:** formulário em `/simbolos/contribuir` (quatro passos, escolhas
fechadas), Worker na rota `/simbolos/api/relatar`, Turnstile `managed`, KV para
limite por IP e dedupe, e uma **GitHub App** (`simbolos-br-relatos`, Issues:
write) abrindo issue com o rótulo `aguardando-confirmacao`.

**Por quê:** a revisão manual achou 88 defeitos que o portão de visão não pega —
o canal é o complemento humano. E o acervo tem 258 itens `pendente` sem licença
e zero PDF de ato: o formulário pede **fonte oficial**, então é entrada de
procedência, não só de reclamação.

**Rejeitado:** PAT pessoal (autoria confusa — parece que a pessoa reportou —,
credencial de até 1 ano e presa a uma conta); upload de arquivo (o Worker viraria
armazém e superfície de abuso); item em texto livre (relato inaplicável).

**Consequência:** nenhum comando lê issue e altera o acervo. Aplicar é manual:
`simbolos rejeitar` ou `simbolos importar`, e fechar a issue citando o commit. O
Worker só enfileira.

**Armadilha registrada:** a chave privada da App **vazou no chat** durante a
configuração. Precisa ser revogada na App e trocada com `wrangler secret put
GITHUB_PRIVATE_KEY`. Turnstile: a sitekey é pública (página + var do Worker), o
secret é secret do Worker.
