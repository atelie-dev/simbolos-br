"""Upload para o R2: o CDN público e o acervo privado.

Dois buckets, porque o domínio customizado de um bucket expõe **tudo** o que
está dentro: o que é servido e o que é arquivo não podem morar juntos.

  simbolos-br-cdn     público   embed/v1/...  meta/v1/...
  simbolos-br-acervo  privado   fontes/v1/... evidencias/pdf/...

O envio é idempotente por `sha256` (num livro-razão local), então rodar de novo
depois de publicar mais itens envia só o que mudou.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config

from . import DATA, META

# Cache longo com revalidação: o caminho é o contrato, o conteúdo muda por purge.
CACHE_IMAGEM = "public, max-age=604800, stale-while-revalidate=86400"
CACHE_META = "public, max-age=3600, stale-while-revalidate=600"
CACHE_ACERVO = "private, max-age=0"

TIPOS = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".webp": "image/webp",
}

BUCKETS = {
    "cdn": ("CLOUDFLARE_R2_BUCKET_CDN", "simbolos-br-cdn"),
    "acervo": ("CLOUDFLARE_R2_BUCKET_ACERVO", "simbolos-br-acervo"),
}

LEDGER_CDN = DATA / "_cache" / "r2-cdn.json"
LEDGER_ACERVO = DATA / "_cache" / "r2-acervo.json"

EXTENSOES = ("svg", "png", "jpg")


def cliente():
    """Cliente S3 do R2. As chaves vêm do .env montado pelo 1Password."""
    faltando = [
        v
        for v in (
            "CLOUDFLARE_R2_ENDPOINT",
            "CLOUDFLARE_R2_ACCESS_KEY_ID",
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
        )
        if not os.environ.get(v)
    ]
    if faltando:
        raise RuntimeError(f"faltam variaveis no .env: {', '.join(faltando)}")
    return boto3.client(
        "s3",
        endpoint_url=os.environ["CLOUDFLARE_R2_ENDPOINT"],
        aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 5, "mode": "standard"},
            max_pool_connections=32,
        ),
    )


def nome_bucket(papel: str) -> str:
    chave, padrao = BUCKETS[papel]
    return os.environ.get(chave, padrao)


def sha256_arquivo(caminho: Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        while pedaco := f.read(bloco):
            h.update(pedaco)
    return h.hexdigest()


def _ascii(valor: object) -> str:
    """Metadado do S3 é ASCII; acento vira nada em vez de derrubar o envio."""
    return str(valor).encode("ascii", "ignore").decode().strip() or "-"


def _metadados(registro: dict, sha: str | None) -> dict[str, str]:
    md = {
        "cod-ibge": _ascii(registro.get("codigo_ibge")),
        "tipo": _ascii(registro.get("tipo")),
    }
    if sha:
        md["sha256"] = sha
    if registro.get("licenca"):
        md["licenca"] = _ascii(registro["licenca"])
    return md


def _carregar_ledger(caminho: Path) -> dict[str, str]:
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text())
    except ValueError:
        return {}


def _gravar_ledger(caminho: Path, dados: dict[str, str]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(dados, indent=0, sort_keys=True) + "\n")
    tmp.replace(caminho)


def objetos_cdn(raiz: Path, registros: list[dict]) -> list[tuple[Path, str, str, dict]]:
    """O que o CDN serve: as três renditions de cada item e o sidecar."""
    itens: list[tuple[Path, str, str, dict]] = []
    for reg in registros:
        if reg.get("estado") != "publicado":
            continue
        tipo, cod = reg["tipo"], reg["codigo_ibge"]
        rendicoes = reg.get("rendicoes") or {}
        for ext in EXTENSOES:
            local = raiz / "embed" / "v1" / tipo / f"{cod}.{ext}"
            if not local.exists():
                continue
            sha = (rendicoes.get(ext) or {}).get("sha256") or sha256_arquivo(local)
            itens.append((local, f"embed/v1/{tipo}/{cod}.{ext}", sha, reg))
        meta = META / tipo / f"{cod}.json"
        if meta.exists():
            itens.append((meta, f"meta/v1/{tipo}/{cod}.json", sha256_arquivo(meta), reg))
    return itens


def objetos_acervo() -> list[tuple[Path, str, str]]:
    """O que é arquivo, não serviço: fontes originais e evidências."""
    itens: list[tuple[Path, str, str]] = []
    for prefixo, base in (("fontes", DATA / "fontes"), ("evidencias", DATA / "evidencias")):
        if not base.exists():
            continue
        for arq in base.rglob("*"):
            if arq.is_file() and not arq.name.endswith(".tmp"):
                itens.append(
                    (arq, f"{prefixo}/{arq.relative_to(base).as_posix()}", sha256_arquivo(arq))
                )
    return itens


def _enviar_um(
    s3, balde: str, local: Path, chave: str, sha: str, registro: dict, cache: str
) -> None:
    ext = local.suffix.lower()
    # Sidecar muda quando a licença ou a procedência é corrigida: cache curto.
    efetivo = CACHE_META if ext == ".json" else cache
    s3.upload_file(
        str(local),
        balde,
        chave,
        ExtraArgs={
            "ContentType": TIPOS.get(ext, "application/octet-stream"),
            "CacheControl": efetivo,
            "Metadata": _metadados(registro, sha),
        },
    )


def _enviar(
    itens: list[tuple[Path, str, str, dict]],
    *,
    papel: str,
    ledger_path: Path,
    cache: str,
    concorrencia: int,
    forcar: bool,
) -> dict:
    ledger = _carregar_ledger(ledger_path)
    balde = nome_bucket(papel)
    resumo: dict = {"objetos": len(itens), "enviados": 0, "pulados": 0, "falhas": {}, "bytes": 0}

    fila = []
    for local, chave, sha, reg in itens:
        if not forcar and ledger.get(chave) == sha:
            resumo["pulados"] += 1
            continue
        fila.append((local, chave, sha, reg))

    if not fila:
        return resumo

    s3 = cliente()
    inicio = time.time()
    with ThreadPoolExecutor(max_workers=concorrencia) as pool:
        futuros = {
            pool.submit(_enviar_um, s3, balde, local, chave, sha, reg, cache): (local, chave, sha)
            for local, chave, sha, reg in fila
        }
        for feito, fut in enumerate(as_completed(futuros), 1):
            local, chave, sha = futuros[fut]
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                resumo["falhas"][chave] = str(exc)[:120]
            else:
                ledger[chave] = sha
                resumo["enviados"] += 1
                resumo["bytes"] += local.stat().st_size
            if feito % 200 == 0:
                _gravar_ledger(ledger_path, ledger)
                print(
                    f"[{feito}/{len(fila)}] {resumo['enviados']} enviados "
                    f"| {len(resumo['falhas'])} falhas "
                    f"| {resumo['bytes'] / 1024 / 1024:.0f} MB "
                    f"| {time.time() - inicio:.0f}s",
                    flush=True,
                )
    _gravar_ledger(ledger_path, ledger)
    return resumo


def enviar_cdn(
    raiz: Path,
    registros: list[dict],
    *,
    concorrencia: int = 16,
    limite: int = 0,
    forcar: bool = False,
    prefixo: str = "",
) -> dict:
    """Sobe `embed/` e `meta/` para o bucket público."""
    itens = objetos_cdn(raiz, registros)
    if prefixo:
        itens = [i for i in itens if i[1].startswith(prefixo)]
    if limite:
        itens = itens[:limite]
    return _enviar(
        itens,
        papel="cdn",
        ledger_path=LEDGER_CDN,
        cache=CACHE_IMAGEM,
        concorrencia=concorrencia,
        forcar=forcar,
    )


def enviar_acervo(*, concorrencia: int = 8, limite: int = 0, forcar: bool = False) -> dict:
    """Sobe o arquivo privado: fontes originais e PDFs de atos.

    É o único backup que o acervo tem hoje, então este comando não é opcional
    para a saúde do projeto.
    """
    itens: list[tuple[Path, str, str, dict]] = [
        (local, chave, sha, {}) for local, chave, sha in objetos_acervo()
    ]
    if limite:
        itens = itens[:limite]
    return _enviar(
        itens,
        papel="acervo",
        ledger_path=LEDGER_ACERVO,
        cache=CACHE_ACERVO,
        concorrencia=concorrencia,
        forcar=forcar,
    )
