"""Coleta no site da AAM — Associação Amazonense de Municípios.

Uma página por município, e a imagem do símbolo em
`/wp-content/uploads/aam-municipios/{slug}/{hash}.png`. A listagem
(`/municipios/`) já traz, para cada um dos 62 municípios, o slug, o nome e a
imagem — então uma requisição resolve o índice inteiro.

O tipo não é confiado ao `alt` ("Bandeira de X"): o portão de visão decide, como
em qualquer outra fonte. O que vem daqui entra `pendente` e sem licença
afirmada, porque o símbolo é do município, não da associação.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from . import DATA, publicacao, rede, visao

LISTA = "https://aam.org.br/municipios/"
CATALOGO = DATA / "_catalogo" / "catalogo.json"
MUNICIPIOS = DATA / "municipios.json"

# O card de cada município vem com atributos quebrados em várias linhas. O
# `data-select-municipio` existe só no mapa, não no card: a âncora é a classe.
_CARD = re.compile(
    r'class="aam-municipio-card"(?P<meio>.*?)'
    r'src="(?P<img>https://aam\.org\.br/wp-content/uploads/aam-municipios/[^"]+\.png)"',
    re.DOTALL,
)
_SLUG = re.compile(r'href="https://aam\.org\.br/([^/"]+)/"')
_NOME = re.compile(r'data-nome="([^"]+)"')


def itens(texto: str | None = None) -> list[dict]:
    """Os 62 municípios da listagem, com slug, nome e URL da imagem."""
    html = texto if texto is not None else rede.requisitar(LISTA, tentativas=3).text
    saida = []
    for achado in _CARD.finditer(html):
        meio = achado.group("meio")
        slug = _SLUG.search(meio)
        nome = _NOME.search(meio)
        if not slug:
            continue
        saida.append(
            {
                "slug": slug.group(1),
                "municipio": nome.group(1) if nome else "",
                "url": achado.group("img"),
                "pagina": f"https://aam.org.br/{slug.group(1)}/",
            }
        )
    return saida


def _visao(conteudo: bytes, mime: str, contexto: str) -> dict:
    ext = publicacao.EXT_POR_MIME.get(mime, "png")
    with tempfile.TemporaryDirectory(prefix="simbolos-aam-") as tmp:
        arquivo = Path(tmp) / f"candidato.{ext}"
        arquivo.write_bytes(conteudo)
        return visao.verificar_decisao(str(arquivo), contexto=contexto)


def coletar(*, limite: int = 0, forcar: bool = False) -> dict:
    """Baixa, classifica e põe no catálogo o que a AAM publica."""
    catalogo: dict = json.loads(CATALOGO.read_text())
    municipios = json.loads(MUNICIPIOS.read_text())
    por_slug = {m["slug"]: m for m in municipios if m["uf"] == "AM"}

    encontrados = itens()
    if limite:
        encontrados = encontrados[:limite]

    resumo = {
        "lidos": len(encontrados),
        "sem_municipio": 0,
        "importados": 0,
        "rejeitados": 0,
        "ja_tinha": 0,
        "falhas": 0,
        "bytes": 0,
        "visao_usd": 0.0,
    }

    for achado in encontrados:
        base = por_slug.get(achado["slug"])
        if base is None:
            resumo["sem_municipio"] += 1
            continue
        codigo = base["codigo"]
        item = catalogo.get(codigo) or {
            "codigo_ibge": codigo,
            "uf": "AM",
            "municipio": base["nome"],
        }

        try:
            resposta = rede.requisitar(achado["url"], tentativas=3)
            resposta.raise_for_status()
            mime = (resposta.headers.get("content-type") or "").split(";")[0].strip()
            if not mime.startswith("image/"):
                resumo["falhas"] += 1
                continue
            conteudo = resposta.content
        except Exception:  # noqa: BLE001
            resumo["falhas"] += 1
            continue

        decisao = _visao(
            conteudo,
            mime,
            f"Candidato a símbolo do município de {base['nome']}/AM, "
            "extraído do site da associação de municípios.",
        )
        custo = (decisao.get("uso") or {}).get("custo")
        if custo:
            resumo["visao_usd"] += float(custo)

        tipo = decisao.get("tipo")
        if tipo not in ("brasao", "bandeira"):
            resumo["rejeitados"] += 1
            continue
        if not decisao.get("aceito"):
            resumo["rejeitados"] += 1
            continue

        existente = item.get(tipo)
        if existente and not existente.get("rejeitado") and not forcar:
            resumo["ja_tinha"] += 1
            continue

        sinais = visao.sinais(conteudo)
        arquivo = publicacao.guardar_fonte(publicacao.FONTES, codigo, tipo, mime, conteudo)
        item[tipo] = {
            "url": achado["url"],
            "pagina": achado["pagina"],
            "mime": mime,
            "largura": sinais.get("largura"),
            "altura": sinais.get("altura"),
            "bytes": len(conteudo),
            "licenca": "NOASSERTION",
            "balde": "pendente",
            "autor": None,
            "fonte": "aam",
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
        catalogo[codigo] = item
        resumo["importados"] += 1
        resumo["bytes"] += len(conteudo)

    tmp = CATALOGO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(CATALOGO)
    resumo["no_catalogo"] = len(catalogo)
    return resumo
