"""Mapa canonico municipio -> arquivo via Wikidata (P1585 -> P94/P41).

Uma consulta SPARQL devolve os 5.571 codigos IBGE com brasao e bandeira quando
existem. E o casamento exato que o scrape por artigo nunca teve.
"""

from __future__ import annotations

import time
from urllib.parse import unquote

import httpx

from . import USER_AGENT

SPARQL = "https://query.wikidata.org/sparql"

CONSULTA = """
SELECT ?codigo ?brasao ?bandeira WHERE {
  ?item wdt:P1585 ?codigo .
  OPTIONAL { ?item wdt:P94 ?brasao }
  OPTIONAL { ?item wdt:P41 ?bandeira }
}
"""


def mapa(tentativas: int = 3) -> dict[str, dict[str, str]]:
    """{codigo_ibge: {"brasao": arquivo, "bandeira": arquivo}}."""
    ultimo: Exception | None = None
    for i in range(tentativas):
        try:
            r = httpx.get(
                SPARQL,
                params={"query": CONSULTA, "format": "json"},
                headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
                timeout=120.0,
            )
            r.raise_for_status()
            dados = r.json()
            break
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            time.sleep(3 * (i + 1))
    else:
        raise RuntimeError("SPARQL do Wikidata falhou") from ultimo

    saida: dict[str, dict[str, str]] = {}
    for b in dados["results"]["bindings"]:
        codigo = b["codigo"]["value"]
        item = saida.setdefault(codigo, {})
        if "brasao" in b:
            item["brasao"] = b["brasao"]["value"]
        if "bandeira" in b:
            item["bandeira"] = b["bandeira"]["value"]
    return saida


def titulos(mapa: dict[str, dict[str, str]]) -> list[str]:
    """Todos os nomes de arquivo distintos citados no mapa."""
    return sorted({arquivo for item in mapa.values() for arquivo in item.values()})


def titulo_normalizado(valor: str) -> str:
    """Converte o valor de P94/P41 em titulo do Commons.

    A maioria e 'Brasão de X.svg', mas parte do Wikidata guarda uma URL
    (Special:FilePath/...). Os dois formatos viram 'File:Nome do arquivo.ext'.
    """
    valor = valor.strip()
    if valor.startswith(("http://", "https://")):
        caminho = valor.split("/Special:FilePath/", 1)[-1]
        caminho = caminho.split("?", 1)[0].split("#", 1)[0]
        valor = unquote(caminho).replace("_", " ")
    if valor.lower().startswith("file:"):
        valor = valor[5:].strip()
    return f"File:{valor}"
