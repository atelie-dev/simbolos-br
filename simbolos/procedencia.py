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

from . import DIST, VETORES, commons, guarda, publicacao, rede

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
    """Onde está a fonte deste item: o SVG versionado ou o raster arquivado.

    Prefere `data/vetores` a `dist`: o acervo é a verdade, a saída é cópia.
    """
    if reg.get("formato_origem") == "svg":
        versionado = VETORES / reg["tipo"] / f"{reg['codigo_ibge']}.svg"
        if versionado.exists():
            return versionado
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
    reg: dict,
    estado: str,
    *,
    sha1_commons: str | None = None,
    titulo_atual: str | None = None,
    http: int | None = None,
) -> None:
    verificacao = {"em": _agora(), "estado": estado}
    if sha1_commons:
        verificacao["sha1_commons"] = sha1_commons
    if titulo_atual:
        verificacao["titulo_atual"] = titulo_atual
    if http is not None:
        verificacao["http"] = http
    reg["verificacao"] = verificacao
    reg["guarda"] = guarda.classificar(reg)
    publicacao.gravar_meta(reg)


LIMITE_COMPARACAO = 10 * 1024 * 1024


def _verificar_link(reg: dict) -> None:
    """Origem fora do Commons: o link responde e os bytes são os mesmos?

    É o único teste possível para um item que veio de um site de prefeitura —
    não existe hash publicado por terceiro para comparar.
    """
    url = reg.get("origem") or ""
    if not url.startswith(("http://", "https://")):
        _anotar(reg, "sem_fonte")
        return
    try:
        resposta = rede.requisitar(url, tentativas=2, timeout=30.0)
    except Exception:  # noqa: BLE001
        _anotar(reg, "link_morto")
        return
    if resposta.status_code >= 400:
        _anotar(reg, "link_morto", http=resposta.status_code)
        return

    esperado = reg.get("sha256_origem")
    conteudo = resposta.content
    if esperado and 0 < len(conteudo) <= LIMITE_COMPARACAO:
        estado = "igual" if publicacao.sha256(conteudo) == esperado else "divergente"
    else:
        estado = "link_vivo"
    _anotar(reg, estado, http=resposta.status_code)


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
        "link_vivo": 0,
        "link_morto": 0,
        "sem_fonte": 0,
        "sem_hash": 0,
        "pulados": 0,
        "lotes": 0,
    }
    por_titulo: dict[str, list[dict]] = defaultdict(list)
    sem_commons: list[dict] = []
    for reg in regs:
        if not forcar and (reg.get("verificacao") or {}).get("em"):
            resumo["pulados"] += 1
            continue
        titulo = reg.get("titulo_commons") or guarda.titulo_commons(reg.get("origem"))
        if not titulo:
            # Origem fora do Commons (.gov.br): não há sha1 publicado para
            # comparar. A pergunta passa a ser se o link ainda responde.
            sem_commons.append(reg)
            continue
        if not reg.get("sha1_origem"):
            # Sem sha1 não há o que comparar: rode `simbolos atestar` antes.
            resumo["sem_hash"] += 1
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

    # Por último, quem não tem espelho no Commons: o link de origem responde?
    for reg in sem_commons:
        _verificar_link(reg)
        resumo[reg["verificacao"]["estado"]] += 1
        resumo["itens"] += 1

    return resumo


def _gravar_atomico(destino: Path, conteudo: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".tmp")
    tmp.write_bytes(conteudo)
    tmp.replace(destino)


def _vetoriais(*, uf: str | None = None) -> list[dict]:
    regs = [r for r in publicacao.indice_meta().values() if r.get("formato_origem") == "svg"]
    regs = [r for r in regs if not uf or r.get("uf") == uf]
    regs.sort(key=lambda r: (r["codigo_ibge"], r["tipo"]))
    return regs


def _atualizar_guarda(reg: dict) -> None:
    """Recalcula a guarda com o fato atual e regrava o sidecar."""
    reg["guarda"] = guarda.classificar(reg)
    publicacao.gravar_meta(reg)


def arquivar_vetores(*, raiz: Path = DIST, uf: str | None = None, forcar: bool = False) -> dict:
    """Copia os SVGs publicados para `data/vetores`, conferindo o sha256 do sidecar.

    O SVG publicado é a fonte, byte a byte. Versioná-lo é o que torna o acervo
    reproduzível sem rede — e o que devolve a `dist/` o papel de saída.
    """
    resumo = {
        "itens": 0,
        "arquivados": 0,
        "ja_tinha": 0,
        "sem_svg": 0,
        "divergentes": 0,
        "bytes": 0,
    }
    conflito = VETORES.parent / "conflito"
    for reg in _vetoriais(uf=uf):
        resumo["itens"] += 1
        origem = raiz / "embed" / "v1" / reg["tipo"] / f"{reg['codigo_ibge']}.svg"
        if not origem.exists():
            resumo["sem_svg"] += 1
            continue
        conteudo = origem.read_bytes()
        obtido = publicacao.sha256(conteudo)
        esperado = reg.get("sha256_origem")
        if esperado and obtido != esperado:
            _gravar_atomico(conflito / reg["tipo"] / f"{reg['codigo_ibge']}.svg", conteudo)
            resumo["divergentes"] += 1
            continue
        destino = VETORES / reg["tipo"] / f"{reg['codigo_ibge']}.svg"
        if destino.exists() and not forcar:
            if publicacao.sha256(destino.read_bytes()) == obtido:
                resumo["ja_tinha"] += 1
                _atualizar_guarda(reg)
                continue
            # Já existe com outro conteúdo: não sobrescreve sem --forcar.
            resumo["divergentes"] += 1
            continue
        _gravar_atomico(destino, conteudo)
        resumo["arquivados"] += 1
        resumo["bytes"] += len(conteudo)
        _atualizar_guarda(reg)
    return resumo


def restaurar_vetores(*, raiz: Path = DIST, uf: str | None = None) -> dict:
    """Devolve os SVGs versionados para `dist/embed`, conferindo o hash.

    É o caminho de quem clonou o repositório: `dist/` é saída e não vem no git;
    o que vem é a fonte, em `data/vetores`.
    """
    resumo = {"itens": 0, "restaurados": 0, "ja_tinha": 0, "sem_arquivo": 0, "bytes": 0}
    for reg in _vetoriais(uf=uf):
        resumo["itens"] += 1
        fonte = VETORES / reg["tipo"] / f"{reg['codigo_ibge']}.svg"
        if not fonte.exists():
            resumo["sem_arquivo"] += 1
            continue
        conteudo = fonte.read_bytes()
        destino = raiz / "embed" / "v1" / reg["tipo"] / f"{reg['codigo_ibge']}.svg"
        if destino.exists() and publicacao.sha256(destino.read_bytes()) == publicacao.sha256(
            conteudo
        ):
            resumo["ja_tinha"] += 1
            continue
        _gravar_atomico(destino, conteudo)
        resumo["restaurados"] += 1
        resumo["bytes"] += len(conteudo)
    return resumo
