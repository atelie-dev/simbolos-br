"""Conferência da procedência: o que temos em disco e o que a origem ainda diz.

Duas perguntas diferentes, de propósito:

  atestar          offline   relê o arquivo guardado e completa o sidecar
  verificar_fonte  na rede   compara o sha1 guardado com o que o Commons publica

Separar as duas evita o custo do `fontes`: rebaixar 1,3 GB só para descobrir um
hash que já estava em disco. E separa também as duas datas — a da captura, que
não muda, e a da conferência, que é sempre agora.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from . import DIST, commons, guarda, publicacao

LOTE = 50  # limite da API do Commons por requisição


def _agora() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hashes(arquivo: Path) -> tuple[str, str, int]:
    """sha256, sha1 e tamanho numa passada só: 1,3 GB não se lê duas vezes."""
    h256, h1 = hashlib.sha256(), hashlib.sha1()
    total = 0
    with arquivo.open("rb") as f:
        while bloco := f.read(1 << 20):
            h256.update(bloco)
            h1.update(bloco)
            total += len(bloco)
    return h256.hexdigest(), h1.hexdigest(), total


def arquivo_guardado(reg: dict, raiz: Path = DIST) -> Path | None:
    """Onde está a fonte deste item: o SVG publicado ou o raster arquivado."""
    if reg.get("formato_origem") == "svg":
        return raiz / "embed" / "v1" / reg["tipo"] / f"{reg['codigo_ibge']}.svg"
    return publicacao.caminho_fonte(reg.get("fonte"))


def atestar(*, raiz: Path = DIST, uf: str | None = None, limite: int = 0) -> dict:
    """Completa o sidecar com o que só o disco sabe: sha1, bytes e data de captura.

    Não corrige hash divergente em silêncio: um arquivo em disco que não bate com
    o `sha256_origem` vira `conflito_local` e o item não é reatestado.
    """
    regs = [r for r in publicacao.indice_meta().values() if not uf or r.get("uf") == uf]
    regs.sort(key=lambda r: (r["codigo_ibge"], r["tipo"]))
    if limite:
        regs = regs[:limite]

    resumo = {"itens": 0, "atestados": 0, "sem_arquivo": 0, "divergentes": 0, "bytes": 0}
    for reg in regs:
        resumo["itens"] += 1
        arquivo = arquivo_guardado(reg, raiz)
        if arquivo is None or not arquivo.exists():
            resumo["sem_arquivo"] += 1
            continue

        h256, h1, tamanho = _hashes(arquivo)
        esperado = reg.get("sha256_origem")
        if esperado and esperado != h256:
            reg["conflito_local"] = {"esperado": esperado, "obtido": h256}
            resumo["divergentes"] += 1
        else:
            reg["sha256_origem"] = h256
            reg["sha1_origem"] = h1
            reg["bytes_origem"] = tamanho
            resumo["bytes"] += tamanho
            if not reg.get("capturado_em"):
                reg["capturado_em"] = publicacao.mtime(arquivo)
                reg["captura_fonte"] = "mtime"
            if not reg.get("titulo_commons"):
                titulo = guarda.titulo_commons(reg.get("origem"))
                if titulo:
                    reg["titulo_commons"] = titulo

        reg["guarda"] = guarda.classificar(reg)
        publicacao.gravar_meta(reg)
        resumo["atestados"] += 1

        if resumo["itens"] % 1000 == 0:
            print(
                f"[{resumo['itens']}/{len(regs)}] {resumo['atestados']} atestados "
                f"| {resumo['bytes'] / 1024 / 1024:.0f} MB lidos",
                flush=True,
            )
    return resumo


def _anotar(
    reg: dict, estado: str, *, sha1_commons: str | None = None, titulo_atual: str | None = None
) -> None:
    verificacao = {"em": _agora(), "estado": estado}
    if sha1_commons:
        verificacao["sha1_commons"] = sha1_commons
    if titulo_atual:
        verificacao["titulo_atual"] = titulo_atual
    reg["verificacao"] = verificacao
    reg["guarda"] = guarda.classificar(reg)
    publicacao.gravar_meta(reg)


def verificar_fonte(*, uf: str | None = None, limite: int = 0, forcar: bool = False) -> dict:
    """Compara cada item com o Commons pelo sha1, sem baixar arquivo.

    Quatro estados: **igual**; **divergente** (o Commons re-enviou outra versão
    sob o mesmo nome); **renomeado** (o título derivado da URL não resolve, mas
    os bytes estão sob outro nome); e **sumiu** (nem título, nem sha1).
    """
    regs = [r for r in publicacao.indice_meta().values() if not uf or r.get("uf") == uf]
    regs.sort(key=lambda r: (r["codigo_ibge"], r["tipo"]))
    if limite:
        regs = regs[:limite]

    resumo = {
        "itens": 0,
        "igual": 0,
        "divergente": 0,
        "renomeado": 0,
        "sumiu": 0,
        "sem_hash": 0,
        "sem_titulo": 0,
        "pulados": 0,
        "lotes": 0,
    }
    por_titulo: dict[str, list[dict]] = defaultdict(list)
    for reg in regs:
        if not forcar and (reg.get("verificacao") or {}).get("em"):
            resumo["pulados"] += 1
            continue
        if not reg.get("sha1_origem"):
            # Sem sha1 não há o que comparar: rode `simbolos atestar` antes.
            resumo["sem_hash"] += 1
            resumo["itens"] += 1
            continue
        titulo = reg.get("titulo_commons") or guarda.titulo_commons(reg.get("origem"))
        if not titulo:
            resumo["sem_titulo"] += 1
            resumo["itens"] += 1
            continue
        por_titulo[titulo].append(reg)

    titulos = sorted(por_titulo)
    inicio = time.time()
    perdidos: list[str] = []
    for i in range(0, len(titulos), LOTE):
        lote = titulos[i : i + LOTE]
        infos = commons.sha1_por_titulo(lote)
        resumo["lotes"] += 1
        for titulo in lote:
            info = infos.get(commons.chave(titulo))
            if info is None:
                perdidos.append(titulo)
                continue
            for reg in por_titulo[titulo]:
                estado = "igual" if info.get("sha1") == reg["sha1_origem"] else "divergente"
                _anotar(reg, estado, sha1_commons=info.get("sha1"))
                resumo[estado] += 1
                resumo["itens"] += 1
        if resumo["lotes"] % 20 == 0:
            print(
                f"[{min(i + LOTE, len(titulos))}/{len(titulos)} titulos] "
                f"{resumo['igual']} iguais | {resumo['divergente']} divergentes "
                f"| {time.time() - inicio:.0f}s",
                flush=True,
            )

    # Título que não resolve: pode ser renomeação, não sumiço. A busca por sha1
    # decide com o hash, que é o que de fato identifica o arquivo.
    for titulo in perdidos:
        for reg in por_titulo[titulo]:
            atual = commons.titulo_do_sha1(reg.get("sha1_origem") or "")
            if atual:
                _anotar(reg, "renomeado", titulo_atual=atual)
                resumo["renomeado"] += 1
            else:
                _anotar(reg, "sumiu")
                resumo["sumiu"] += 1
            resumo["itens"] += 1

    return resumo
