"""Importa para o catálogo os símbolos achados no crawl oficial.

O crawl guarda URL e município; não guarda o arquivo. Aqui o arquivo é baixado
uma vez, com a mesma polidez de sempre, o portão de visão decide **o que é** e
**de quem é**, e o original vai para `data/fontes` — que é de onde a publicação
renderiza, sem rede.

Nada entra como `livre`: símbolo de site de prefeitura não traz licença, então
entra `pendente` e fica fora dos pacotes que se dizem livres.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote

from . import DATA, publicacao, rede, visao

COLETA = DATA / "_coleta" / "leis.jsonl"
CATALOGO = DATA / "_catalogo" / "catalogo.json"

LICENCA = "NOASSERTION"
TIPOS = ("brasao", "bandeira")

_BRASAO = re.compile(r"bras[aã]o|escudo|armas|brasa", re.IGNORECASE)
_BANDEIRA = re.compile(r"bandeira|flag|pavilh", re.IGNORECASE)


def palpite(url: str) -> str | None:
    """O que o nome do arquivo sugere — só um palpite, nunca a decisão."""
    nome = unquote(url)
    if _BRASAO.search(nome):
        return "brasao"
    if _BANDEIRA.search(nome):
        return "bandeira"
    return None


def achados(*, uf: str | None = None) -> list[dict]:
    """Símbolos do crawl, deduplicados por URL.

    O mesmo arquivo aparece em várias páginas do mesmo município (/simbolos,
    /historia, /a-cidade). Sem deduplicar, o acervo ganharia centenas de itens
    que são o mesmo arquivo.
    """
    ultimo: dict[str, dict] = {}
    for linha in COLETA.read_text().splitlines():
        if not linha.strip():
            continue
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError:
            continue
        ultimo[registro["codigo"]] = registro

    por_url: dict[str, dict] = {}
    for registro in ultimo.values():
        if uf and registro.get("uf") != uf:
            continue
        for pagina in registro.get("paginas") or []:
            url = pagina.get("simbolo")
            if not url or url in por_url:
                continue
            por_url[url] = {
                "url": url,
                "pagina": pagina.get("url"),
                "codigo": registro["codigo"],
                "uf": registro["uf"],
                "municipio": registro["municipio"],
                "tipo_palpite": pagina.get("simbolo_tipo") or palpite(url),
                "confianca_extracao": pagina.get("simbolo_confianca"),
            }
    return sorted(por_url.values(), key=lambda a: (a["uf"], a["codigo"], a["url"]))


def rejeitar(codigo: str, tipo: str, motivo: str, *, por: str = "revisao visual") -> dict:
    """Marca um item importado como rejeitado — sem apagar nada.

    O acervo não apaga: registra. O sidecar passa a `estado: rejeitado` (que
    `indice_meta` já ignora), e o catálogo guarda o motivo. A imagem original
    fica em `data/fontes` como evidência do que foi recusado e por quê.
    """
    catalogo: dict = json.loads(CATALOGO.read_text())
    item = catalogo.get(codigo)
    if not item or not item.get(tipo):
        raise KeyError(f"{codigo}/{tipo} nao esta no catalogo")
    marcado = {"motivo": motivo, "em": publicacao.agora(), "por": por}
    item[tipo]["rejeitado"] = marcado

    sidecar = publicacao.META / tipo / f"{codigo}.json"
    if sidecar.exists():
        registro = json.loads(sidecar.read_text())
        registro["estado"] = "rejeitado"
        registro["rejeitado"] = marcado
        tmp = sidecar.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n")
        tmp.replace(sidecar)

    tmp = CATALOGO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(CATALOGO)
    return {"codigo": codigo, "tipo": tipo, **marcado}


def chaves_rejeitadas() -> list[str]:
    """Chaves do CDN dos itens rejeitados: as três renditions e o sidecar."""
    catalogo: dict = json.loads(CATALOGO.read_text())
    chaves: list[str] = []
    for item in catalogo.values():
        for tipo in TIPOS:
            if not (item.get(tipo) or {}).get("rejeitado"):
                continue
            codigo = item["codigo_ibge"]
            chaves += [f"embed/v1/{tipo}/{codigo}.{ext}" for ext in ("svg", "png", "jpg")]
            chaves.append(f"meta/v1/{tipo}/{codigo}.json")
    return chaves


def _visao(conteudo: bytes, mime: str, contexto: str) -> dict:
    """Roda o portão de visão sobre os bytes, sem baixar de novo.

    `visao.carregar` aceita caminho local: o arquivo vai para um temporário só
    durante a chamada. O original de verdade fica em `data/fontes`.
    """
    ext = publicacao.EXT_POR_MIME.get(mime, "jpg")
    with tempfile.TemporaryDirectory(prefix="simbolos-visao-") as tmp:
        arquivo = Path(tmp) / f"candidato.{ext}"
        arquivo.write_bytes(conteudo)
        return visao.verificar_decisao(str(arquivo), contexto=contexto)


def _contexto(achado: dict) -> str:
    return (
        f"Candidato a símbolo do município de {achado['municipio']}/{achado['uf']}, "
        "extraído do site da prefeitura."
    )


def importar(*, uf: str | None = None, limite: int = 0, sem_visao: bool = False) -> dict:
    """Baixa, classifica e põe no catálogo. Não publica: quem renderiza é `publicar`."""
    catalogo: dict = json.loads(CATALOGO.read_text())
    itens = achados(uf=uf)
    if limite:
        itens = itens[:limite]

    resumo = {
        "achados": len(itens),
        "importados": 0,
        "rejeitados": 0,
        "ja_tinha": 0,
        "falhas": 0,
        "sem_tipo": 0,
        "visao_usd": 0.0,
        "bytes": 0,
        "motivos": {},
    }
    cache: dict[str, tuple[bytes, str] | None] = {}

    def motivo(nome: str) -> None:
        resumo["motivos"][nome] = resumo["motivos"].get(nome, 0) + 1

    for achado in itens:
        url = achado["url"]
        if url not in cache:
            try:
                resposta = rede.requisitar(url, tentativas=3)
                resposta.raise_for_status()
                mime = (resposta.headers.get("content-type") or "").split(";")[0].strip()
                cache[url] = (resposta.content, mime) if mime.startswith("image/") else None
            except Exception:  # noqa: BLE001
                cache[url] = None

        obtido = cache[url]
        if obtido is None:
            resumo["falhas"] += 1
            motivo("download")
            continue
        conteudo, mime = obtido

        decisao: dict = {}
        if sem_visao:
            tipo = achado["tipo_palpite"]
            aceito, confianca = tipo in TIPOS, None
        else:
            decisao = _visao(conteudo, mime, _contexto(achado))
            custo = (decisao.get("uso") or {}).get("custo")
            if custo:
                resumo["visao_usd"] += float(custo)
            tipo = decisao.get("tipo")
            aceito = bool(decisao.get("aceito"))
            confianca = decisao.get("confianca")

        if not tipo:
            resumo["sem_tipo"] += 1
            motivo("sem_tipo")
            continue
        if not aceito:
            resumo["rejeitados"] += 1
            motivo("visao_rejeitou")
            continue

        item = catalogo.get(achado["codigo"]) or {
            "codigo_ibge": achado["codigo"],
            "uf": achado["uf"],
            "municipio": achado["municipio"],
        }
        existente = item.get(tipo)
        if existente and (existente.get("rejeitado") or existente.get("fonte") != "govbr"):
            # Rejeição é decisão registrada: reimportar não a desfaz.
            resumo["ja_tinha"] += 1
            motivo("ja_tinha")
            continue

        sinais = visao.sinais(conteudo)
        arquivo = publicacao.guardar_fonte(
            publicacao.FONTES, achado["codigo"], tipo, mime, conteudo
        )
        item[tipo] = {
            "url": url,
            "pagina": achado["pagina"],
            "mime": mime,
            "largura": sinais.get("largura"),
            "altura": sinais.get("altura"),
            "bytes": len(conteudo),
            "licenca": LICENCA,
            "balde": "pendente",
            "autor": None,
            "fonte": "govbr",
            "precisa_visao": False,
            "visao": {
                "motor": "sem-visao" if sem_visao else "systemone",
                "perguntas_versao": decisao.get("perguntas_versao"),
                "confianca": confianca,
                "confianca_extracao": achado["confianca_extracao"],
                "fundo_limpo": decisao.get("fundo_limpo"),
                "marca_dagua": decisao.get("marca_dagua"),
                "precisa_recorte": decisao.get("precisa_recorte"),
                "rejeitar_motivo": decisao.get("rejeitar_motivo"),
            },
            "arquivo": publicacao._relativo(arquivo),
        }
        catalogo[achado["codigo"]] = item
        resumo["importados"] += 1
        resumo["bytes"] += len(conteudo)

    tmp = CATALOGO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(catalogo, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(CATALOGO)
    resumo["no_catalogo"] = len(catalogo)
    return resumo
