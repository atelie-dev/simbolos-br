"""Publicação local: baixar, validar, renderizar e montar a árvore de embed.

Saída (descartável por convenção):
  dist/embed/v1/{brasao|bandeira}/{cod_ibge}.{svg,png,jpg}
  dist/catalogo.json                               (agregado, derivado)

Fora da saída, porque é a verdade e não se regenera sem baixar de novo:
  data/meta/v1/{brasao|bandeira}/{cod_ibge}.json   (sidecar do item)

O SVG é servido como veio (sanitizado por validação), o PNG é 512×512 com fundo
transparente e o JPG é 512×512 com fundo branco — nunca esticando a arte.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from . import DATA, META, VETORES, guarda, rede

LADO = 512
RESPIRO = 0.02
QUALIDADE_JPG = 88
TIMEOUT = 90.0

# Fonte canonica: o arquivo exatamente como veio da origem. Rendition e derivado;
# se o original nao fica em disco, o acervo guarda a versao pequena e perde a boa.
FONTES = DATA / "fontes" / "v1"
FONTES_REL = "data/fontes/v1"

EXT_POR_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/tiff": "tif",
    "image/bmp": "bmp",
    "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico",
}

_SVG_PROIBIDO = re.compile(
    r"<script|\son[a-z]+\s*=|<foreignObject|xlink:href\s*=\s*[\"']https?://|href\s*=\s*[\"']https?://",
    re.IGNORECASE,
)


def baixar(url: str, tentativas: int = 5) -> bytes:
    """GET com polidez por host e backoff em 429/503 — a política vive em `rede`."""
    return rede.baixar(url, tentativas=tentativas)


def validar_svg(conteudo: bytes) -> str | None:
    texto = conteudo.decode("utf-8", errors="ignore")
    if "<svg" not in texto[:2000].lower():
        return "svg_sem_raiz"
    achado = _SVG_PROIBIDO.search(texto)
    if achado:
        return f"svg_inseguro:{achado.group(0)[:20]}"
    return None


def _canvas(imagem: Image.Image, fundo: tuple | None) -> Image.Image:
    """Encaixa a arte num quadrado de LADO, preservando proporção."""
    margem = int(LADO * RESPIRO)
    util = LADO - 2 * margem
    copia = imagem.copy()
    copia.thumbnail((util, util), Image.LANCZOS)
    base = (
        Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
        if fundo is None
        else Image.new("RGBA", (LADO, LADO), (*fundo, 255))
    )
    x = (LADO - copia.width) // 2
    y = (LADO - copia.height) // 2
    base.alpha_composite(copia, (x, y))
    return base


def _png_e_jpg(imagem: Image.Image) -> tuple[bytes, bytes]:
    rgba = _canvas(imagem.convert("RGBA"), None)
    buf_png = io.BytesIO()
    rgba.save(buf_png, format="PNG", optimize=True)

    branco = Image.new("RGB", (LADO, LADO), (255, 255, 255))
    branco.paste(rgba, mask=rgba.getchannel("A"))
    buf_jpg = io.BytesIO()
    branco.save(buf_jpg, format="JPEG", quality=QUALIDADE_JPG, optimize=True, progressive=True)
    return buf_png.getvalue(), buf_jpg.getvalue()


def svg_para_png(conteudo: bytes) -> bytes:
    """Renderiza o SVG a 1024 e devolve PNG (para depois reduzir a 512)."""
    with tempfile.TemporaryDirectory() as tmp:
        origem = Path(tmp) / "in.svg"
        destino = Path(tmp) / "out.png"
        origem.write_bytes(conteudo)
        subprocess.run(
            ["resvg", "--width", "1024", str(origem), str(destino)],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return destino.read_bytes()


def sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def sha1(conteudo: bytes) -> str:
    """SHA1 do arquivo de origem: é o formato que a API do Commons publica.

    Sem ele, conferir procedência custa rebaixar 1,3 GB; com ele, custa uma
    requisição por lote de 50 itens.
    """
    return hashlib.sha1(conteudo).hexdigest()


def agora() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def mtime(arquivo: Path) -> str:
    """Data de captura lida do sistema de arquivos, em UTC.

    É a hora em que o arquivo foi gravado, não a da execução. Para a safra
    antiga é a única data de captura que existe — e inventar outra seria pior
    que declarar a origem do dado em `captura_fonte`.
    """
    return datetime.fromtimestamp(arquivo.stat().st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _relativo(arquivo: Path) -> str:
    """Caminho legivel no registro: relativo a `data/` quando possivel."""
    return str(arquivo.relative_to(DATA)) if arquivo.is_relative_to(DATA) else str(arquivo)


def caminho_fonte(fonte: dict | None) -> Path | None:
    """Onde o original foi arquivado, a partir do campo `fonte` do sidecar."""
    arq = (fonte or {}).get("arquivo")
    if not arq:
        return None
    p = Path(arq)
    return p if p.is_absolute() else DATA / p


def guardar_fonte(base: Path, codigo: str, tipo: str, mime: str, conteudo: bytes) -> Path:
    """Grava o arquivo de origem, byte a byte, fora da arvore de embed."""
    ext = EXT_POR_MIME.get((mime or "").lower(), "bin")
    pasta = base / tipo
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{codigo}.{ext}"
    if destino.exists() and sha256(destino.read_bytes()) == sha256(conteudo):
        return destino
    tmp = destino.with_suffix(destino.suffix + ".tmp")
    tmp.write_bytes(conteudo)
    tmp.replace(destino)
    return destino


def ler_fonte_local(
    item: dict, tipo: str, base_fontes: Path | None = None
) -> tuple[bytes, Path] | None:
    """O arquivo já arquivado deste item, se existir em disco.

    A publicação lê daqui **antes** da rede: é o que faz o acervo versionado ser
    a fonte, e não só um backup. Sem isso, um clone do repositório não republica
    nada sem rebaixar 1,6 GB do Commons.
    """
    codigo = item["codigo_ibge"]
    dados = item[tipo]
    if (dados.get("mime") or "").lower() == "image/svg+xml":
        alvo = VETORES / tipo / f"{codigo}.svg"
        return (alvo.read_bytes(), alvo) if alvo.exists() else None

    pasta = (base_fontes or FONTES) / tipo
    ext = EXT_POR_MIME.get((dados.get("mime") or "").lower())
    candidatos = [pasta / f"{codigo}.{ext}"] if ext else []
    candidatos += sorted(p for p in pasta.glob(f"{codigo}.*") if p.suffix != ".tmp")
    for alvo in candidatos:
        if alvo.exists() and alvo.suffix != ".svg":
            return alvo.read_bytes(), alvo
    return None


def publicar_item(
    item: dict,
    tipo: str,
    raiz: Path,
    fontes: Path | None = None,
    esperado: dict | None = None,
) -> dict:
    """Valida, renderiza e grava as renditions de um item. Devolve o registro.

    Tenta o arquivo já arquivado antes de baixar: é o que permite a um clone do
    repositório republicar sem rede. `esperado` é o registro anterior — se o
    hash do arquivo local não bate com o que foi publicado, ele não serve, e a
    rede decide.
    """
    base_fontes = fontes or FONTES
    dados = item[tipo]
    registro = {
        "codigo_ibge": item["codigo_ibge"],
        "uf": item["uf"],
        "municipio": item["municipio"],
        "tipo": tipo,
        "origem": dados["url"],
        "licenca": dados["licenca"],
        "balde": dados["balde"],
        "autor": dados.get("autor"),
        "estado": "falhou",
    }

    local = ler_fonte_local(item, tipo, base_fontes)
    anterior = (esperado or {}).get("sha256_origem")
    if local is not None and anterior and sha256(local[0]) != anterior:
        local = None
    if local is not None:
        conteudo, arquivo_local = local
        capturado, captura_fonte = mtime(arquivo_local), "arquivo"
    else:
        try:
            conteudo = baixar(dados["url"])
        except Exception as exc:  # noqa: BLE001
            registro["erro"] = f"download: {exc}"[:160]
            return registro
        capturado, captura_fonte = agora(), "relogio"

    mime = dados.get("mime") or ""
    pasta = raiz / "embed" / "v1" / tipo
    pasta.mkdir(parents=True, exist_ok=True)

    try:
        if mime == "image/svg+xml":
            problema = validar_svg(conteudo)
            if problema:
                registro["erro"] = problema
                return registro
            png_fonte = svg_para_png(conteudo)
            imagem = Image.open(io.BytesIO(png_fonte))
            (pasta / f"{item['codigo_ibge']}.svg").write_bytes(conteudo)
            registro["formato_origem"] = "svg"
        else:
            imagem = Image.open(io.BytesIO(conteudo))
            imagem.load()
            registro["formato_origem"] = mime
        png, jpg = _png_e_jpg(imagem)
    except Exception as exc:  # noqa: BLE001
        registro["erro"] = f"render: {exc}"[:160]
        return registro

    (pasta / f"{item['codigo_ibge']}.png").write_bytes(png)
    (pasta / f"{item['codigo_ibge']}.jpg").write_bytes(jpg)
    hash_origem = sha256(conteudo)
    hash1_origem = sha1(conteudo)
    registro.update(
        {
            "estado": "publicado",
            "sha256_origem": hash_origem,
            "sha1_origem": hash1_origem,
            "bytes_origem": len(conteudo),
            # D7: a procedência é capturada, com data. `relogio` distingue o
            # download do preenchimento a partir do arquivo já guardado.
            "capturado_em": capturado,
            "captura_fonte": captura_fonte,
            "rendicoes": {
                "png": {"bytes": len(png), "sha256": sha256(png), "lado": LADO},
                "jpg": {"bytes": len(jpg), "sha256": sha256(jpg), "lado": LADO},
            },
        }
    )
    titulo = guarda.titulo_commons(dados["url"])
    if titulo:
        registro["titulo_commons"] = titulo
    if (pasta / f"{item['codigo_ibge']}.svg").exists():
        # No SVG o arquivo publicado e a fonte, byte a byte: nao ha o que duplicar.
        registro["rendicoes"]["svg"] = {"bytes": len(conteudo), "sha256": hash_origem}
    else:
        # Raster: o original nao cabe na rendition. Sem ele o acervo guarda a
        # versao reduzida e perde a boa, e a procedencia deixa de ser refazivel.
        arquivo = guardar_fonte(base_fontes, item["codigo_ibge"], tipo, mime, conteudo)
        registro["fonte"] = {
            "arquivo": _relativo(arquivo),
            "bytes": len(conteudo),
            "sha256": hash_origem,
            "sha1": hash1_origem,
        }
    registro["guarda"] = guarda.classificar(registro)
    return registro


def _pasta_meta(tipo: str) -> Path:
    return META / tipo


def gravar_meta(registro: dict) -> None:
    """Sidecar por ativo: a verdade sobre um item, ao lado do catálogo agregado.

    O catálogo é derivado e escrito em lote; o sidecar é escrito assim que o
    item fica publicado. Se o processo morrer no meio, o próximo run reconstrói
    o agregado a partir dos sidecars sem baixar nada de novo.

    Mora em `data/meta`, não em `dist`: `dist` é saída e pode ser apagada, e a
    procedência não pode ser regenerada sem rebaixar o arquivo.
    """
    if registro.get("estado") != "publicado":
        return
    pasta = _pasta_meta(registro["tipo"])
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{registro['codigo_ibge']}.json"
    tmp = destino.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(destino)


def indice_meta() -> dict[tuple[str, str], dict]:
    """Todos os itens publicados segundo os sidecars."""
    indice: dict[tuple[str, str], dict] = {}
    if not META.exists():
        return indice
    for arq in META.rglob("*.json"):
        try:
            reg = json.loads(arq.read_text())
        except OSError, ValueError:
            continue
        if reg.get("estado") == "publicado":
            indice[(reg["codigo_ibge"], reg["tipo"])] = reg
    return indice


def registro_do_disco(item: dict, tipo: str, raiz: Path) -> dict | None:
    """Reconstrói o registro a partir das renditions já gravadas.

    `sha256_origem` fica nulo e o item é marcado `reconstruido`: o arquivo de
    origem não está em disco e inventar um hash seria pior que declarar a lacuna.
    """
    pasta = raiz / "embed" / "v1" / tipo
    png = pasta / f"{item['codigo_ibge']}.png"
    jpg = pasta / f"{item['codigo_ibge']}.jpg"
    if not (png.exists() and jpg.exists()):
        return None
    dados = item[tipo]
    rendicoes: dict[str, dict] = {}
    for ext, arq in (("png", png), ("jpg", jpg)):
        conteudo = arq.read_bytes()
        rendicoes[ext] = {"bytes": len(conteudo), "sha256": sha256(conteudo), "lado": LADO}
    svg = pasta / f"{item['codigo_ibge']}.svg"
    origem: dict = {}
    if svg.exists():
        conteudo = svg.read_bytes()
        rendicoes["svg"] = {"bytes": len(conteudo), "sha256": sha256(conteudo)}
        # No SVG o arquivo publicado é a fonte, byte a byte: dá para atestar o
        # hash sem rebaixar nada. No raster não dá — a rendition não é o original.
        origem = {
            "sha256_origem": rendicoes["svg"]["sha256"],
            "sha1_origem": sha1(conteudo),
            "bytes_origem": len(conteudo),
            "capturado_em": mtime(svg),
            "captura_fonte": "mtime",
        }
    registro = {
        "codigo_ibge": item["codigo_ibge"],
        "uf": item["uf"],
        "municipio": item["municipio"],
        "tipo": tipo,
        "origem": dados["url"],
        "licenca": dados["licenca"],
        "balde": dados["balde"],
        "autor": dados.get("autor"),
        "estado": "publicado",
        "formato_origem": "svg" if "svg" in rendicoes else dados.get("mime"),
        "sha256_origem": None,
        "reconstruido": True,
        "rendicoes": rendicoes,
        **origem,
    }
    titulo = guarda.titulo_commons(registro["origem"])
    if titulo:
        registro["titulo_commons"] = titulo
    registro["guarda"] = guarda.classificar(registro)
    return registro


def gravar_catalogo(destino: Path, final: dict[tuple[str, str], dict]) -> None:
    """Escrita atômica: um kill no meio não deixa JSON truncado."""
    ordem = sorted(final)
    tmp = destino.with_suffix(".json.tmp")
    tmp.write_text(json.dumps([final[k] for k in ordem], ensure_ascii=False, indent=1) + "\n")
    tmp.replace(destino)


def publicar(
    catalogo: dict,
    raiz: Path,
    *,
    limite: int = 0,
    uf: str | None = None,
) -> dict:
    if shutil.which("resvg") is None:
        raise RuntimeError(
            "resvg nao encontrado no PATH: rode dentro do devenv (`devenv shell`) "
            "ou instale o pacote. Sem ele nenhum SVG e renderizado."
        )
    itens = [x for x in catalogo.values() if not uf or x["uf"] == uf]
    itens.sort(key=lambda x: x["codigo_ibge"])
    if limite:
        itens = itens[:limite]

    raiz.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    registros: list[dict] = []
    resumo = {
        "itens": 0,
        "publicados": 0,
        "falhas": 0,
        "pulados": 0,
        "reconstruidos": 0,
        "bytes": 0,
        "motivos": {},
    }

    # Retomada em tres camadas: sidecar por ativo (o mais recente), catalogo
    # agregado (traz o hash da origem) e, por ultimo, as renditions em disco.
    # Interromper a execucao nao custa nem download nem requisicao nova — e o
    # catalogo em disco pode estar atrasado em horas sem prejuizo.
    anterior = raiz / "catalogo.json"
    indice = indice_meta()
    # Rejeição é decisão registrada: não se republica por estar no catálogo
    # antigo nem por ter rendition no disco.
    rejeitados = {
        (item["codigo_ibge"], tipo)
        for item in catalogo.values()
        for tipo in ("brasao", "bandeira")
        if (item.get(tipo) or {}).get("rejeitado")
    }
    if anterior.exists():
        for reg in json.loads(anterior.read_text()):
            chave = (reg.get("codigo_ibge"), reg.get("tipo"))
            if reg.get("estado") != "publicado" or chave in rejeitados:
                continue
            atual = indice.get(chave)
            # O catalogo so vence quando traz o hash da origem e o sidecar nao:
            # um item reconstruido do disco (sha256_origem nulo) e atualizado
            # assim que aparece um catalogo com a procedencia completa.
            if atual is None or (atual.get("sha256_origem") is None and reg.get("sha256_origem")):
                indice[chave] = reg
                gravar_meta(reg)

    final: dict[tuple[str, str], dict] = dict(indice)
    for item in itens:
        for tipo in ("brasao", "bandeira"):
            if tipo not in item:
                continue
            chave = (item["codigo_ibge"], tipo)
            if chave in rejeitados:
                resumo["rejeitados"] = resumo.get("rejeitados", 0) + 1
                continue
            reg = None
            if (
                chave in indice
                and (raiz / "embed" / "v1" / tipo / f"{item['codigo_ibge']}.png").exists()
            ):
                reg = indice[chave]
                resumo["pulados"] += 1
            else:
                reg = registro_do_disco(item, tipo, raiz)
                if reg is not None:
                    gravar_meta(reg)
                    resumo["pulados"] += 1
                    resumo["reconstruidos"] += 1

            if reg is None:
                reg = publicar_item(item, tipo, raiz, esperado=indice.get(chave))
                if reg["estado"] == "publicado":
                    gravar_meta(reg)
                    resumo["publicados"] += 1
                else:
                    resumo["falhas"] += 1
                    motivo = (reg.get("erro") or "?").split(":")[0]
                    resumo["motivos"][motivo] = resumo["motivos"].get(motivo, 0) + 1

            registros.append(reg)
            final[chave] = reg
            resumo["itens"] += 1
            if reg.get("estado") == "publicado":
                resumo["bytes"] += sum(r["bytes"] for r in reg["rendicoes"].values())

            if resumo["itens"] % 100 == 0:
                print(
                    f"[{resumo['itens']}/{len(itens) * 2}] publicado {resumo['publicados']} "
                    f"| falhas {resumo['falhas']} | pulados {resumo['pulados']} "
                    f"| {resumo['bytes'] / 1024 / 1024:.0f} MB | {time.time() - inicio:.0f}s",
                    flush=True,
                )
            # Checkpoint: um kill perde no maximo 200 itens de catalogo, nunca
            # os arquivos (que ja estao em disco e nos sidecars).
            if resumo["itens"] % 200 == 0:
                gravar_catalogo(anterior, final)

    gravar_catalogo(anterior, final)
    resumo["no_catalogo"] = len(final)
    return resumo


def baixar_fontes(
    registros: list[dict],
    *,
    base: Path | None = None,
    raiz: Path | None = None,
    destino_catalogo: Path | None = None,
    limite: int = 0,
    uf: str | None = None,
) -> dict:
    """Rebaixa e arquiva o arquivo de origem dos itens ja publicados.

    Serve para a safra publicada antes de a fonte ser guardada. Confere o hash
    contra `sha256_origem`; divergencia vira `fonte_divergente` e o arquivo novo
    vai para `fontes/conflito/` — procedencia nao se corrige em silencio.
    """
    pasta = base or FONTES
    itens = [
        r for r in registros if r.get("estado") == "publicado" and (not uf or r.get("uf") == uf)
    ]
    itens.sort(key=lambda r: (r["codigo_ibge"], r["tipo"]))
    if limite:
        itens = itens[:limite]

    final: dict[tuple[str, str], dict] = {(r["codigo_ibge"], r["tipo"]): r for r in registros}

    resumo = {
        "itens": 0,
        "baixadas": 0,
        "puladas": 0,
        "divergentes": 0,
        "falhas": 0,
        "bytes": 0,
    }
    inicio = time.time()
    for reg in itens:
        resumo["itens"] += 1
        # No SVG o arquivo publicado e a fonte, byte a byte.
        if reg.get("formato_origem") == "svg":
            resumo["puladas"] += 1
            continue
        atual = caminho_fonte(reg.get("fonte"))
        if atual is not None and atual.exists():
            resumo["puladas"] += 1
            continue

        try:
            conteudo = baixar(reg["origem"])
        except Exception as exc:  # noqa: BLE001
            reg["fonte_erro"] = str(exc)[:160]
            resumo["falhas"] += 1
            continue

        obtido = sha256(conteudo)
        obtido1 = sha1(conteudo)
        esperado = reg.get("sha256_origem")
        mime = reg.get("formato_origem") or ""
        if esperado and esperado != obtido:
            conflito = guardar_fonte(
                pasta.parent / "conflito", reg["codigo_ibge"], reg["tipo"], mime, conteudo
            )
            reg["fonte_divergente"] = {
                "esperado": esperado,
                "obtido": obtido,
                "arquivo": _relativo(conflito),
            }
            resumo["divergentes"] += 1
        else:
            arquivo = guardar_fonte(pasta, reg["codigo_ibge"], reg["tipo"], mime, conteudo)
            reg["fonte"] = {
                "arquivo": _relativo(arquivo),
                "bytes": len(conteudo),
                "sha256": obtido,
                "sha1": obtido1,
            }
            reg["sha256_origem"] = obtido
            reg["sha1_origem"] = obtido1
            reg["bytes_origem"] = len(conteudo)
            if not esperado:
                # Item reconstruido do disco: o hash so existe a partir de agora.
                reg["origem_reverificada"] = True
            resumo["baixadas"] += 1
            resumo["bytes"] += len(conteudo)

        reg["guarda"] = guarda.classificar(reg)
        if raiz is not None:
            gravar_meta(reg)
        if resumo["itens"] % 50 == 0:
            if destino_catalogo is not None:
                gravar_catalogo(destino_catalogo, final)
            print(
                f"[{resumo['itens']}/{len(itens)}] {resumo['baixadas']} fontes "
                f"| {resumo['bytes'] / 1024 / 1024:.0f} MB | {time.time() - inicio:.0f}s",
                flush=True,
            )

    if destino_catalogo is not None:
        gravar_catalogo(destino_catalogo, final)
    return resumo
