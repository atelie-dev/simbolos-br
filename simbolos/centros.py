"""Coleta as coordenadas da sede de cada município no Wikidata (P625).

Serve para o botão "ver o brasão da minha cidade": o navegador pega a posição,
o site cruza com estes pontos e abre a página — sem mandar coordenada para
servidor nenhum.
"""

from __future__ import annotations

import json
import time

import httpx

from . import DATA, USER_AGENT

SAIDA = DATA / "centros.json"
CONSULTA = """
SELECT ?ibge ?coord WHERE {
  ?item wdt:P1585 ?ibge .
  ?item wdt:P625 ?coord .
}
"""


def _parse_ponto(wkt: str) -> tuple[float, float] | None:
    """`Point(-46.6333 -23.5505)` -> (lat, lon)."""
    try:
        dentro = wkt[wkt.index("(") + 1 : wkt.index(")")]
        lon_txt, lat_txt = dentro.split()
        return float(lat_txt), float(lon_txt)
    except ValueError, IndexError:
        return None


def coletar() -> dict:
    inicio = time.time()
    resposta = httpx.get(
        "https://query.wikidata.org/sparql",
        params={"query": CONSULTA, "format": "json"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        timeout=180.0,
    )
    resposta.raise_for_status()
    linhas = resposta.json()["results"]["bindings"]

    centros: dict[str, list[float]] = {}
    for linha in linhas:
        codigo = str(linha["ibge"]["value"]).strip()
        ponto = _parse_ponto(linha["coord"]["value"])
        if not ponto or len(codigo) != 7 or not codigo.isdigit():
            continue
        # Alguns itens têm mais de um valor; o primeiro vence.
        centros.setdefault(codigo, [round(ponto[0], 5), round(ponto[1], 5)])

    SAIDA.write_text(json.dumps(centros, ensure_ascii=False, separators=(",", ":")) + "\n")
    return {
        "municipios": len(centros),
        "linhas": len(linhas),
        "bytes": SAIDA.stat().st_size,
        "segundos": round(time.time() - inicio, 1),
    }
