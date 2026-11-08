"""Monta a árvore que vai para o Cloudflare Pages.

Um único projeto serve o domínio: o portal na raiz e o acervo em `/simbolos`.
Isso porque o Pages publica na raiz do domínio — não existe "montar em
subcaminho". Duas árvores separadas exigiriam um Worker roteando.

    python scripts/empacotar_site.py
    wrangler pages deploy deploy --project-name coletivo --branch main
"""

from __future__ import annotations

import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PORTAL = RAIZ / "portal"
SITE = RAIZ / "site" / "dist"
DESTINO = RAIZ / "deploy"

LIMITE_ARQUIVOS = 20_000  # Cloudflare Pages, plano Free


def montar(destino: Path = DESTINO) -> dict:
    if not SITE.exists():
        raise SystemExit("site/dist nao existe: rode `npm run build` em site/")
    if not (SITE / "api" / "v1" / "resumo.json").exists():
        raise SystemExit("falta o indice: rode `simbolos indice` antes do build")

    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir()

    for arq in PORTAL.iterdir():
        if arq.is_file():
            shutil.copy2(arq, destino / arq.name)

    shutil.copytree(SITE, destino / "simbolos")

    arquivos = [p for p in destino.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in arquivos)
    resumo = {
        "arquivos": len(arquivos),
        "mb": round(total / 1024 / 1024, 1),
        "limite": LIMITE_ARQUIVOS,
        "folga_pct": round(100 * len(arquivos) / LIMITE_ARQUIVOS, 1),
    }
    if len(arquivos) > LIMITE_ARQUIVOS:
        raise SystemExit(
            f"{len(arquivos)} arquivos passam do limite de {LIMITE_ARQUIVOS} do Pages Free"
        )
    return resumo


if __name__ == "__main__":
    r = montar()
    print(f"arquivos: {r['arquivos']} de {r['limite']} ({r['folga_pct']}% do limite)")
    print(f"tamanho:  {r['mb']} MB")
    print(f"-> {DESTINO}/ (index.html + simbolos/)")
