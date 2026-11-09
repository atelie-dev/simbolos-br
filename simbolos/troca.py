"""Troca a origem de um item já publicado por uma versão melhor.

Existe porque qualidade de arquivo não é monotônica: o Commons costuma ter a
versão antiga de um brasão em 317 px, e a câmara do município publica a mesma
arte em 799 px. O acervo não deve ficar preso à primeira cópia que apareceu.

A troca é explícita e registra o que havia antes: o item guarda `anterior` com
URL, licença, fonte e medidas da origem substituída. O sidecar e as rendições
são apagados para o `publicar` refazer do zero — procedência e verificação
descrevem um arquivo, e o arquivo mudou.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import DATA, publicacao, rede, visao
from .modelos import balde_de

CATALOGO = DATA / "_catalogo" / "catalogo.json"
RAIZ = DATA.parent / "dist"
FONTES = publicacao.FONTES
TIPOS = ("brasao", "bandeira")


def _decisao(conteudo: bytes, mime: str, contexto: str) -> dict:
    ext = publicacao.EXT_POR_MIME.get((mime or "").lower(), "bin")
    with tempfile.TemporaryDirectory(prefix="simbolos-troca-") as tmp:
        arquivo = Path(tmp) / f"candidato.{ext}"
        arquivo.write_bytes(conteudo)
        return visao.verificar_decisao(str(arquivo), contexto=contexto)


def _limpar(codigo: str, tipo: str) -> list[str]:
    """Remove sidecar e rendições do item: o publicar reconstrói do catálogo."""
    apagados: list[str] = []
    sidecar = publicacao.META / tipo / f"{codigo}.json"
    if sidecar.exists():
        sidecar.unlink()
        apagados.append(str(sidecar))
    for ext in ("png", "jpg", "svg"):
        alvo = RAIZ / "embed" / "v1" / tipo / f"{codigo}.{ext}"
        if alvo.exists():
            alvo.unlink()
            apagados.append(str(alvo))
    return apagados


def _guardar_anterior(item: dict, tipo: str) -> dict | None:
    """Copia a origem atual para `_versoes` antes de sobrescrever.

    `guardar_fonte` grava um arquivo por item/tipo, então a troca apagaria a
    versão antiga. A cópia fica ao lado, nomeada pelo sha256, e o item guarda a
    lista `versoes` — hoje só registro, amanhã acesso público a várias versões.
    """
    dados = item.get(tipo) or {}
    caminho: Path | None = None
    relativo = dados.get("arquivo")
    if relativo:
        candidato = DATA.parent / relativo
        if candidato.exists():
            caminho = candidato
    if caminho is None:
        # Item vindo do Commons não guarda `arquivo` no catálogo: o original foi
        # gravado pelo `publicar` em FONTES/{tipo}/{codigo}.{ext}.
        for achado in sorted((FONTES / tipo).glob(f"{item['codigo_ibge']}.*")):
            if achado.suffix != ".tmp":
                caminho = achado
                break
    if caminho is None:
        return None
    conteudo = caminho.read_bytes()
    resumo = publicacao.sha256(conteudo)[:12]
    destino_dir = FONTES.parent / "_versoes" / tipo
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{item['codigo_ibge']}-{resumo}{caminho.suffix}"
    if not destino.exists():
        destino.write_bytes(conteudo)
    return {
        "tipo": tipo,
        "url": dados.get("url"),
        "licenca": dados.get("licenca"),
        "fonte": dados.get("fonte"),
        "largura": dados.get("largura"),
        "altura": dados.get("altura"),
        "bytes": dados.get("bytes"),
        "sha256": publicacao.sha256(conteudo),
        "arquivo": publicacao._relativo(destino),
    }


def trocar(
    codigo: str,
    tipo: str,
    url: str,
    *,
    licenca: str = "NOASSERTION",
    autor: str | None = None,
    fonte: str = "oficial",
    seco: bool = False,
) -> dict:
    """Baixa a nova origem, passa pelo portão e substitui o item."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo invalido: {tipo}")
    cat: dict = json.loads(CATALOGO.read_text())
    item = cat.get(codigo)
    if not item:
        raise ValueError(f"codigo fora do catalogo: {codigo}")
    anterior = (item.get(tipo) or {}).copy()
    if not anterior:
        raise ValueError(f"{codigo} nao tem {tipo} no catalogo")

    resposta = rede.requisitar(url, tentativas=3)
    resposta.raise_for_status()
    mime = (resposta.headers.get("content-type") or "").split(";")[0].strip()
    if not mime.startswith("image/"):
        raise ValueError(f"resposta nao e imagem: {mime or 'sem content-type'}")
    conteudo = resposta.content

    decisao = _decisao(
        conteudo,
        mime,
        f"Candidato a {tipo} do município de {item['municipio']}/{item['uf']}, "
        f"extraído de fonte oficial: {url}",
    )
    if decisao.get("tipo") != tipo or not decisao.get("aceito"):
        return {
            "troca": False,
            "motivo": decisao.get("rejeitar_motivo") or f"visao disse {decisao.get('tipo')}",
            "codigo": codigo,
            "tipo": tipo,
            "anterior": anterior.get("url"),
        }

    sinais = visao.sinais(conteudo)
    resumo = {
        "troca": True,
        "codigo": codigo,
        "municipio": item["municipio"],
        "tipo": tipo,
        "de": {
            "url": anterior.get("url"),
            "largura": anterior.get("largura"),
            "altura": anterior.get("altura"),
            "bytes": anterior.get("bytes"),
            "licenca": anterior.get("licenca"),
        },
        "para": {
            "url": url,
            "largura": sinais.get("largura"),
            "altura": sinais.get("altura"),
            "bytes": len(conteudo),
            "licenca": licenca,
        },
        "confianca": decisao.get("confianca"),
        "apagados": [],
    }
    if seco:
        return resumo

    # A versão que sai não pode desaparecer: arquivar ANTES de sobrescrever.
    anterior_arquivado = _guardar_anterior(item, tipo)
    arquivo = publicacao.guardar_fonte(FONTES, codigo, tipo, mime, conteudo)
    versoes = list((item.get(tipo) or {}).get("versoes") or [])
    if anterior_arquivado and not any(
        v.get("sha256") == anterior_arquivado.get("sha256") for v in versoes
    ):
        versoes.append(anterior_arquivado)
    item[tipo] = {
        **anterior,
        "url": url,
        "mime": mime,
        "largura": sinais.get("largura"),
        "altura": sinais.get("altura"),
        "bytes": len(conteudo),
        "licenca": licenca,
        "balde": balde_de(licenca),
        "autor": autor,
        "fonte": fonte,
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
        "versoes": versoes,
    }
    if anterior_arquivado:
        resumo["arquivado"] = anterior_arquivado
    tmp = CATALOGO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(CATALOGO)
    resumo["apagados"] = _limpar(codigo, tipo)
    return resumo
