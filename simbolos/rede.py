"""Requisições HTTP com polidez: intervalo por host, recuo e `Retry-After`.

Wikimedia responde 429 quando o bot acelera; um site de prefeitura responde 403
e bloqueia o IP. As duas coisas se resolvem do mesmo jeito: uma requisição por
vez por host, com espera entre elas, e recuo quando o servidor pede.

A política é por **host**, não global: seis prefeituras diferentes em paralelo
não incomodam ninguém; seis requisições no mesmo servidor, sim.
"""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import httpx

from . import USER_AGENT

TIMEOUT = 90.0
TENTATIVAS = 4

INTERVALO = {
    "upload.wikimedia.org": 1.0,
    "commons.wikimedia.org": 0.5,
}
# Site de prefeitura: 1 req/s. É mais lento que o necessário na maioria dos
# casos, e é o que evita o bloqueio nos poucos que têm WAF.
INTERVALO_PADRAO = 1.0

_ultimo: dict[str, float] = {}
_trava = threading.Lock()


def esperar(host: str, intervalo: float | None = None) -> None:
    """Bloqueia até o host estar livre de novo."""
    pausa = INTERVALO.get(host, INTERVALO_PADRAO) if intervalo is None else intervalo
    with _trava:
        agora = time.time()
        alvo = _ultimo.get(host, 0.0) + pausa
        espera = max(0.0, alvo - agora)
        _ultimo[host] = max(agora, alvo)
    if espera:
        time.sleep(espera)


def _espera_do_recuo(resposta: httpx.Response, tentativa: int) -> float:
    bruto = resposta.headers.get("retry-after")
    if bruto and bruto.isdigit():
        return min(float(bruto), 60.0)
    return min(2.0 ** (tentativa + 1), 30.0)


def requisitar(
    url: str,
    *,
    tentativas: int = TENTATIVAS,
    timeout: float = TIMEOUT,
    intervalo: float | None = None,
) -> httpx.Response:
    """GET com polidez por host. Devolve a resposta e **não** levanta por status.

    Quem decide o que fazer com 404 é o chamador: `robots.txt` ausente e arquivo
    ausente significam coisas diferentes.
    """
    host = urlparse(url).hostname or ""
    ultimo: Exception | None = None
    for i in range(tentativas):
        esperar(host, intervalo)
        try:
            resposta = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                follow_redirects=True,
            )
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
            time.sleep(min(2.0 ** (i + 1), 20.0))
            continue
        if resposta.status_code in (429, 503):
            time.sleep(_espera_do_recuo(resposta, i))
            ultimo = RuntimeError(f"HTTP {resposta.status_code}")
            continue
        return resposta
    raise RuntimeError(f"{url}: falhou apos {tentativas} tentativas ({ultimo})")


def baixar(url: str, *, tentativas: int = TENTATIVAS) -> bytes:
    """GET que exige sucesso: é o que a publicação precisa."""
    resposta = requisitar(url, tentativas=tentativas)
    resposta.raise_for_status()
    return resposta.content
