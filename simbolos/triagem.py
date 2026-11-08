"""Triagem: de milhares de candidatos para um item por município.

Regras de escolha, na ordem:
1. licença melhor (oficial > livre > compartilha > pendente não escolhe se houver outra)
2. vetor antes de raster
3. maior resolução
4. canal mais autoritativo (prefeitura > wikimedia)

A visão não roda em tudo: roda por risco. Wikidata `P94`/`P41` já declara o tipo;
candidato vindo de categoria do Commons (casado por nome) ou de site oficial
(casado por página) é que precisa de confirmação.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .modelos import Candidato

RANK_BALDE = {"oficial": 4, "livre": 3, "compartilha": 2, "pendente": 0}
RANK_FORMATO = {
    "image/svg+xml": 5,
    "image/png": 4,
    "image/jpeg": 3,
    "image/webp": 2,
    "image/gif": 1,
}
RANK_CANAL = {"prefeitura": 4, "estado": 3, "wikimedia": 2, "outro": 1, "acervo-legado": 0}


def chave(c: Candidato) -> tuple:
    """Vetor primeiro, depois licença, depois resolução.

    `pendente` não entra na disputa enquanto houver alternativa (isso é filtro,
    não peso). Entre `livre` e `compartilha`, o vetor ganha: qualidade é o
    produto, e o balde da licença é exibido e filtrado depois.
    """
    return (
        RANK_FORMATO.get(c.mime or "", 0),
        RANK_BALDE.get(c.licenca.balde, 0),
        c.largura or 0,
        RANK_CANAL.get(c.coleta.evidencia.get("canal", "wikimedia"), 2),
        c.bytes or 0,
    )


def escolher(candidatos: list[Candidato]) -> Candidato:
    com_licenca = [c for c in candidatos if c.licenca.balde != "pendente"]
    return max(com_licenca or candidatos, key=chave)


def precisa_visao(c: Candidato) -> bool:
    """Confirmação visual só onde o tipo não é declarado por propriedade."""
    return not (c.coleta.metodo == "wikidata" and not c.avisos)


def montar(caminhos: list[Path]) -> dict:
    por_item: dict[tuple[str, str], list[Candidato]] = defaultdict(list)
    for caminho in caminhos:
        if not caminho.exists():
            continue
        for linha in caminho.read_text().splitlines():
            if not linha.strip():
                continue
            c = Candidato.model_validate_json(linha)
            por_item[(c.codigo_ibge, c.tipo)].append(c)

    catalogo: dict[str, dict] = {}
    for (codigo, tipo), candidatos in por_item.items():
        melhor = escolher(candidatos)
        catalogo.setdefault(
            codigo, {"codigo_ibge": codigo, "uf": melhor.uf, "municipio": melhor.municipio}
        )
        catalogo[codigo][tipo] = {
            "url": melhor.url,
            "mime": melhor.mime,
            "largura": melhor.largura,
            "altura": melhor.altura,
            "bytes": melhor.bytes,
            "licenca": melhor.licenca.spdx,
            "balde": melhor.licenca.balde,
            "autor": melhor.autor,
            "fonte": melhor.coleta.metodo,
            "score": chave(melhor),
            "precisa_visao": precisa_visao(melhor),
            "alternativas": len(candidatos),
        }
    return catalogo


def relatorio(catalogo: dict) -> dict:
    total = len(catalogo)
    brasao = [x for x in catalogo.values() if "brasao" in x]
    bandeira = [x for x in catalogo.values() if "bandeira" in x]
    svg = [x for x in brasao if x["brasao"]["mime"] == "image/svg+xml"]
    gate = [
        x
        for x in catalogo.values()
        for t in ("brasao", "bandeira")
        if t in x and x[t]["precisa_visao"]
    ]
    baldes = Counter(
        x[t]["balde"] for x in catalogo.values() for t in ("brasao", "bandeira") if t in x
    )
    formatos = Counter(
        x[t]["mime"] for x in catalogo.values() for t in ("brasao", "bandeira") if t in x
    )
    multiplos = (
        sum(1 for x in catalogo.values() if "brasao" in x and x["brasao"]["alternativas"] > 1)
        if brasao
        else 0
    )
    return {
        "municipios": total,
        "com_brasao": len(brasao),
        "com_bandeira": len(bandeira),
        "com_os_dois": sum(1 for x in catalogo.values() if "brasao" in x and "bandeira" in x),
        "brasao_svg": len(svg),
        "precisam_visao": len(gate),
        "baldes": dict(baldes),
        "formatos": dict(formatos),
        "com_alternativas": multiplos,
    }
