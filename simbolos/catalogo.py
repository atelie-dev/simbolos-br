"""Catalogo IBGE: estados e municipios, com slug e nome normalizado."""

from __future__ import annotations

import json
import time

import httpx

from . import DATA, UFS, USER_AGENT
from .nomes import normalizar, slug

IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades"
ESTADOS = DATA / "estados.json"
MUNICIPIOS = DATA / "municipios.json"


def _get(url: str, tentativas: int = 4) -> object:
    ultimo: Exception | None = None
    for i in range(tentativas):
        try:
            r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=45.0)
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"falhou: {url}") from ultimo


def construir() -> tuple[list[dict], list[dict]]:
    estados: list[dict] = []
    municipios: list[dict] = []

    brutos = {e["sigla"]: e for e in _get(f"{IBGE}/estados?orderBy=nome")}

    for uf in UFS:
        info = brutos[uf]
        estados.append(
            {
                "codigo": str(info["id"]),
                "uf": uf,
                "nome": info["nome"],
                "slug": slug(info["nome"]),
                "regiao": (info.get("regiao") or {}).get("nome"),
            }
        )

        for m in _get(f"{IBGE}/estados/{uf}/municipios"):
            nome = m["nome"]
            municipios.append(
                {
                    "codigo": str(m["id"]),
                    "uf": uf,
                    "nome": nome,
                    "slug": slug(nome),
                    "nome_norm": normalizar(nome),
                }
            )
        print(f"  {uf}: {len(municipios)} acumulados", flush=True)
        time.sleep(0.25)

    municipios.sort(key=lambda m: (m["uf"], m["nome"]))
    return estados, municipios


def carregar(uf: str | None = None) -> list[dict]:
    municipios = json.loads(MUNICIPIOS.read_text())
    if uf:
        return [m for m in municipios if m["uf"] == uf]
    return municipios


def por_codigo() -> dict[str, dict]:
    return {m["codigo"]: m for m in carregar()}


def escrever() -> tuple[int, int]:
    estados, municipios = construir()
    DATA.mkdir(parents=True, exist_ok=True)
    ESTADOS.write_text(json.dumps(estados, ensure_ascii=False, indent=1) + "\n")
    MUNICIPIOS.write_text(json.dumps(municipios, ensure_ascii=False, indent=1) + "\n")
    return len(estados), len(municipios)


if __name__ == "__main__":
    e, m = escrever()
    print(f"{e} estados, {m} municipios -> {DATA}")
