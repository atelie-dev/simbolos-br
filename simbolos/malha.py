"""Malha municipal do IBGE fatiada em células, para point-in-polygon no cliente.

O botão "onde estou" precisa saber em qual município o ponto caiu, não qual sede
está mais perto. Baixar 3,4 MB de GeoJSON para isso seria absurdo, então a malha
é cortada em células de 1°: o cliente calcula a célula do ponto, busca um arquivo
pequeno e testa o polígono ali dentro.

Formato de cada célula: ``{"t": [[codigo, [anel, ...]], ...]}``, onde cada anel é
uma lista de ``[lon, lat]``. Vários anéis no mesmo item = MultiPolygon ou furo;
o teste par-ímpar trata os dois.
"""

from __future__ import annotations

import json
import math
import shutil
from collections import defaultdict

import httpx

from . import DATA, USER_AGENT

URL = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
PARAMS = {
    "formato": "application/vnd.geo+json",
    "qualidade": "minima",
    "intrarregiao": "municipio",
}
CACHE = DATA / "_cache" / "malha-ibge.json"
DESTINO = DATA.parent / "site" / "public" / "api" / "v1" / "malha"
GRAU = 1
CASAS = 3  # ~110 m: sobra para decidir município, corta muito byte


def baixar() -> dict:
    """GeoJSON da malha, com cache em disco (gitignored)."""
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    resposta = httpx.get(URL, params=PARAMS, headers={"User-Agent": USER_AGENT}, timeout=300)
    resposta.raise_for_status()
    dados = resposta.json()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(dados))
    return dados


def _aneis(geometria: dict) -> list[list[list[float]]]:
    tipo = geometria.get("type")
    coords = geometria.get("coordinates") or []
    if tipo == "Polygon":
        return coords
    if tipo == "MultiPolygon":
        return [anel for poligono in coords for anel in poligono]
    return []


def _limpar(anel: list[list[float]]) -> list[list[float]]:
    """Arredonda, remove repetidos seguidos e fecha o anel."""
    saida: list[list[float]] = []
    for lon, lat in anel:
        ponto = [round(lon, CASAS), round(lat, CASAS)]
        if not saida or saida[-1] != ponto:
            saida.append(ponto)
    if len(saida) > 2 and saida[0] != saida[-1]:
        saida.append(saida[0])
    return saida


def _celulas(lats: list[float], lons: list[float], grau: int) -> list[tuple[int, int]]:
    """Células que a caixa envolvente toca (sem recortar o polígono)."""
    i0, i1 = math.floor(min(lats) / grau), math.floor(max(lats) / grau)
    j0, j1 = math.floor(min(lons) / grau), math.floor(max(lons) / grau)
    return [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]


def fatiar(grau: int = GRAU) -> dict:
    dados = baixar()
    municipios = json.loads((DATA / "municipios.json").read_text())
    slugs = {m["codigo"]: m["slug"] for m in municipios}
    celulas: dict[tuple[int, int], list] = defaultdict(list)

    for feature in dados["features"]:
        codigo = str(feature["properties"].get("codarea") or "").strip()
        if codigo not in slugs:
            continue
        aneis = [_limpar(a) for a in _aneis(feature["geometry"])]
        aneis = [a for a in aneis if len(a) >= 4]
        if not aneis:
            continue
        lats = [p[1] for a in aneis for p in a]
        lons = [p[0] for a in aneis for p in a]
        for celula in _celulas(lats, lons, grau):
            # slug junto do código: o cliente navega sem baixar outro arquivo
            celulas[celula].append([codigo, slugs[codigo], aneis])

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True)

    total = 0
    maior = 0
    for (i, j), itens in celulas.items():
        conteudo = json.dumps({"t": itens}, ensure_ascii=False, separators=(",", ":"))
        arquivo = DESTINO / f"{i}_{j}.json"
        arquivo.write_text(conteudo + "\n")
        tamanho = arquivo.stat().st_size
        total += tamanho
        maior = max(maior, tamanho)

    return {
        "celulas": len(celulas),
        "bytes": total,
        "maior_kb": round(maior / 1024, 1),
        "media_kb": round(total / max(len(celulas), 1) / 1024, 1),
    }
