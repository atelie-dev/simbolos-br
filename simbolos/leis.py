"""Caca a lei que instituiu o simbolo e o PDF oficial.

Rota: dominio por DNS -> home -> paginas de legislacao/simbolos -> texto ->
LLM acha o ato (com citacao verificada) -> link de PDF -> checagem de vetor.

Paralelismo: entre municípios (hosts diferentes, seguro), entre as páginas de um
município e entre as duas perguntas de cada página — a rede de um município já
terminou quando o LLM começa. Dentro de um host, as requisições são sequenciais e
espaçadas. Um semáforo separado limita as chamadas ao provedor.
"""

from __future__ import annotations

import html
import json
import re
import socket
import subprocess
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from . import DATA, USER_AGENT, maritaca, publicacao, rede
from .nomes import compacto

COLETA = DATA / "_coleta" / "leis.jsonl"

PADROES_DOMINIO = ("{c}.{uf}.gov.br", "{s}.{uf}.gov.br", "www.{c}.{uf}.gov.br")

PISTAS_PAGINA = re.compile(
    r"legisla|lei|decreto|simbol|brasao|brasão|escudo|bandeira|historia|história"
    r"|o-municipio|municipio|sobre",
    re.IGNORECASE,
)
_LINK = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")

# Ordem de prioridade do link: símbolo primeiro, legislação genérica por último.
PRIORIDADE = (
    (re.compile(r"simbol|brasao|brasão|escudo|bandeira", re.IGNORECASE), 3),
    (re.compile(r"historia|história|o-municipio|municipio|a-cidade|cidade", re.IGNORECASE), 2),
    (re.compile(r"legisla|lei|decreto", re.IGNORECASE), 1),
)

# Caminhos comuns quando o menu não expõe o link, do mais provável ao menos.
CAMINHOS = (
    "/cidade/simbolo",
    "/simbolos",
    "/o-municipio/sua-historia",
    "/o-municipio/historia",
    "/o-municipio",
    "/a-cidade",
    "/brasao",
    "/historia",
)

TIMEOUT_PAGINA = 20.0
TIMEOUT_SONDAGEM = 6.0

# Quanto da página vai para o modelo. A página inteira custa caro e o que
# interessa está perto de palavras-chave.
MAX_CHARS_TEXTO = 4000
MAX_TAGS = 220
_JANELA = 700
_MARCAS = re.compile(
    r"bras[aã]o|bras[oõ]es|simbol|escudo|bandeira|institui|lei\s+n|decreto|"
    r"her[aá]ldic|armas",
    re.IGNORECASE,
)
_TAG_INTERESSE = re.compile(r"<(?:img|a)\b[^>]*>", re.IGNORECASE)


def _janelas(texto: str, max_chars: int = MAX_CHARS_TEXTO, janela: int = _JANELA) -> str:
    """Mantém a cabeça do texto e janelas em volta das palavras que importam."""
    if len(texto) <= max_chars:
        return texto
    partes = [texto[:1200]]
    gasto = 1200
    for m in _MARCAS.finditer(texto):
        if gasto >= max_chars:
            break
        ini = max(0, m.start() - janela)
        fim = min(len(texto), m.end() + janela)
        partes.append(texto[ini:fim])
        gasto += fim - ini
    return " ".join(partes)[:max_chars]


def fragmento(html: str) -> str:
    """Recorte do HTML: todas as tags de imagem/link + texto em volta dos temas.

    A citação é verificada contra o HTML completo, então cortar aqui não afrouxa
    o portão — só reduz o que o modelo precisa ler.
    """
    tags = _TAG_INTERESSE.findall(html)[:MAX_TAGS]
    return " ".join(tags) + "\n\n" + _janelas(_texto(html))


def resolver_dominio(nome: str, slug: str, uf: str) -> str | None:
    for padrao in PADROES_DOMINIO:
        host = padrao.format(c=compacto(nome), s=slug, uf=uf.lower())
        try:
            socket.getaddrinfo(host, None)
            return f"https://{host}"
        except OSError:
            continue
    return None


def _texto(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"\s+", " ", _TAG.sub(" ", html)).strip()


def _peso(url: str, rotulo: str) -> int:
    """Prioriza símbolo > história/município > legislação. Olha o caminho, não a query."""
    caminho = urlparse(url).path.lower()
    texto = rotulo.lower()
    if re.search(r"simbol|brasao|escudo|bandeira", caminho + texto):
        return 4
    if re.search(r"historia|sua-historia|a-cidade|o-municipio", caminho):
        return 3
    if re.search(r"historia|municipio", texto):
        return 2
    if re.search(r"legisla|/lei/|/decreto/", caminho):
        return 1
    return 0


def paginas_candidatas(html: str, base: str, limite: int = 3) -> list[tuple[str, str]]:
    """(url, rotulo) das páginas candidatas, por prioridade."""
    vistos: set[str] = set()
    achadas: list[tuple[int, str, str]] = []
    for href, rotulo in _LINK.findall(html):
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(base, href)
        chave = str(url).split("?")[0]
        if chave in vistos:
            continue
        texto = re.sub(r"\s+", " ", _TAG.sub(" ", rotulo)).strip()[:80]
        peso = _peso(str(url), texto)
        if peso <= 0:
            continue
        vistos.add(chave)
        achadas.append((peso, str(url), texto))

    achadas.sort(key=lambda x: x[0], reverse=True)
    return [(url, rotulo) for _, url, rotulo in achadas[:limite]]


def montar_alvos(html: str, base: str, limite: int) -> list[tuple[str, str]]:
    """Links do menu + caminhos sondados, deduplicados e ordenados por peso."""
    candidatos = paginas_candidatas(html, base, 50)
    vistos = {url for url, _ in candidatos}
    for url, rotulo in _sondar_caminhos(base, vistos, limite):
        candidatos.append((url, rotulo))
    candidatos.sort(key=lambda x: _peso(x[0], x[1]), reverse=True)
    return candidatos[:limite]


def paginas_do_pdf(pdf: Path) -> dict:
    """Paginas sem raster (provavel vetor) e total de paginas."""
    try:
        info = subprocess.run(
            ["pdfinfo", str(pdf)], check=False, capture_output=True, text=True
        ).stdout
        total = int(re.search(r"Pages:\s+(\d+)", info).group(1))
        lista = subprocess.run(
            ["pdfimages", "-list", str(pdf)], check=False, capture_output=True, text=True
        ).stdout
    except Exception:  # noqa: BLE001
        return {"paginas": None, "vetoriais": []}
    com_raster = {
        int(ln.split()[0])
        for ln in lista.splitlines()[2:]
        if ln.strip() and ln.split()[0].isdigit()
    }
    return {"paginas": total, "vetoriais": [n for n in range(1, total + 1) if n not in com_raster]}


# robots.txt por host, lido uma vez por execução. O cache é de processo: a
# coleta de um município inteiro acontece dentro de uma execução só.
_ROBOTS: dict[str, RobotFileParser | None] = {}


def _bloqueia_tudo() -> RobotFileParser:
    """robots.txt inacessível por erro de servidor: RFC 9309 manda não confiar."""
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /"])
    return parser


def _ler_robots(base: str) -> RobotFileParser | None:
    """None = sem restrição (inclusive 404). 5xx ou falha = bloqueia tudo."""
    try:
        resposta = rede.requisitar(f"{base}/robots.txt", tentativas=2, timeout=15.0)
    except Exception:  # noqa: BLE001
        return _bloqueia_tudo()
    if resposta.status_code >= 500:
        return _bloqueia_tudo()
    if resposta.status_code >= 400:
        return None
    parser = RobotFileParser()
    parser.parse(resposta.text.splitlines())
    return parser


def _robots(url: str) -> RobotFileParser | None:
    partes = urlparse(url)
    if not partes.scheme or not partes.netloc:
        return None
    base = f"{partes.scheme}://{partes.netloc}"
    if base not in _ROBOTS:
        _ROBOTS[base] = _ler_robots(base)
    return _ROBOTS[base]


def permite(url: str) -> bool:
    """O robots.txt do host autoriza este caminho?"""
    parser = _robots(url)
    return parser is None or parser.can_fetch(USER_AGENT, url)


def _sondar_caminhos(base: str, ja_temos: set[str], quantos: int) -> list[tuple[str, str]]:
    """Testa os caminhos comuns **em série**, um por vez no mesmo host.

    Sondar em paralelo era o que dava até oito requisições simultâneas num
    servidor de prefeitura — e 403 nos que têm WAF. O ganho de tempo não paga o
    bloqueio: seis municípios diferentes em paralelo já usam a banda.
    """
    if quantos <= 0:
        return []
    urls = []
    for caminho in CAMINHOS:
        url = urljoin(base + "/", caminho.lstrip("/"))
        if url not in ja_temos:
            urls.append((url, f"(sondado) {caminho}"))

    achados: list[tuple[str, str]] = []
    for url, rotulo in urls:
        if not permite(url):
            continue
        try:
            resposta = rede.requisitar(url, timeout=TIMEOUT_SONDAGEM, tentativas=2)
        except Exception:  # noqa: BLE001, S112 - sondagem que falha e resultado, nao erro
            continue
        if resposta.status_code == 200 and len(resposta.text) > 500:
            achados.append((url, rotulo))
            if len(achados) >= quantos:
                break
    return achados


def coletar_municipio(
    m: dict,
    *,
    provedor: str | None = None,
    modelo: str | None = None,
    limite_paginas: int = 3,
    flex: bool = True,
    baixar_pdf: bool = True,
    semaforo: threading.Semaphore | None = None,
) -> dict:
    inicio = time.time()
    registro: dict = {
        "codigo": m["codigo"],
        "uf": m["uf"],
        "municipio": m["nome"],
        "dominio": None,
        "paginas": [],
        "ato": None,
        "ato_aceito": False,
        "pdf": None,
        "pdf_vetorial": None,
        "custo": 0.0,
        "moeda": None,
    }

    dominio = resolver_dominio(m["nome"], m["slug"], m["uf"])
    if not dominio:
        registro["erro"] = "dominio_nao_resolvido"
        registro["segundos"] = round(time.time() - inicio, 1)
        return registro
    registro["dominio"] = dominio

    if not permite(dominio):
        registro["erro"] = "robots_disallow"
        registro["segundos"] = round(time.time() - inicio, 1)
        return registro

    try:
        home = rede.requisitar(dominio, timeout=TIMEOUT_PAGINA)
        home.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        registro["erro"] = f"home: {exc}"[:160]
        registro["segundos"] = round(time.time() - inicio, 1)
        return registro

    alvos = montar_alvos(home.text, dominio, limite_paginas)

    # 1) Rede: as páginas candidatas, uma por vez no mesmo host.
    baixadas: list[tuple[str, str, str]] = []
    for url, rotulo in alvos:
        if not permite(url):
            registro["paginas"].append({"url": url, "rotulo": rotulo, "robots": "disallow"})
            continue
        try:
            pagina = rede.requisitar(url, timeout=TIMEOUT_PAGINA)
            pagina.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            registro["paginas"].append({"url": url, "rotulo": rotulo, "erro": str(exc)[:120]})
            continue
        baixadas.append((url, rotulo, pagina.text))

    # 2) LLM: todas as páginas de uma vez. É aqui que o tempo vai, e esperar o
    #    flex página por página fazia cada município custar N rodadas em série.
    #    O slot de rede já foi liberado antes desta fase começar.
    if baixadas:
        with ThreadPoolExecutor(max_workers=min(len(baixadas) * 2, 6)) as ex:
            futuros = []
            for url, rotulo, html in baixadas:
                futuros.append(
                    (
                        url,
                        rotulo,
                        ex.submit(
                            _com_semaforo,
                            semaforo,
                            maritaca.achar_ato,
                            _janelas(_texto(html)),
                            url,
                            provedor=provedor,
                            modelo=modelo,
                            flex=flex,
                        ),
                        ex.submit(
                            _com_semaforo,
                            semaforo,
                            maritaca.extrair,
                            fragmento(html),
                            url,
                            provedor=provedor,
                            modelo=modelo,
                            flex=flex,
                        ),
                    )
                )

            for url, rotulo, f_ato, f_simbolo in futuros:
                ato = f_ato.result()
                simbolo = f_simbolo.result()

                for r in (ato, simbolo):
                    uso = r.get("uso") or {}
                    if uso.get("custo") is not None:
                        registro["custo"] += uso["custo"]
                        registro["moeda"] = uso.get("moeda")

                registro["paginas"].append(
                    {
                        "url": url,
                        "rotulo": rotulo,
                        "ato": ato.get("ato"),
                        "ato_aceito": ato.get("aceito"),
                        "trecho": ato.get("trecho"),
                        "url_pdf": ato.get("url_pdf"),
                        "simbolo": simbolo.get("url_ativo"),
                        "simbolo_aceito": simbolo.get("aceito"),
                        # O modelo já responde brasao/bandeira: guardar é de graça,
                        # e perder obriga a refazer a página inteira depois.
                        "simbolo_tipo": simbolo.get("tipo"),
                        "simbolo_confianca": simbolo.get("confianca"),
                    }
                )
                if ato.get("aceito") and registro["ato"] is None:
                    registro["ato"] = ato.get("ato")
                    registro["ato_aceito"] = True
                if ato.get("url_pdf") and not registro["pdf"]:
                    registro["pdf"] = ato["url_pdf"]

    if baixar_pdf and registro["pdf"]:
        # Evidencia de procedencia: o PDF do ato tem que sobreviver ao reboot.
        # /tmp aqui e zram (RAM) — nada que prove algo pode morar la.
        destino = DATA / "evidencias" / "pdf" / f"{m['codigo']}.pdf"
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not permite(registro["pdf"]):
                raise RuntimeError("robots: disallow")
            r = rede.requisitar(registro["pdf"], timeout=90.0)
            r.raise_for_status()
            if "pdf" in (r.headers.get("content-type") or "").lower() or r.content[:4] == b"%PDF":
                destino.write_bytes(r.content)
                registro["pdf_vetorial"] = paginas_do_pdf(destino)
        except Exception as exc:  # noqa: BLE001
            registro["pdf_vetorial"] = {"erro": str(exc)[:120]}

    registro["segundos"] = round(time.time() - inicio, 1)
    return registro


def _com_semaforo(semaforo: threading.Semaphore | None, funcao, *args, **kwargs):
    """Segura o teto global de chamadas ao provedor, e nada mais.

    O semáforo é para o LLM, não para o site: quantas chamadas de modelo podem
    estar em voo, independente de quantos municípios estão sendo lidos. A
    polidez com o servidor municipal é outra coisa e vive em `rede`.
    """
    if semaforo is None:
        return funcao(*args, **kwargs)
    with semaforo:
        return funcao(*args, **kwargs)


def _incompleto(registro: dict) -> bool:
    """O LLM falhou neste município? Então ele não conta como feito.

    `ato_aceito` nulo numa página baixada, sem erro de HTTP nem robots, é falha
    do modelo (429 esgotado ou timeout) — não é página sem lei. Tratar os dois
    igual faria a retomada pular justamente o que precisa ser refeito.
    """
    for pagina in registro.get("paginas") or []:
        if pagina.get("erro") or pagina.get("robots"):
            continue
        if pagina.get("ato_aceito") is None:
            return True
    return False


def coletar_lote(
    municipios: Iterable[dict],
    saida: Path,
    *,
    provedor: str | None = None,
    modelo: str | None = None,
    limite_paginas: int = 3,
    flex: bool = True,
    paralelismo: int = 6,
    paralelismo_llm: int = 12,
    pausa: float = 0.0,
) -> dict:
    # A retomada olha o último registro de cada município: quem teve falha de
    # LLM volta para a fila, mesmo já estando no arquivo.
    ultimo: dict[str, dict] = {}
    if saida.exists():
        for linha in saida.read_text().splitlines():
            if not linha.strip():
                continue
            try:
                registro = json.loads(linha)
            except json.JSONDecodeError:
                continue
            ultimo[registro["codigo"]] = registro
    feitos = {codigo for codigo, reg in ultimo.items() if not _incompleto(reg)}
    incompletos = len(ultimo) - len(feitos)

    pendentes = [m for m in municipios if m["codigo"] not in feitos]
    resumo = {
        "processados": 0,
        "com_ato": 0,
        "com_pdf": 0,
        "com_pdf_vetorial": 0,
        "incompletos": incompletos,
        "custos": {},
        "segundos": 0.0,
    }
    if incompletos:
        print(f"refazendo {incompletos} municipios com falha de LLM", flush=True)
    saida.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    # Teto de chamadas ao provedor. Mais municípios em voo que chamadas de LLM:
    # enquanto um espera o flex, outro está lendo página.
    semaforo = threading.Semaphore(max(1, paralelismo_llm))

    with ThreadPoolExecutor(max_workers=max(1, paralelismo)) as ex, saida.open("a") as f:
        futuros = {
            ex.submit(
                coletar_municipio,
                m,
                provedor=provedor,
                modelo=modelo,
                limite_paginas=limite_paginas,
                flex=flex,
                semaforo=semaforo,
            ): m
            for m in pendentes
        }
        for futuro in as_completed(futuros):
            m = futuros[futuro]
            try:
                registro = futuro.result()
            except Exception as exc:  # noqa: BLE001
                registro = {
                    "codigo": m["codigo"],
                    "uf": m["uf"],
                    "municipio": m["nome"],
                    "paginas": [],
                    "ato_aceito": False,
                    "pdf": None,
                    "custo": 0.0,
                    "moeda": None,
                    "erro": str(exc)[:160],
                    "segundos": None,
                }
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            f.flush()
            resumo["processados"] += 1
            resumo["com_ato"] += int(bool(registro["ato_aceito"]))
            resumo["com_pdf"] += int(bool(registro["pdf"]))
            resumo["com_pdf_vetorial"] += int(
                bool((registro.get("pdf_vetorial") or {}).get("vetoriais"))
            )
            if registro.get("moeda"):
                moeda = registro["moeda"]
                resumo["custos"][moeda] = resumo["custos"].get(moeda, 0.0) + registro["custo"]
            acumulado = " ".join(f"{k} {v:.6f}" for k, v in resumo["custos"].items()) or "-"
            print(
                f"{registro['municipio']}/{registro['uf']} "
                f"ato={'sim' if registro['ato_aceito'] else 'nao'} "
                f"pdf={'sim' if registro['pdf'] else 'nao'} "
                f"{registro.get('segundos')}s | {acumulado}",
                flush=True,
            )
            if pausa:
                time.sleep(pausa)

    resumo["segundos"] = round(time.time() - inicio, 1)
    return resumo


def _ultimos(caminho: Path) -> dict[str, dict]:
    """Último registro de cada município — o arquivo é append-only."""
    ultimo: dict[str, dict] = {}
    if not caminho.exists():
        return ultimo
    for linha in caminho.read_text().splitlines():
        if not linha.strip():
            continue
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError:
            continue
        ultimo[registro["codigo"]] = registro
    return ultimo


# A lei existe para o símbolo que ela institui. Quando o texto nomeia um tipo,
# aplicar o ato ao outro seria afirmar o que a norma não diz — "institui o
# brasão" no card da bandeira é uma frase errada, ainda que o link esteja certo.
_DE_BRASAO = re.compile(r"bras[aã]o|escudo|armas", re.IGNORECASE)
_DE_BANDEIRA = re.compile(r"bandeira|pavilh", re.IGNORECASE)


def _tipos(texto: str) -> tuple[str, ...]:
    brasao = bool(_DE_BRASAO.search(texto))
    bandeira = bool(_DE_BANDEIRA.search(texto))
    if brasao and not bandeira:
        return ("brasao",)
    if bandeira and not brasao:
        return ("bandeira",)
    # Nem nomeia, ou nomeia os dois: a norma trata dos símbolos do município.
    return ("brasao", "bandeira")


def atos_aceitos(caminho: Path = COLETA) -> dict[str, dict]:
    """Lei confirmada por município, com a página e o trecho que a sustentam.

    O texto do ato sozinho não prova nada: sem a página onde ele aparece,
    ninguém confere depois. O registro guarda os três.
    """
    saida: dict[str, dict] = {}
    for codigo, registro in _ultimos(caminho).items():
        if not registro.get("ato_aceito") or not registro.get("ato"):
            continue
        pagina = next((p for p in registro.get("paginas") or [] if p.get("ato_aceito")), {})
        trecho = html.unescape((pagina.get("trecho") or "").strip())
        saida[codigo] = {
            "texto": html.unescape(registro["ato"].strip()),
            "fonte": pagina.get("url"),
            "trecho": trecho or None,
        }
    return saida


def aplicar_atos(*, caminho: Path = COLETA) -> dict:
    """Grava a lei nos sidecars já publicados. Idempotente.

    A coleta é do agregado (`leis.jsonl`), mas quem manda é o item: só recebe a
    lei o sidecar que está publicado. Rejeitado e não publicado ficam de fora —
    a norma de um símbolo que o acervo não serve não é dado nosso.
    """
    atos = atos_aceitos(caminho)
    resumo = {"candidatos": len(atos), "gravados": 0, "sem_sidecar": 0, "sem_publicacao": 0}
    for codigo, ato in atos.items():
        tipos = _tipos(ato["texto"])
        achou = False
        for tipo in tipos:
            arquivo = publicacao.META / tipo / f"{codigo}.json"
            if not arquivo.exists():
                continue
            registro = json.loads(arquivo.read_text())
            if registro.get("estado") != "publicado":
                resumo["sem_publicacao"] += 1
                continue
            registro["ato"] = ato
            publicacao.gravar_meta(registro)
            resumo["gravados"] += 1
            achou = True
        if not achou:
            resumo["sem_sidecar"] += 1
    return resumo
