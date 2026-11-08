"""Endereços públicos do serviço. Domínio é configuração, nunca constante.

Trocar de domínio deve ser mudar variável de ambiente — não caçar string no
código. E como a URL de embed é o contrato do produto, ela é derivada daqui.
"""

from __future__ import annotations

import os

SITE_BASE = os.environ.get("SITE_BASE", "https://coletivo.dev.br").rstrip("/")
CDN_BASE = os.environ.get("CDN_BASE", "https://simbolos.coletivo.dev.br").rstrip("/")
# O serviço de símbolos é o primeiro acervo do coletivo; outros entram como irmãos.
SERVICO = os.environ.get("SERVICO_PATH", "/simbolos").rstrip("/")

EXTENSOES = ("svg", "png", "jpg")


def url_embed(codigo_ibge: str, tipo: str, ext: str) -> str:
    return f"{CDN_BASE}/embed/v1/{tipo}/{codigo_ibge}.{ext}"


def urls_do_item(registro: dict) -> dict[str, str]:
    """As três URLs públicas de um item publicado."""
    return {ext: url_embed(registro["codigo_ibge"], registro["tipo"], ext) for ext in EXTENSOES}


def url_pagina(codigo_ibge: str, slug: str = "") -> str:
    sufixo = f"-{slug}" if slug else ""
    return f"{SITE_BASE}{SERVICO}/municipios/{codigo_ibge}{sufixo}"
