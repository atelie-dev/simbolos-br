"""Completa a lacuna de um tipo por categoria do Commons, sem refazer o catálogo.

Duas limitações do fluxo antigo motivam este módulo:

1. O `simbolos commons` varre **só** categoria de brasão. Bandeira vinha apenas
   do Wikidata (P41), e prefeitura que não declarou P41 fica sem bandeira mesmo
   com o arquivo publicado na categoria do estado.
2. O `simbolos triar` **reconstrói** o catálogo a partir dos candidatos, o que
   apagaria os imports do crawl oficial e da AAM, que não estão em jsonl.

Aqui a escrita é aditiva: mexe apenas no tipo que falta, e o portão de visão
decide o que entra — o nome do arquivo e a categoria dão a pista, nunca o veredito.
"""

from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from pathlib import Path

from . import DATA, NOMES_UF_COMMONS, catalogo, commons, nomes, publicacao, rede, triagem, visao
from .modelos import Candidato

CATALOGO = DATA / "_catalogo" / "catalogo.json"
FONTES = publicacao.FONTES
TIPOS = ("brasao", "bandeira")

CATEGORIAS = {
    "brasao": (
        "Coats of arms of municipalities of {uf}",
        "SVG coats of arms of municipalities of {uf}",
    ),
    "bandeira": (
        "Flags of municipalities of {uf}",
        "SVG flags of municipalities of {uf}",
    ),
}


def _municipios(uf: str) -> list[dict]:
    return catalogo.carregar(uf)


def candidatos(
    uf: str,
    tipos: tuple[str, ...],
    existentes: dict,
    *,
    forcar: bool = False,
) -> tuple[dict[tuple[str, str], list[Candidato]], list[dict]]:
    """Pares (código, tipo) sem arquivo no catálogo, com os candidatos do Commons."""
    nome_uf = NOMES_UF_COMMONS[uf]
    municipios = _municipios(uf)
    por_chave: dict[tuple[str, str], list[Candidato]] = defaultdict(list)
    sem_casamento: list[dict] = []

    for tipo in tipos:
        for molde in CATEGORIAS[tipo]:
            categoria = molde.format(uf=nome_uf)
            try:
                membros = commons.membros_categoria(categoria)
            except RuntimeError as exc:
                sem_casamento.append({"categoria": categoria, "erro": str(exc)[:120]})
                continue
            if not membros:
                continue
            infos = commons.imageinfo(membros)
            for titulo in membros:
                info = infos.get(commons.chave(titulo))
                if not info:
                    continue
                arquivo = titulo.removeprefix("File:")
                if nomes.parece_ruido(arquivo):
                    continue
                municipio, motivo = nomes.casar_municipio(arquivo, municipios, uf)
                if not municipio:
                    sem_casamento.append({"categoria": categoria, "arquivo": arquivo})
                    continue
                # O nome do arquivo pode declarar o tipo; quando declara, ele
                # vence a categoria — o portão confirma depois.
                declarado = nomes.classificar_tipo(arquivo)
                alvo = declarado if declarado in TIPOS else tipo
                chave = (municipio["codigo"], alvo)
                if alvo in (existentes.get(municipio["codigo"]) or {}) and not forcar:
                    continue
                cand = commons.candidato(
                    codigo=municipio["codigo"],
                    uf=uf,
                    municipio=municipio["nome"],
                    tipo=alvo,
                    info=info,
                    metodo="commons-categoria",
                    evidencia={
                        "categoria": categoria.removeprefix("Category:"),
                        "arquivo": titulo,
                        "casamento": motivo,
                    },
                )
                cand.avisos = [] if declarado == alvo else ["tipo_presumido_pela_categoria"]
                por_chave[chave].append(cand)

    return por_chave, sem_casamento


def _decisao(conteudo: bytes, mime: str, contexto: str) -> dict:
    ext = publicacao.EXT_POR_MIME.get((mime or "").lower(), "bin")
    with tempfile.TemporaryDirectory(prefix="simbolos-completar-") as tmp:
        arquivo = Path(tmp) / f"candidato.{ext}"
        arquivo.write_bytes(conteudo)
        return visao.verificar_decisao(str(arquivo), contexto=contexto)


def aplicar(
    uf: str,
    *,
    tipos: tuple[str, ...] = TIPOS,
    forcar: bool = False,
    seco: bool = False,
    limite: int = 0,
) -> dict:
    """Preenche o que falta no catálogo. `seco` mostra sem baixar nem gravar."""
    cat: dict = json.loads(CATALOGO.read_text())
    por_chave, sem_casamento = candidatos(uf, tipos, cat, forcar=forcar)
    chaves = sorted(por_chave)
    if limite:
        chaves = chaves[:limite]

    resumo = {
        "uf": uf,
        "categorias": len(por_chave),
        "municipios": len({codigo for codigo, _ in chaves}),
        "aceitos": 0,
        "rejeitados": 0,
        "falhas": 0,
        "bytes": 0,
        "visao_usd": 0.0,
        "por_tipo": defaultdict(int),
        "sem_casamento": len(sem_casamento),
        "detalhe": [],
    }

    for codigo, tipo in chaves:
        melhor = triagem.escolher(por_chave[(codigo, tipo)])
        if seco:
            resumo["detalhe"].append(
                {
                    "codigo": codigo,
                    "municipio": melhor.municipio,
                    "tipo": tipo,
                    "url": melhor.url,
                    "largura": melhor.largura,
                    "altura": melhor.altura,
                }
            )
            continue
        try:
            conteudo = rede.requisitar(melhor.url, tentativas=3).content
        except Exception as exc:  # noqa: BLE001
            resumo["falhas"] += 1
            resumo["detalhe"].append({"codigo": codigo, "erro": str(exc)[:120]})
            continue

        decisao = _decisao(
            conteudo,
            melhor.mime or "",
            f"Candidato a {tipo} do município de {melhor.municipio}/{uf}, "
            "arquivo do Wikimedia Commons.",
        )
        custo = (decisao.get("uso") or {}).get("custo")
        if custo:
            resumo["visao_usd"] += float(custo)

        if decisao.get("tipo") != tipo or not decisao.get("aceito"):
            resumo["rejeitados"] += 1
            resumo["detalhe"].append(
                {
                    "codigo": codigo,
                    "municipio": melhor.municipio,
                    "tipo": tipo,
                    "motivo": decisao.get("rejeitar_motivo") or decisao.get("tipo"),
                }
            )
            continue

        arquivo = publicacao.guardar_fonte(FONTES, codigo, tipo, melhor.mime or "", conteudo)
        item = cat.setdefault(
            codigo,
            {"codigo_ibge": codigo, "uf": uf, "municipio": melhor.municipio},
        )
        item[tipo] = {
            "url": melhor.url,
            "mime": melhor.mime,
            "largura": melhor.largura,
            "altura": melhor.altura,
            "bytes": melhor.bytes,
            "licenca": melhor.licenca.spdx,
            "balde": melhor.licenca.balde,
            "autor": melhor.autor,
            "fonte": "commons-categoria",
            "precisa_visao": False,
            "visao": {
                "motor": "systemone",
                "perguntas_versao": decisao.get("perguntas_versao"),
                "confianca": decisao.get("confianca"),
                "fundo_limpo": decisao.get("fundo_limpo"),
                "marca_dagua": decisao.get("marca_dagua"),
                "precisa_recorte": decisao.get("precisa_recorte"),
                "rejeitar_motivo": decisao.get("rejeitar_motivo"),
            },
            "arquivo": publicacao._relativo(arquivo),
        }
        resumo["aceitos"] += 1
        resumo["por_tipo"][tipo] += 1
        resumo["bytes"] += len(conteudo)
        resumo["detalhe"].append({"codigo": codigo, "municipio": melhor.municipio, "tipo": tipo})

    if not seco and resumo["aceitos"]:
        tmp = CATALOGO.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")
        tmp.replace(CATALOGO)

    resumo["por_tipo"] = dict(resumo["por_tipo"])
    resumo["no_catalogo"] = len(cat)
    resumo["sem_casamento_exemplos"] = sem_casamento[:8]
    return resumo
