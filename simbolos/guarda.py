"""Guarda de um item: as casas independentes que têm os mesmos bytes.

Risco não é sobre tamanho nem sobre licença em si — é sobre existir outra cópia
quando esta sumir. `espelhos` é o fato (quem mais guarda o arquivo); `risco` é a
política aplicada sobre ele.

Regra vigente (D21): **vetor é sempre baixo**, porque o SVG publicado é a própria
fonte, byte a byte, e vai versionado no git; **raster segue a regra estrita** e é
alto quando fica sem espelho independente. O motivo continua registrado, então
um leitor discorda da política com o dado na mão.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from urllib.parse import unquote, urlparse

from . import VETORES

COMMONS = "upload.wikimedia.org"

PREMISSAS = (
    "vetor é sempre baixo por decisão (D21)",
    "o SVG publicado é a fonte, byte a byte, e vai versionado em data/vetores",
    "quando ele ainda não está lá, o motivo vetor_versionavel registra a dívida",
)

# Estados de verificação em que o Commons segue valendo como espelho: renomeado
# tem os mesmos bytes, só o título mudou.
_ESPELHO_VALIDO = frozenset({"igual", "renomeado"})


def titulo_commons(origem: str | None) -> str | None:
    """`File:Nome.ext` a partir da URL direta do upload.

    A URL de origem é o endereço do arquivo, não o título: o último segmento é o
    nome do arquivo no instante em que a API respondeu. Se ele for renomeado
    depois, este título deixa de resolver — por isso a conferência cai para a
    busca por sha1 em vez de concluir que o arquivo sumiu.
    """
    if not origem:
        return None
    partes = urlparse(origem)
    if partes.hostname != COMMONS:
        return None
    nome = unquote(partes.path.rstrip("/").rsplit("/", 1)[-1])
    return f"File:{nome}" if nome else None


def vetor_arquivado(reg: dict) -> bool:
    """Se o SVG deste item está versionado em `data/vetores`."""
    if reg.get("formato_origem") != "svg":
        return False
    return (VETORES / reg["tipo"] / f"{reg['codigo_ibge']}.svg").exists()


def classificar(reg: dict, *, vetor_arquivado_em_git: bool | None = None) -> dict:
    """Quem guarda este item além do R2, e o risco que sobra disso.

    `vetor_arquivado_em_git` permite ao chamador passar o fato já apurado; sem
    ele, o fato é lido do disco — a classificação não afirma cópia que não viu.
    """
    motivos: list[str] = []
    espelhos: list[str] = []

    if titulo_commons(reg.get("origem")):
        espelhos.append("commons")
    else:
        motivos.append("origem_fora_do_commons")

    # Licença não resolvida é o caso em que o Commons apaga: ele deixa de contar
    # como espelho justamente quando é a única cópia que temos.
    if reg.get("balde") == "pendente":
        espelhos = [e for e in espelhos if e != "commons"]
        motivos.append("licenca_pendente")

    estado = (reg.get("verificacao") or {}).get("estado")
    if estado in ("divergente", "sumiu"):
        espelhos = [e for e in espelhos if e != "commons"]
        motivos.append(f"fonte_{estado}")
    elif estado not in _ESPELHO_VALIDO:
        motivos.append("nao_verificado")

    if reg.get("formato_origem") == "svg":
        versionado = (
            vetor_arquivado(reg) if vetor_arquivado_em_git is None else vetor_arquivado_em_git
        )
        if versionado:
            espelhos.append("git")
            motivos.append("vetor_versionado")
        else:
            motivos.append("vetor_versionavel")
        return {"espelhos": sorted(set(espelhos)), "risco": "baixo", "motivo": motivos}

    return {
        "espelhos": sorted(set(espelhos)),
        "risco": "baixo" if espelhos else "alto",
        "motivo": motivos,
    }


def relatorio(regs: list[dict]) -> dict:
    """O que está guardado só no R2, e por quê.

    Só os itens de risco alto entram na lista: o arquivo é o alarme, não o
    inventário — quem quer o inventário completo lê os sidecars.
    """
    altos: list[dict] = []
    resumo: Counter[str] = Counter()
    motivos: Counter[str] = Counter()

    for reg in regs:
        if reg.get("estado") != "publicado":
            continue
        situacao = classificar(reg)
        resumo[situacao["risco"]] += 1
        motivos.update(situacao["motivo"])
        if situacao["risco"] != "alto":
            continue
        altos.append(
            {
                "codigo_ibge": reg["codigo_ibge"],
                "tipo": reg["tipo"],
                "uf": reg.get("uf"),
                "municipio": reg.get("municipio"),
                "balde": reg.get("balde"),
                "espelhos": situacao["espelhos"],
                "motivo": situacao["motivo"],
            }
        )

    altos.sort(key=lambda x: (x["uf"] or "", x["codigo_ibge"], x["tipo"]))
    return {
        "gerado_em": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "premissas": list(PREMISSAS),
        "resumo": {
            "itens": sum(resumo.values()),
            "risco_alto": resumo["alto"],
            "risco_baixo": resumo["baixo"],
            "por_motivo": dict(sorted(motivos.items())),
        },
        "risco_alto": altos,
    }
