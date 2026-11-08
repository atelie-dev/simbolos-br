"""Modelos de proveniencia: o que torna um arquivo publicavel."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Tipo = Literal["brasao", "bandeira"]
Natureza = Literal[
    "original",
    "exportado",
    "vetorizado",
    "reconstruido",
    "recortado",
    "reduzido",
    "ampliado",
    "indeterminada",
]
Canal = Literal["prefeitura", "estado", "wikimedia", "acervo-legado", "outro"]
BaldeLicenca = Literal["livre", "compartilha", "oficial", "pendente"]

SPDX_POR_BALDE: dict[str, str] = {
    "livre": "CC0-1.0",
    "compartilha": "CC-BY-SA-4.0",
    "oficial": "LicenseRef-simbolo-oficial-municipal",
    "pendente": "NOASSERTION",
}


class Licenca(BaseModel):
    spdx: str
    balde: BaldeLicenca
    url: str | None = None
    nome_original: str | None = None
    atribuicao: str | None = None
    restricoes: list[str] = Field(default_factory=list)


class Coleta(BaseModel):
    """Como o arquivo foi encontrado — a parte que se reaudita em 10 anos."""

    metodo: Literal["wikidata", "commons-categoria", "commons-search", "govbr", "manual"]
    consultado_em: date
    endpoint: str | None = None
    evidencia: dict[str, str] = Field(default_factory=dict)
    http_status: int | None = None
    resposta_sha256: str | None = None
    extmetadata: dict[str, str] = Field(default_factory=dict)


class Candidato(BaseModel):
    codigo_ibge: str
    uf: str
    municipio: str
    tipo: Tipo
    url: str
    mime: str | None = None
    bytes: int | None = None
    largura: int | None = None
    altura: int | None = None
    autor: str | None = None
    credito: str | None = None
    licenca: Licenca
    coleta: Coleta
    confianca: float = 0.0
    avisos: list[str] = Field(default_factory=list)


def balde_de(spdx_ou_nome: str | None) -> BaldeLicenca:
    """Classifica a licenca declarada na origem em um dos tres baldes.

    Qualquer coisa desconhecida cai em 'pendente' — nunca em 'livre'.
    """
    if not spdx_ou_nome:
        return "pendente"
    n = spdx_ou_nome.lower()
    if any(p in n for p in ("public domain", "publicdomain", "pd-", "cc0", "dominio publico")):
        return "livre"
    if "by-sa" in n or "share" in n:
        return "compartilha"
    if "cc by" in n or "cc-by" in n or n.strip() in {"cc-by-4.0", "cc by 4.0"}:
        return "livre"
    return "pendente"
