"""PIX: valida o BR Code, gera o QR no build e publica os campos.

O QR é gerado aqui, não em serviço de terceiro: a página não faz requisição a
ninguém para mostrar a imagem, e o código nunca passa por um servidor alheio.

O BR Code fica em ``data/pix.json``; o comando ``simbolos pix --codigo ...``
valida o CRC, reescreve o arquivo e regenera o SVG.
"""

from __future__ import annotations

import json

import segno

from . import DATA

ORIGEM = DATA / "pix.json"
QR = DATA.parent / "site" / "public" / "pix-qr.svg"
DADOS = DATA.parent / "site" / "src" / "data" / "pix.json"


def crc16(payload: str) -> str:
    """CRC16/CCITT-FALSE: poly 0x1021, init 0xFFFF, sem reflexão."""
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def campos(texto: str) -> list[tuple[str, str]]:
    """Percorre os TLVs do BR Code (2 dígitos de id, 2 de tamanho)."""
    saida: list[tuple[str, str]] = []
    i = 0
    while i < len(texto):
        ident = texto[i : i + 2]
        tamanho = int(texto[i + 2 : i + 4])
        valor = texto[i + 4 : i + 4 + tamanho]
        saida.append((ident, valor))
        i += 4 + tamanho
    return saida


def validar(codigo: str) -> dict:
    codigo = codigo.strip()
    corpo, informado = codigo[:-4], codigo[-4:]
    calculado = crc16(corpo)
    topo = campos(codigo)
    conta = next((v for k, v in topo if k == "26"), "")
    pix = dict(campos(conta))
    return {
        "ok": calculado == informado,
        "crc": informado,
        "chave": pix.get("01"),
        "nome": next((v for k, v in topo if k == "59"), ""),
        "cidade": next((v for k, v in topo if k == "60"), ""),
        "valor": next((v for k, v in topo if k == "54"), ""),
        "txid": next((v for k, v in topo if k == "62"), ""),
    }


def registrar(codigo: str) -> dict:
    """Valida e grava o código em data/pix.json (falha alto se o CRC não fecha)."""
    # Só quebra de linha e espaço nas pontas: espaço interno do nome e da cidade
    # é conteúdo, e o tamanho do campo conta com ele.
    codigo = "".join(codigo.splitlines()).strip()
    dados = validar(codigo)
    if not dados["ok"]:
        raise SystemExit(f"CRC invalido: informado {dados['crc']}, calculado {crc16(codigo[:-4])}")
    ORIGEM.write_text(json.dumps({"codigo": codigo, **dados}, ensure_ascii=False, indent=1) + "\n")
    return gerar()


def gerar() -> dict:
    if not ORIGEM.exists():
        raise SystemExit("sem data/pix.json: rode `simbolos pix --codigo ...`")
    dados = json.loads(ORIGEM.read_text())
    codigo = dados["codigo"]
    if not validar(codigo)["ok"]:
        raise SystemExit("CRC de data/pix.json nao confere; regenere o codigo")

    QR.parent.mkdir(parents=True, exist_ok=True)
    segno.make(codigo, error="m").save(
        QR, kind="svg", scale=6, border=2, dark="#241c17", light="#ffffff"
    )
    DADOS.parent.mkdir(parents=True, exist_ok=True)
    DADOS.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n")
    return {**dados, "bytes_qr": QR.stat().st_size}
