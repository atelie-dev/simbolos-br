"""Caca a lei que instituiu o simbolo e o PDF oficial.

Rota: dominio por DNS -> home -> paginas de legislacao/simbolos -> texto ->
LLM acha o ato (com citacao verificada) -> link de PDF -> checagem de vetor.

Paralelismo: entre municipios (hosts diferentes, seguro) e entre as duas
perguntas de cada pagina. Dentro de um host, as paginas sao sequenciais.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from . import DATA, USER_AGENT, maritaca
from .nomes import compacto

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


def _sondar_caminhos(base: str, ja_temos: set[str], quantos: int) -> list[tuple[str, str]]:
    """Testa os caminhos comuns em paralelo, com timeout curto.

    Site que não responde em 6 s não vai responder melhor em 25 — e esperar em
    série era o que fazia cada município custar mais de um minuto.
    """
    if quantos <= 0:
        return []
    urls = []
    for caminho in CAMINHOS:
        url = urljoin(base + "/", caminho.lstrip("/"))
        if url not in ja_temos:
            urls.append((url, f"(sondado) {caminho}"))

    def testar(item: tuple[str, str]) -> tuple[str, str] | None:
        url, rotulo = item
        try:
            r = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_SONDAGEM,
                follow_redirects=True,
            )
        except Exception:  # noqa: BLE001
            return None
        return (url, rotulo) if r.status_code == 200 and len(r.text) > 500 else None

    achados: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=len(urls) or 1) as ex:
        for resultado in ex.map(testar, urls):
            if resultado and len(achados) < quantos:
                achados.append(resultado)
    return achados


def coletar_municipio(
    m: dict,
    *,
    provedor: str | None = None,
    modelo: str | None = None,
    limite_paginas: int = 3,
    flex: bool = True,
    baixar_pdf: bool = True,
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

    try:
        home = httpx.get(
            dominio,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_PAGINA,
            follow_redirects=True,
        )
        home.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        registro["erro"] = f"home: {exc}"[:160]
        registro["segundos"] = round(time.time() - inicio, 1)
        return registro

    alvos = montar_alvos(home.text, dominio, limite_paginas)
    for url, rotulo in alvos:
        try:
            pagina = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_PAGINA,
                follow_redirects=True,
            )
            pagina.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            registro["paginas"].append({"url": url, "rotulo": rotulo, "erro": str(exc)[:120]})
            continue

        texto = _texto(pagina.text)
        enviado = fragmento(pagina.text)
        # As duas perguntas são independentes: rodam juntas.
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_ato = ex.submit(
                maritaca.achar_ato,
                _janelas(texto),
                url,
                provedor=provedor,
                modelo=modelo,
                flex=flex,
            )
            f_simbolo = ex.submit(
                maritaca.extrair,
                enviado,
                url,
                provedor=provedor,
                modelo=modelo,
                flex=flex,
            )
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
            }
        )
        if ato.get("aceito") and registro["ato"] is None:
            registro["ato"] = ato.get("ato")
            registro["ato_aceito"] = True
        if ato.get("url_pdf") and not registro["pdf"]:
            registro["pdf"] = ato["url_pdf"]
        if registro["ato_aceito"] and registro["pdf"]:
            break

    if baixar_pdf and registro["pdf"]:
        # Evidencia de procedencia: o PDF do ato tem que sobreviver ao reboot.
        # /tmp aqui e zram (RAM) — nada que prove algo pode morar la.
        destino = DATA / "evidencias" / "pdf" / f"{m['codigo']}.pdf"
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:
            r = httpx.get(
                registro["pdf"],
                headers={"User-Agent": USER_AGENT},
                timeout=90.0,
                follow_redirects=True,
            )
            r.raise_for_status()
            if "pdf" in (r.headers.get("content-type") or "").lower() or r.content[:4] == b"%PDF":
                destino.write_bytes(r.content)
                registro["pdf_vetorial"] = paginas_do_pdf(destino)
        except Exception as exc:  # noqa: BLE001
            registro["pdf_vetorial"] = {"erro": str(exc)[:120]}

    registro["segundos"] = round(time.time() - inicio, 1)
    return registro


def coletar_lote(
    municipios: Iterable[dict],
    saida: Path,
    *,
    provedor: str | None = None,
    modelo: str | None = None,
    limite_paginas: int = 3,
    flex: bool = True,
    paralelismo: int = 6,
    pausa: float = 0.0,
) -> dict:
    feitos: set[str] = set()
    if saida.exists():
        for linha in saida.read_text().splitlines():
            try:
                feitos.add(json.loads(linha)["codigo"])
            except Exception:  # noqa: BLE001, S110
                pass

    pendentes = [m for m in municipios if m["codigo"] not in feitos]
    resumo = {
        "processados": 0,
        "com_ato": 0,
        "com_pdf": 0,
        "com_pdf_vetorial": 0,
        "custos": {},
        "segundos": 0.0,
    }
    saida.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.time()

    with ThreadPoolExecutor(max_workers=max(1, paralelismo)) as ex, saida.open("a") as f:
        futuros = {
            ex.submit(
                coletar_municipio,
                m,
                provedor=provedor,
                modelo=modelo,
                limite_paginas=limite_paginas,
                flex=flex,
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
