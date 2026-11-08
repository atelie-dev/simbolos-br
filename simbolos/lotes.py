"""Batch da Maritaca (formato OpenAI): metade do preço, latência irrelevante.

Fluxo: montar JSONL -> POST /files -> POST /batches -> polling -> GET
/files/{output}/content. Cada linha de saída é pareada de volta com a página
original pelo `custom_id`, e a citação é verificada no HTML guardado.
"""

from __future__ import annotations

import json
import time
import uuid

import httpx

from . import maritaca, provedores

ENDPOINT = "/v1/chat/completions"
JANELA = "24h"


def _cabecalhos() -> dict[str, str]:
    p = provedores.obter("maritaca")
    return {"Authorization": f"Bearer {maritaca._chave(p.nome)}"}


def montar(
    itens: list[tuple[str, str]],
    *,
    modelo: str = "S5",
    max_tokens: int = maritaca.MAX_TOKENS_PADRAO,
) -> bytes:
    """(custom_id, html) -> JSONL de requisições de chat."""
    linhas = []
    for custom_id, html in itens:
        linhas.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": ENDPOINT,
                "body": {
                    "model": modelo,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": maritaca.PROMPT_EXTRACAO},
                        {
                            "role": "user",
                            "content": "HTML da pagina:\n\n" + maritaca.limpar_html(html),
                        },
                    ],
                },
            }
        )
    return ("\n".join(json.dumps(x, ensure_ascii=False) for x in linhas) + "\n").encode()


def subir(conteudo: bytes, nome: str = "lote.jsonl") -> dict:
    p = provedores.obter("maritaca")
    r = httpx.post(
        f"{p.base}/files",
        headers=_cabecalhos(),
        files={"file": (nome, conteudo, "application/jsonl")},
        data={"purpose": "batch"},
        timeout=180.0,
    )
    r.raise_for_status()
    return r.json()


def criar(file_id: str, *, janela: str = JANELA) -> dict:
    p = provedores.obter("maritaca")
    r = httpx.post(
        f"{p.base}/batches",
        headers={**_cabecalhos(), "Content-Type": "application/json"},
        json={"input_file_id": file_id, "endpoint": ENDPOINT, "completion_window": janela},
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()


def estado(batch_id: str) -> dict:
    p = provedores.obter("maritaca")
    r = httpx.get(f"{p.base}/batches/{batch_id}", headers=_cabecalhos(), timeout=60.0)
    r.raise_for_status()
    return r.json()


def baixar(file_id: str) -> list[dict]:
    p = provedores.obter("maritaca")
    r = httpx.get(f"{p.base}/files/{file_id}/content", headers=_cabecalhos(), timeout=180.0)
    r.raise_for_status()
    saida = []
    for linha in r.text.splitlines():
        if linha.strip():
            saida.append(json.loads(linha))
    return saida


def esperar(batch_id: str, *, timeout: float = 1800.0, intervalo: float = 15.0) -> dict:
    """Polling com prazo. Devolve o último estado, completo ou não."""
    inicio = time.time()
    while True:
        e = estado(batch_id)
        if e.get("status") in ("completed", "failed", "cancelled", "expired"):
            return e
        if time.time() - inicio > timeout:
            e["_timeout"] = True
            return e
        time.sleep(intervalo)


def verificar_linha(linha: dict, html: str) -> dict:
    """Transforma uma linha de resultado no mesmo formato de `extrair`."""
    resposta = linha.get("response") or {}
    corpo = resposta.get("body") or {}
    escolhas = corpo.get("choices") or []
    if not escolhas:
        return {
            "encontrado": False,
            "erro": (linha.get("error") or {}).get("message", "sem choices"),
            "aceito": False,
        }

    texto = escolhas[0]["message"].get("content") or ""
    achado = texto[texto.find("{") : texto.rfind("}") + 1]
    try:
        dados = json.loads(achado)
    except json.JSONDecodeError:
        return {"encontrado": False, "erro": "sem JSON", "bruto": texto[:200], "aceito": False}

    corpo_html = maritaca.limpar_html(html)
    trecho = dados.get("trecho_que_prova")
    cita_ok = maritaca._presente(trecho, corpo_html)
    ato = dados.get("ato_oficial") or None
    ato_ok = maritaca._presente(ato, corpo_html) if ato else False
    return {
        "encontrado": bool(dados.get("tem_simbolo")) and bool(dados.get("url_ativo")),
        "tipo": dados.get("tipo"),
        "url_ativo": dados.get("url_ativo"),
        "ato_oficial": ato if ato_ok else None,
        "ato_verificado": ato_ok,
        "trecho": trecho if cita_ok else None,
        "citacao_verificada": cita_ok,
        "confianca": dados.get("confianca"),
        "aceito": bool(dados.get("tem_simbolo")) and bool(dados.get("url_ativo")) and cita_ok,
        "uso": {
            "entrada": (corpo.get("usage") or {}).get("prompt_tokens"),
            "saida": (corpo.get("usage") or {}).get("completion_tokens"),
        },
    }


def executar(
    paginas: list[tuple[str, str]],
    *,
    modelo: str = "S5",
    timeout: float = 1800.0,
    apenas_enviar: bool = False,
) -> dict:
    """Orquestra: sobe, cria, espera, baixa e verifica. `paginas` = (url, html)."""
    itens = [(f"p{i}", html) for i, (_url, html) in enumerate(paginas)]
    por_id = {f"p{i}": url for i, (url, _html) in enumerate(paginas)}
    html_por_id = {f"p{i}": html for i, (_url, html) in enumerate(paginas)}

    arquivo = subir(montar(itens, modelo=modelo), f"simbolos-{uuid.uuid4().hex[:8]}.jsonl")
    lote = criar(arquivo["id"])
    resultado = {
        "modelo": modelo,
        "file_id": arquivo["id"],
        "batch_id": lote["id"],
        "paginas": len(paginas),
        "status": lote.get("status"),
        "resultados": [],
    }
    if apenas_enviar:
        return resultado

    final = esperar(lote["id"], timeout=timeout)
    resultado["status"] = final.get("status")
    resultado["timeout"] = bool(final.get("_timeout"))
    if final.get("output_file_id"):
        for linha in baixar(final["output_file_id"]):
            cid = linha.get("custom_id")
            item = verificar_linha(linha, html_por_id.get(cid, ""))
            item["url"] = por_id.get(cid)
            resultado["resultados"].append(item)
    return resultado
