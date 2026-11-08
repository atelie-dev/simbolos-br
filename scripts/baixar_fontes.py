"""Baixa as fontes variáveis do Google Fonts para o site (uma vez, versionadas).

Autohospedar evita requisição a terceiros na página e garante que o acervo não
dependa da disponibilidade de um CDN alheio.
"""

import re
from pathlib import Path

import httpx

DESTINO = Path(__file__).resolve().parents[1] / "site" / "public" / "fonts"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"

FAMILIAS = {
    "bricolage-grotesque": "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400..800&display=swap",
    "source-sans-3": "https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300..700&display=swap",
}


def baixar() -> dict[str, int]:
    DESTINO.mkdir(parents=True, exist_ok=True)
    tamanhos = {}
    for nome, url in FAMILIAS.items():
        css = httpx.get(url, headers={"User-Agent": UA}, timeout=30).text
        # o último bloco do CSS é o do alfabeto latino
        blocos = re.findall(r"src:\s*url\((https://[^)]+\.woff2)\)", css)
        if not blocos:
            raise RuntimeError(f"sem woff2 no CSS de {nome}")
        arquivo = DESTINO / f"{nome}.woff2"
        conteudo = httpx.get(blocos[-1], timeout=60).content
        arquivo.write_bytes(conteudo)
        tamanhos[nome] = len(conteudo)
    return tamanhos


if __name__ == "__main__":
    for nome, tamanho in baixar().items():
        print(f"{nome}: {tamanho / 1024:.0f} KB")
