"""Cliente LLM (Maritaca/DeepSeek/GLM) com chamada robusta, custo e extracao citada."""

from __future__ import annotations

import html as html_mod
import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from . import provedores

MODELO_FALLBACK = "sabia-4"

# Orcamento de saida: o S5 cobra raciocinio como saida e, com teto curto, devolve
# `content: null` e `finish_reason: "length"`. Piso alto evita truncar; o custo
# real e por token gerado, nao por token reservado.
MAX_TOKENS_PADRAO = 8000
MAX_TOKENS_TETO = 24000

PROMPT_EXTRACAO = """Você recebe o HTML de uma página de prefeitura municipal brasileira.

Responda SOMENTE um objeto JSON, sem texto fora dele:
{"tem_simbolo": true|false,
 "tipo": "brasao"|"bandeira"|null,
 "url_ativo": "string ou null",
 "ato_oficial": "string ou null",
 "trecho_que_prova": "string ou null",
 "confianca": 0.0-1.0}

Regras obrigatórias:
1. url_ativo só pode conter uma URL que exista literalmente no HTML recebido.
2. trecho_que_prova deve ser copiado literalmente do HTML, sem reescrever.
3. ato_oficial (lei/decreto que instituiu) só se estiver escrito no HTML.
4. Se não houver brasão ou bandeira, responda tem_simbolo=false e url_ativo=null.
5. NUNCA invente URL, lei, data ou autor. Não saber é resposta válida.
6. "Brasil", "brasileiro" e logotipo de prefeitura NÃO são brasão municipal."""

PROMPT_ATO = """Você recebe o texto de uma página ou documento de uma prefeitura.

Responda SOMENTE JSON:
{"tem_ato": true|false,
 "ato": "string ou null",
 "data": "string ou null",
 "url_pdf": "string ou null",
 "trecho_que_prova": "string ou null",
 "confianca": 0.0-1.0}

Objetivo: achar a lei, decreto ou resolução que INSTITUIU o brasão ou a bandeira
do município (não a que alterou depois, não a que criou a marca da gestão).

Regras:
1. "ato" copiado como está no texto (ex.: "Lei nº 264, de 10 de junho de 1959").
2. "url_pdf" só se houver um link literal para PDF no documento.
3. "trecho_que_prova" copiado literalmente.
4. Se não houver, tem_ato=false. Não invente número, data ou link."""

_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_ESPACO = re.compile(r"\s+")


class ErroLLM(RuntimeError):
    """Falha de configuracao ou de API."""


@dataclass
class Resposta:
    conteudo: str
    modelo: str
    provedor: str
    finish_reason: str | None
    entrada: int
    saida: int
    cache: int
    tentativas: int
    reasoning: int = 0
    custo_reportado: float | None = None
    restante: float | None = None
    service_tier: str | None = None
    fallback: bool = False

    @property
    def moeda(self) -> str | None:
        return provedores.obter(self.provedor).moeda if self.custo is not None else None

    @property
    def custo(self) -> float | None:
        """Prefere o custo que o provedor reportou; senão estima pela tabela."""
        if self.custo_reportado is not None:
            return self.custo_reportado
        return provedores.obter(self.provedor).custo(
            self.entrada,
            self.saida,
            cache=self.cache,
            tier=self.service_tier,
            modelo=self.modelo,
        )

    def json(self) -> dict[str, Any] | None:
        achado = re.search(r"\{.*\}", self.conteudo, re.DOTALL)
        if not achado:
            return None
        try:
            return json.loads(achado.group(0))
        except json.JSONDecodeError:
            return None


def _chave(provedor: str) -> str:
    p = provedores.obter(provedor)
    valor = p.chave()
    if not valor:
        raise ErroLLM(
            f"{p.env} ausente para o provedor '{p.nome}'. Materialize o ambiente "
            "do 1Password num .env fora do repo e carregue antes de rodar."
        )
    return valor


def _headers(provedor: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_chave(provedor)}",
        "Content-Type": "application/json",
    }


def _post_llm(url: str, cabecalhos: dict, corpo: dict, *, timeout: float) -> httpx.Response:
    """POST com retry exponencial em 429 (flex tier enfileira e pode recusar)."""
    for tentativa in range(6):
        r = httpx.post(url, headers=cabecalhos, json=corpo, timeout=timeout)
        if r.status_code != 429 or tentativa == 5:
            return r
        time.sleep(min(2**tentativa, 30) + random.random())
    return r


def chamar(
    mensagens: list[dict],
    *,
    provedor: str = provedores.PADRAO,
    modelo: str | None = None,
    max_tokens: int = MAX_TOKENS_PADRAO,
    tentativas: int = 3,
    flex: bool = False,
    timeout: float = 300.0,
) -> Resposta:
    """Chama o modelo; se voltar vazio ou truncado, dobra o orcamento e repete.

    `flex=True` usa a fila: no Neuralwatt é o sufixo `-flex`; na Maritaca é
    `service_tier: "flex"` (50%, com 429 possível). Se o modelo não tiver a
    variante, volta para o normal em vez de falhar.
    """
    p = provedores.obter(provedor)
    modelo = modelo or p.modelo
    if flex and not p.usa_service_tier:
        modelo = p.com_flex(modelo)
    limite = max_tokens
    for tentativa in range(1, tentativas + 1):
        corpo = {"model": modelo, "messages": mensagens, "max_tokens": limite}
        if flex and p.usa_service_tier:
            corpo["service_tier"] = "flex"
        r = _post_llm(p.chat, _headers(p.nome), corpo, timeout=timeout)
        if r.status_code in (400, 404) and modelo.endswith("-flex"):
            # Modelo sem variante de fila: volta para o normal.
            modelo = modelo.removesuffix("-flex")
            r = _post_llm(
                p.chat,
                _headers(p.nome),
                {"model": modelo, "messages": mensagens, "max_tokens": limite},
                timeout=timeout,
            )
        if r.status_code != 200:
            raise ErroLLM(f"{p.nome} HTTP {r.status_code}: {r.text[:400]}")
        d = r.json()
        escolha = d["choices"][0]
        conteudo = (escolha["message"].get("content") or "").strip()
        uso = d.get("usage") or {}
        detalhes_entrada = uso.get("prompt_tokens_details") or {}
        detalhes_saida = uso.get("completion_tokens_details") or {}
        custo_api = d.get("cost") or {}
        reportado = custo_api.get("request_cost_usd")
        if reportado is None:
            reportado = custo_api.get("request_cost")
        resp = Resposta(
            conteudo=conteudo,
            modelo=modelo,
            provedor=p.nome,
            finish_reason=escolha.get("finish_reason"),
            entrada=int(uso.get("prompt_tokens") or 0),
            saida=int(uso.get("completion_tokens") or 0),
            cache=int(uso.get("cached_tokens") or detalhes_entrada.get("cached_tokens") or 0),
            tentativas=tentativa,
            reasoning=int(detalhes_saida.get("reasoning_tokens") or 0),
            custo_reportado=float(reportado) if reportado is not None else None,
            restante=custo_api.get("allowance_remaining_usd"),
            service_tier=d.get("service_tier"),
        )
        if conteudo:
            return resp
        limite = min(limite * 2, MAX_TOKENS_TETO)

    if p.nome == "maritaca" and modelo != MODELO_FALLBACK:
        alternativo = chamar(
            mensagens,
            provedor="maritaca",
            modelo=MODELO_FALLBACK,
            max_tokens=max_tokens,
            tentativas=1,
            timeout=timeout,
        )
        alternativo.fallback = True
        return alternativo

    raise ErroLLM(f"{modelo} nao devolveu conteudo apos {tentativas} tentativas")


def chamar_json(
    mensagens: list[dict],
    *,
    provedor: str = provedores.PADRAO,
    modelo: str | None = None,
    max_tokens: int = MAX_TOKENS_PADRAO,
    flex: bool = False,
    timeout: float = 300.0,
) -> tuple[dict, Resposta]:
    """Chama e exige JSON valido. Reforca orcamento e, se preciso, troca de modelo."""
    resp = chamar(
        mensagens,
        provedor=provedor,
        modelo=modelo,
        max_tokens=max_tokens,
        flex=flex,
        timeout=timeout,
    )
    for _ in range(2):
        dados = resp.json()
        if dados is not None:
            return dados, resp
        max_tokens = min(max_tokens * 2, MAX_TOKENS_TETO)
        resp = chamar(
            mensagens,
            provedor=provedor,
            modelo=modelo,
            max_tokens=max_tokens,
            flex=flex,
            timeout=timeout,
        )

    if provedor == "maritaca" and modelo != MODELO_FALLBACK:
        resp = chamar(
            mensagens,
            provedor="maritaca",
            modelo=MODELO_FALLBACK,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        resp.fallback = True
        dados = resp.json()
        if dados is not None:
            return dados, resp

    raise ErroLLM(f"{resposta_nome(provedor, modelo)} sem JSON valido: {resp.conteudo[:200]}")


def resposta_nome(provedor: str, modelo: str | None) -> str:
    return f"{provedor}/{modelo or provedores.obter(provedor).modelo}"


def modelos(provedor: str = provedores.PADRAO) -> list[dict]:
    p = provedores.obter(provedor)
    r = httpx.get(p.modelos, headers=_headers(p.nome), timeout=60.0)
    r.raise_for_status()
    return r.json().get("data", [])


def saldo(provedor: str = provedores.PADRAO) -> dict:
    """Saldo normalizado: Maritaca em BRL, Neuralwatt em USD."""
    p = provedores.obter(provedor)
    if p.nome == "maritaca":
        r = httpx.get(f"{p.base}/billing/usage", headers=_headers(p.nome), timeout=60.0)
        r.raise_for_status()
        d = r.json()
        return {
            "provedor": p.nome,
            "moeda": "BRL",
            "saldo": d.get("balance", 0.0),
            "periodo": d.get("period"),
            "uso": d.get("usage") or {},
        }
    if p.nome == "neuralwatt":
        r = httpx.get(f"{p.base}/billing/balance", headers=_headers(p.nome), timeout=60.0)
        r.raise_for_status()
        d = r.json()
        return {
            "provedor": p.nome,
            "moeda": "USD",
            "saldo": d.get("dollar_balance", 0.0),
            "periodo": None,
            "uso": {},
        }
    raise ErroLLM(f"saldo nao implementado para {p.nome}")


def limpar_html(html: str) -> str:
    html = _SCRIPT.sub(" ", html)
    html = _COMENTARIO.sub(" ", html)
    return _compactar(html)


def _compactar(texto: str) -> str:
    return _ESPACO.sub(" ", texto).strip()


def _presente(agulha: str | None, palheiro: str) -> bool:
    """O trecho citado existe mesmo? Tolera entidades HTML e tags."""
    if not agulha:
        return False
    alvo = _compactar(agulha)
    for variante in (alvo, _compactar(html_mod.unescape(alvo)), _compactar(_TAG.sub(" ", alvo))):
        if variante and variante in palheiro:
            return True
    return False


def _uso(resp: Resposta) -> dict:
    return {
        "entrada": resp.entrada,
        "saida": resp.saida,
        "cache": resp.cache,
        "reasoning": resp.reasoning,
        "custo": resp.custo,
        "moeda": resp.moeda,
        "custo_brl": resp.custo if resp.moeda == "BRL" else None,
        "service_tier": resp.service_tier,
        "restante": resp.restante,
        "tentativas": resp.tentativas,
        "fallback": resp.fallback,
        "finish_reason": resp.finish_reason,
        "provedor": resp.provedor,
        "modelo": resp.modelo,
    }


def formatar_custo(resp: Resposta) -> str:
    if resp.custo is None:
        return "custo a confirmar"
    prefixo = {"BRL": "R$ ", "USD": "US$ ", "CNY": "CN¥ "}.get(resp.moeda or "", "")
    return f"{prefixo}{resp.custo:.6f}"


def extrair(
    html: str,
    url_base: str,
    *,
    provedor: str | None = None,
    modelo: str | None = None,
    max_tokens: int = MAX_TOKENS_PADRAO,
    flex: bool = False,
) -> dict:
    """Extracao do simbolo com citacao obrigatoria e verificada.

    `aceito` so e True quando ha URL + citação literal no HTML. Nao e sugestao:
    e o portao que impede alucinacao de virar dado.
    """
    provedor, modelo = provedores.resolver_extracao(provedor, modelo)
    corpo = limpar_html(html)
    try:
        dados, resp = chamar_json(
            [
                {"role": "system", "content": PROMPT_EXTRACAO},
                {"role": "user", "content": "HTML da pagina:\n\n" + corpo},
            ],
            provedor=provedor,
            modelo=modelo,
            max_tokens=max_tokens,
            flex=flex,
        )
    except ErroLLM as exc:
        return {
            "encontrado": False,
            "erro": str(exc)[:300],
            "provedor": provedor,
            "modelo": modelo,
        }

    url = dados.get("url_ativo")
    if url:
        url = urljoin(url_base, str(url).strip())

    trecho = dados.get("trecho_que_prova")
    cita_ok = _presente(trecho, corpo)
    ato = dados.get("ato_oficial") or None
    ato_ok = _presente(ato, corpo) if ato else False

    return {
        "encontrado": bool(dados.get("tem_simbolo")) and bool(url),
        "tipo": dados.get("tipo"),
        "url_ativo": url,
        "ato_oficial": ato if ato_ok else None,
        "ato_verificado": ato_ok,
        "trecho": trecho if cita_ok else None,
        "citacao_verificada": cita_ok,
        "confianca": dados.get("confianca"),
        "aceito": bool(dados.get("tem_simbolo")) and bool(url) and cita_ok,
        "uso": _uso(resp),
    }


def achar_ato(
    texto: str,
    url_base: str,
    *,
    provedor: str | None = None,
    modelo: str | None = None,
    max_tokens: int = MAX_TOKENS_PADRAO,
    flex: bool = False,
) -> dict:
    """Acha a lei/decreto que instituiu o simbolo, com citacao verificada."""
    provedor, modelo = provedores.resolver_extracao(provedor, modelo)
    corpo = _compactar(texto)
    try:
        dados, resp = chamar_json(
            [
                {"role": "system", "content": PROMPT_ATO},
                {"role": "user", "content": "Texto do documento:\n\n" + corpo},
            ],
            provedor=provedor,
            modelo=modelo,
            max_tokens=max_tokens,
            flex=flex,
        )
    except ErroLLM as exc:
        return {"tem_ato": False, "erro": str(exc)[:300], "uso": None}

    trecho = dados.get("trecho_que_prova")
    cita_ok = _presente(trecho, corpo)
    ato = dados.get("ato") or None
    return {
        "tem_ato": bool(dados.get("tem_ato")) and cita_ok,
        "ato": ato if cita_ok else None,
        "data": dados.get("data") if cita_ok else None,
        "url_pdf": urljoin(url_base, str(dados["url_pdf"]).strip())
        if dados.get("url_pdf")
        else None,
        "trecho": trecho if cita_ok else None,
        "citacao_verificada": cita_ok,
        "aceito": bool(dados.get("tem_ato")) and cita_ok,
        "uso": _uso(resp),
    }
