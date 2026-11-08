"""Coleta no Commons: imageinfo + extmetadata, e membros de categoria."""

from __future__ import annotations

import html
import json
import re
import time
from datetime import date
from pathlib import Path

import httpx

from . import USER_AGENT
from .modelos import Candidato, Coleta, Licenca, balde_de

API = "https://commons.wikimedia.org/w/api.php"
_TAGS = re.compile(r"<[^>]+>")


def _limpar(valor: str | None) -> str | None:
    if not valor:
        return None
    texto = html.unescape(_TAGS.sub("", valor)).strip()
    return " ".join(texto.split()) or None


def _api(params: dict, tentativas: int = 4) -> dict:
    base = {"format": "json", "formatversion": "2", "maxlag": "5"}
    ultimo: Exception | None = None
    for i in range(tentativas):
        try:
            r = httpx.get(
                API,
                params={**base, **params},
                headers={"User-Agent": USER_AGENT},
                timeout=60.0,
            )
            r.raise_for_status()
            dados = r.json()
            if "error" in dados:
                raise RuntimeError(dados["error"].get("info", "erro da API"))
            return dados
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"API do Commons falhou: {params}") from ultimo


def membros_categoria(categoria: str) -> list[str]:
    """Todos os arquivos de uma categoria (paginado)."""
    titulos: list[str] = []
    continuar: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": categoria if categoria.startswith("Category:") else f"Category:{categoria}",
            "cmtype": "file",
            "cmlimit": "500",
        }
        if continuar:
            params["cmcontinue"] = continuar
        dados = _api(params)
        titulos += [p["title"] for p in dados.get("query", {}).get("categorymembers", [])]
        continuar = dados.get("continue", {}).get("cmcontinue")
        if not continuar:
            return titulos
        time.sleep(0.3)


def imageinfo(titulos: list[str]) -> dict[str, dict]:
    """imageinfo em lotes de 50. Devolve {titulo_normalizado: info}."""
    saida: dict[str, dict] = {}
    validos = [t for t in titulos if "://" not in t and t.lower().startswith("file:")]
    for i in range(0, len(validos), 50):
        lote = validos[i : i + 50]
        try:
            dados = _api(
                {
                    "action": "query",
                    "prop": "imageinfo",
                    "titles": "|".join(lote),
                    "iiprop": "url|size|mime|extmetadata",
                    "iiurlwidth": "400",
                }
            )
        except RuntimeError as exc:
            print(f"    lote {i // 50} falhou: {exc}", flush=True)
            continue
        for pagina in dados.get("query", {}).get("pages", []):
            if pagina.get("missing"):
                continue
            info = (pagina.get("imageinfo") or [{}])[0]
            if not info:
                continue
            saida[_chave(pagina["title"])] = {**info, "title": pagina["title"]}
        time.sleep(0.3)
    return saida


def sha1_por_titulo(titulos: list[str]) -> dict[str, dict]:
    """imageinfo com sha1, em lotes de 50. Devolve {chave(titulo): info}.

    Só o sha1 e o url: a conferência de procedência não precisa de extmetadata, e
    pedir menos deixa o lote mais barato.
    """
    saida: dict[str, dict] = {}
    validos = [t for t in titulos if "://" not in t and t.lower().startswith("file:")]
    for i in range(0, len(validos), 50):
        lote = validos[i : i + 50]
        try:
            dados = _api(
                {
                    "action": "query",
                    "prop": "imageinfo",
                    "titles": "|".join(lote),
                    "iiprop": "sha1|url|size|timestamp",
                }
            )
        except RuntimeError as exc:
            print(f"    lote {i // 50} falhou: {exc}", flush=True)
            continue
        for pagina in dados.get("query", {}).get("pages", []):
            if pagina.get("missing"):
                continue
            info = (pagina.get("imageinfo") or [{}])[0]
            if not info:
                continue
            saida[_chave(pagina["title"])] = {**info, "title": pagina["title"]}
        time.sleep(0.3)
    return saida


def titulo_do_sha1(sha1: str) -> str | None:
    """Título atual de um arquivo pela SHA1, ou None se ele não existe mais.

    Serve para separar renomeado de sumido: se o título derivado da URL não
    resolve mas o sha1 está sob outro nome, os bytes continuam lá.
    """
    if not sha1:
        return None
    dados = _api({"action": "query", "list": "allimages", "aisha1": sha1.lower(), "ailimit": "1"})
    achados = dados.get("query", {}).get("allimages") or []
    return achados[0]["title"] if achados else None


def _chave(titulo: str) -> str:
    return titulo.replace("_", " ").strip().lower()


def chave(titulo: str) -> str:
    return _chave(titulo)


def meta(info: dict) -> dict[str, str]:
    em = info.get("extmetadata") or {}
    campos = (
        "LicenseShortName",
        "UsageTerms",
        "AttributionRequired",
        "Copyrighted",
        "Artist",
        "Credit",
        "Restrictions",
        "ImageDescription",
    )
    return {c: _limpar((em.get(c) or {}).get("value")) for c in campos if em.get(c)}


def candidato(
    *,
    codigo: str,
    uf: str,
    municipio: str,
    tipo: str,
    info: dict,
    metodo: str,
    evidencia: dict[str, str],
) -> Candidato:
    em = meta(info)
    licenca_nome = em.get("LicenseShortName") or em.get("UsageTerms")
    balde = balde_de(licenca_nome)
    return Candidato(
        codigo_ibge=codigo,
        uf=uf,
        municipio=municipio,
        tipo=tipo,  # type: ignore[arg-type]
        url=info.get("url", ""),
        mime=info.get("mime"),
        bytes=info.get("size"),
        largura=info.get("width"),
        altura=info.get("height"),
        autor=em.get("Artist"),
        credito=em.get("Credit"),
        licenca=Licenca(
            spdx="CC0-1.0"
            if balde == "livre"
            else "NOASSERTION"
            if balde == "pendente"
            else "CC-BY-SA-4.0",
            balde=balde,
            nome_original=licenca_nome,
            atribuicao=em.get("Credit") or em.get("Artist"),
        ),
        coleta=Coleta(
            metodo=metodo,  # type: ignore[arg-type]
            consultado_em=date.today(),
            endpoint=API,
            evidencia=evidencia,
            http_status=200,
            extmetadata={k: v for k, v in em.items() if v},
        ),
        confianca=0.9 if licenca_nome else 0.4,
    )


def escrever_jsonl(caminho: Path, itens: list[Candidato]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w") as f:
        for c in itens:
            f.write(json.dumps(c.model_dump(mode="json"), ensure_ascii=False) + "\n")
