"""Índice estático que o site consome: busca, cobertura e números da landing.

Nada de backend: o site carrega um JSON e filtra no cliente. Chaves curtas porque
o arquivo é baixado por todo visitante — 5.571 municípios com nomes longos.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from PIL import Image

from . import DATA

CATALOGO = DATA.parent / "dist" / "catalogo.json"
DESTINO = DATA.parent / "site" / "public" / "api" / "v1"
DESTINO_BUILD = DATA.parent / "site" / "src" / "data"

TIPOS = ("brasao", "bandeira")

# Capitais do IBGE: entram como destaques da landing quando têm brasão e bandeira
# em SVG. São reconhecíveis e dão variedade geográfica sem curadoria manual.
CAPITAIS = frozenset(
    {
        "1100205",
        "1200401",
        "1302603",
        "1400100",
        "1501402",
        "1600303",
        "1721000",
        "2111300",
        "2211001",
        "2304400",
        "2408102",
        "2507507",
        "2611606",
        "2704302",
        "2800308",
        "2927408",
        "3106200",
        "3205309",
        "3304557",
        "3550308",
        "4106902",
        "4205407",
        "4314902",
        "5002704",
        "5103403",
        "5208707",
        "5300108",
    }
)


def _destaques(itens: dict[tuple[str, str], dict]) -> list[dict]:
    """Municípios que servem de amostra na landing: brasão e bandeira em SVG."""
    amostra = []
    for codigo in CAPITAIS:
        brasao = itens.get((codigo, "brasao"))
        bandeira = itens.get((codigo, "bandeira"))
        if not (brasao and bandeira):
            continue
        if "svg" not in (brasao.get("rendicoes") or {}):
            continue
        if "svg" not in (bandeira.get("rendicoes") or {}):
            continue
        amostra.append({"c": codigo, "n": brasao["municipio"], "u": brasao["uf"]})
    return sorted(amostra, key=lambda x: x["n"])


def _arte(codigo: str, tipo: str) -> dict | None:
    """Tamanho real da arte dentro do canvas de 512, não o canvas.

    Um brasão de 60 px num PNG 512 continua sendo 60 px: é isso que decide se
    serve para imprimir. O tier não pode mentir sobre isso.
    """
    arq = DATA.parent / "dist" / "embed" / "v1" / tipo / f"{codigo}.png"
    try:
        with Image.open(arq) as imagem:
            caixa = imagem.convert("RGBA").getchannel("A").getbbox()
    except OSError, ValueError:
        return None
    if not caixa:
        return {"l": 0, "a": 0}
    return {"l": caixa[2] - caixa[0], "a": caixa[3] - caixa[1]}


def _tier(item: dict | None, arte: dict | None) -> int:
    """T0 ausente · T1 raster pequeno · T2 raster grande · T3 vetorial."""
    if not item:
        return 0
    if "svg" in (item.get("rendicoes") or {}):
        return 3
    lado = max((arte or {}).get("l", 0), (arte or {}).get("a", 0))
    return 2 if lado >= 400 else 1


def _publicados(catalogo: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["codigo_ibge"], r["tipo"]): r for r in catalogo if r.get("estado") == "publicado"}


def _linha(entrada: dict, itens: dict, tiers: dict[str, int], regiao: dict[str, str]) -> dict:
    codigo = entrada["codigo"]
    return {
        "c": codigo,
        "n": entrada["nome"],
        "u": entrada["uf"],
        "e": regiao.get(entrada["uf"], ""),
        "s": entrada["slug"],
        "b": int((codigo, "brasao") in itens),
        "f": int((codigo, "bandeira") in itens),
        "t": tiers.get(codigo, 0),
    }


def gerar(destino: Path = DESTINO) -> dict:
    catalogo = json.loads(CATALOGO.read_text())
    municipios = json.loads((DATA / "municipios.json").read_text())
    estados = json.loads((DATA / "estados.json").read_text())
    regiao = {e["uf"]: e.get("regiao", "") for e in estados}
    itens = _publicados(catalogo)

    artes = {chave: _arte(chave[0], chave[1]) for chave in itens}
    tiers = {
        codigo: max(_tier(itens.get((codigo, t)), artes.get((codigo, t))) for t in TIPOS)
        for codigo in {c for c, _ in itens}
    }

    indice = [_linha(e, itens, tiers, regiao) for e in sorted(estados, key=lambda x: x["uf"])]
    indice += [_linha(m, itens, tiers, regiao) for m in municipios]

    por_uf = []
    for estado in sorted(estados, key=lambda x: x["uf"]):
        uf = estado["uf"]
        municipios_uf = [m for m in municipios if m["uf"] == uf]
        contagem = {0: 0, 1: 0, 2: 0, 3: 0}
        for m in municipios_uf:
            contagem[tiers.get(m["codigo"], 0)] += 1
        por_uf.append(
            {
                "uf": uf,
                "nome": estado["nome"],
                "total": len(municipios_uf),
                "brasao": sum(1 for m in municipios_uf if (m["codigo"], "brasao") in itens),
                "bandeira": sum(1 for m in municipios_uf if (m["codigo"], "bandeira") in itens),
                "vetorial": contagem[3],
                "t1": contagem[1] + contagem[2],
                "t2": contagem[2],
                "t3": contagem[3],
                "sem": contagem[0],
            }
        )

    hoje = date.today()
    cobertos = sum(1 for m in municipios if tiers.get(m["codigo"], 0) > 0)
    resumo = {
        "versao": f"v{hoje.year}.{hoje.month:02d}",
        "gerado_em": hoje.isoformat(),
        "municipios": len(municipios),
        "estados": len(estados),
        "publicados": len(itens),
        "municipios_cobertos": cobertos,
        "cobertura_pct": round(100 * cobertos / len(municipios), 1),
        "municipios_com_brasao": sum(1 for m in municipios if (m["codigo"], "brasao") in itens),
        "municipios_com_bandeira": sum(1 for m in municipios if (m["codigo"], "bandeira") in itens),
        "vetoriais": sum(1 for r in itens.values() if "svg" in (r.get("rendicoes") or {})),
        "por_uf": por_uf,
    }

    destino.mkdir(parents=True, exist_ok=True)
    (destino / "municipios.json").write_text(
        json.dumps(indice, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    (destino / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1) + "\n")

    # Detalhe por item: só o que a página do município mostra. Fica em `src/`
    # (build-only) para não ser baixado por visitante.
    itens_build = [
        {
            "codigo_ibge": r["codigo_ibge"],
            "tipo": r["tipo"],
            "licenca": r.get("licenca"),
            "balde": r.get("balde"),
            "autor": r.get("autor"),
            "origem": r.get("origem"),
            "formato_origem": r.get("formato_origem"),
            "sha256_origem": r.get("sha256_origem"),
            "rendicoes": r.get("rendicoes") or {},
            "arte": artes.get((r["codigo_ibge"], r["tipo"])),
        }
        for r in sorted(itens.values(), key=lambda x: (x["codigo_ibge"], x["tipo"]))
    ]
    DESTINO_BUILD.mkdir(parents=True, exist_ok=True)
    (DESTINO_BUILD / "itens.json").write_text(
        json.dumps(itens_build, ensure_ascii=False, separators=(",", ":")) + "\n"
    )

    destaques = _destaques(itens)
    (DESTINO_BUILD / "destaques.json").write_text(
        json.dumps(destaques, ensure_ascii=False, separators=(",", ":")) + "\n"
    )

    # Pontos de referência para o "onde estou": só o necessário para o cliente
    # achar o município mais próximo e navegar. Carregado apenas no clique.
    centros_brutos = {}
    arquivo_centros = DATA / "centros.json"
    if arquivo_centros.exists():
        centros_brutos = json.loads(arquivo_centros.read_text())
    slugs = {m["codigo"]: m["slug"] for m in municipios}
    centros = [
        [lat, lon, codigo, slugs[codigo]]
        for codigo, (lat, lon) in sorted(centros_brutos.items())
        if codigo in slugs
    ]
    (destino / "centros.json").write_text(
        json.dumps(centros, ensure_ascii=False, separators=(",", ":")) + "\n"
    )

    return {
        "entradas": len(indice),
        "bytes_indice": (destino / "municipios.json").stat().st_size,
        "bytes_resumo": (destino / "resumo.json").stat().st_size,
        "bytes_itens": (DESTINO_BUILD / "itens.json").stat().st_size,
        "resumo": resumo,
    }
