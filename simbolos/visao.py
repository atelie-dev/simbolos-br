"""Verificacao visual de candidatos: brasao, bandeira, logo ou outro.

Resolve o ponto mais fraco do acervo: milhares de candidatos e nenhum jeito
automatico de saber se a imagem e o simbolo certo. dHash acha duplicata; nao
acha erro.
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageStat

from . import USER_AGENT, provedores

PROVEDOR_VISAO = "neuralwatt"
MODELO_VISAO = "deepseek-v4.1-flash"
MODELO_DECISAO = "clef-flash"
# O prompt é dado, não código: versione para poder comparar no conjunto rotulado.
PERGUNTAS_VERSAO = 2
SISTEMAONE = "/systemone"

# Classificador discriminativo: uma passada, sem tokens de saída, com
# probabilidades. É o formato certo para "isto é brasão?".
PERGUNTAS = {
    "tipo": {
        "type": "choice",
        "instructions": (
            "Classifique a imagem. Se houver pano, campo retangular ou faixa de tecido, "
            "responda bandeira — mesmo que o escudo esteja ao centro e em destaque. "
            "O escudo dentro do pano não faz da imagem um brasão."
        ),
        "criteria": {
            "brasao": "Escudo/heráldica municipal isolado, com ou sem coroa mural, suportes e listel.",
            "bandeira": "Pano ou pavilhão, geralmente retangular, com campo e símbolo ao centro.",
            "logo": "Marca gráfica, tipografia, slogan ou ícone institucional; não é o brasão.",
            "outro": "Foto, mapa, documento, pessoa, ícone de interface ou outra coisa.",
        },
    },
    "tem_marca_dagua": {
        "type": "noul",
        "instructions": (
            "Há texto, selo, prêmio, indicador ou logo que não faz parte da arte — "
            "sobreposto a ela OU ao lado dela no mesmo arquivo?"
        ),
    },
    "fundo_limpo": {
        "type": "noul",
        "instructions": "A arte está isolada em fundo branco ou transparente, sem foto atrás?",
    },
}

PROMPT = """Você analisa imagens de símbolos municipais brasileiros.

Responda SOMENTE JSON:
{"tipo": "brasao"|"bandeira"|"logo"|"outro",
 "municipio": "nome visível na arte ou null",
 "tem_listel": true|false,
 "marca_dagua": true|false,
 "fundo": "limpo"|"foto"|"documento"|"outro",
 "descricao": "uma linha",
 "confianca": 0.0-1.0}

Critérios:
- brasao: escudo/heráldica, com ou sem coroa mural, suportes e listel.
- bandeira: pano/pavilhão, geralmente retangular com campo e símbolo ao centro.
- logo: marca gráfica, tipografia, slogan, ícone institucional — NÃO é o brasão.
- Se for brasão desenhado sobre foto ou mockup, responda "brasao" mas diga na descrição.
- marca_dagua: true se houver texto/selo/logo sobreposto que não faz parte da arte (watermark, "MB!", crédito, textura de banco de imagem).
- fundo: "limpo" se a arte está isolada em fundo branco/transparente; "foto" se está sobre fotografia ou mockup; "documento" se é página escaneada."""

_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def data_url(conteudo: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(conteudo).decode()}"


def sinais(conteudo: bytes) -> dict:
    """Medidas determinísticas da imagem, antes de qualquer modelo.

    Pega o que modelo nenhum pegou no teste: arquivo em branco. E dá a menor
    dimensão, que é o piso de qualidade para servir em 512 px.
    """
    try:
        im = Image.open(BytesIO(conteudo))
        im.load()
    except Exception as exc:  # noqa: BLE001
        return {"erro": f"imagem ilegivel: {exc}"[:160]}
    largura, altura = im.size
    cinza = im.convert("L")
    desvio = ImageStat.Stat(cinza).stddev[0]
    return {
        "largura": largura,
        "altura": altura,
        "min_lado": min(largura, altura),
        "brilho_medio": round(ImageStat.Stat(cinza).mean[0], 1),
        "desvio": round(desvio, 2),
        "vazia": desvio < 2.0,
        "pequena": min(largura, altura) < 160,
        "tem_alpha": im.mode in ("RGBA", "LA") or "transparency" in im.info,
    }


def _rasterizar(conteudo: bytes) -> bytes | None:
    """SVG não entra em modelo de imagem: renderiza antes de perguntar.

    Vetor é o melhor formato do acervo, e o portão recusava todos por não
    conseguir abrir o arquivo. `resvg` só existe dentro do `devenv`; se faltar,
    devolve None e o erro aparece na decisão.
    """
    try:
        from .publicacao import svg_para_png

        return svg_para_png(conteudo)
    except Exception:  # noqa: BLE001
        return None


def carregar(origem: str) -> tuple[bytes, str]:
    """Aceita URL ou caminho local; devolve (bytes, mime)."""
    if origem.startswith(("http://", "https://")):
        r = httpx.get(
            origem, headers={"User-Agent": USER_AGENT}, timeout=60.0, follow_redirects=True
        )
        r.raise_for_status()
        mime = (r.headers.get("content-type") or "image/jpeg").split(";")[0]
        conteudo = r.content
    else:
        caminho = Path(origem)
        ext = caminho.suffix.lower().lstrip(".")
        conteudo = caminho.read_bytes()
        mime = _MIME.get(ext, "image/jpeg")

    if mime == "image/svg+xml" or b"<svg" in conteudo[:1000]:
        png = _rasterizar(conteudo)
        if png:
            return png, "image/png"
    return conteudo, mime


def _payload(modelo: str, url_dados: str, max_tokens: int = 800) -> dict:
    return {
        "model": modelo,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": url_dados}},
                ],
            }
        ],
        "max_tokens": max_tokens,
    }


def verificar_decisao(
    origem: str,
    *,
    provedor: str = PROVEDOR_VISAO,
    modelo: str = MODELO_DECISAO,
    perguntas: dict | None = None,
    timeout: float = 120.0,
    contexto: str | None = None,
) -> dict:
    """Classifica por modelo de decisão (System One): probabilidades, sem geração.

    `aceito` usa as mesmas regras do gate por chat: é brasão/bandeira, com
    confiança razoável, e sem marca d'água. `contexto` entra no `state` — é o
    que permite perguntar "é o brasão DESTE município", e não só "é um brasão".
    """
    p = provedores.obter(provedor)
    chave = p.chave()
    if not chave:
        return {"erro": f"{p.env} ausente", "aceito": False}

    try:
        conteudo, mime = carregar(origem)
    except Exception as exc:  # noqa: BLE001
        return {"erro": f"falha ao carregar imagem: {exc}"[:200], "aceito": False}

    s = sinais(conteudo)
    if s.get("erro"):
        return {"erro": s["erro"], "aceito": False}

    r = httpx.post(
        f"{p.base}{SISTEMAONE}",
        headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
        timeout=timeout,
        json={
            "model": modelo,
            "state": contexto
            or "Candidato a símbolo municipal brasileiro, extraído de site de prefeitura.",
            "images": [data_url(conteudo, mime)],
            "questions": perguntas or PERGUNTAS,
        },
    )
    if r.status_code != 200:
        return {"erro": f"{p.nome} HTTP {r.status_code}: {r.text[:220]}", "aceito": False}

    d = r.json()
    respostas = d.get("answers") or {}
    tipo = respostas.get("tipo") or {}
    escolha = tipo.get("choice")
    confianca = float(tipo.get("confidence") or 0)
    agua = float((respostas.get("tem_marca_dagua") or {}).get("noul") or 0)
    fundo = float((respostas.get("fundo_limpo") or {}).get("noul") or 0)

    uso = d.get("usage") or {}
    custo = d.get("cost") or {}
    reportado = custo.get("request_cost_usd")
    motivo = (
        "imagem_vazia"
        if s["vazia"]
        else "marca_dagua"
        if agua > 0.5
        else "fundo_sujo"
        if fundo <= 0.5
        else None
        if escolha in ("brasao", "bandeira")
        else escolha
    )
    tier = "T1" if s["pequena"] else "T2"
    return {
        "tipo": escolha,
        "perguntas_versao": PERGUNTAS_VERSAO,
        "probabilidades": tipo.get("probabilities"),
        "confianca": confianca,
        "marca_dagua": agua > 0.5,
        "prob_marca_dagua": agua,
        "fundo_limpo": fundo > 0.5,
        "prob_fundo_limpo": fundo,
        "truncated": d.get("truncated"),
        "sinais": s,
        "tier": tier,
        "aceito": (
            escolha in ("brasao", "bandeira")
            and confianca >= 0.6
            and agua <= 0.5
            # Brasão tem que estar isolado; bandeira é pano retangular por
            # natureza, e exigir "fundo limpo" dela reprova bandeira limpa.
            and (escolha == "bandeira" or fundo > 0.5)
            and not s["vazia"]
        ),
        "rejeitar_motivo": motivo,
        "precisa_recorte": bool(s["largura"] / max(s["altura"], 1) > 2.2),
        "kb": round(len(conteudo) / 1024, 1),
        "uso": {
            "provedor": p.nome,
            "modelo": modelo,
            "motor": "systemone",
            "entrada": uso.get("input_tokens"),
            "saida": uso.get("output_tokens", 0),
            "custo": float(reportado) if reportado is not None else None,
            "moeda": p.moeda if reportado is not None else None,
            "restante": custo.get("allowance_remaining_usd"),
        },
    }


def verificar(
    origem: str,
    *,
    provedor: str = PROVEDOR_VISAO,
    modelo: str = MODELO_VISAO,
    flex: bool = False,
    timeout: float = 180.0,
) -> dict:
    """Classifica a imagem. `aceito` = é brasão ou bandeira com confiança razoável."""
    p = provedores.obter(provedor)
    chave = p.chave()
    if not chave:
        return {"erro": f"{p.env} ausente", "aceito": False}

    try:
        conteudo, mime = carregar(origem)
    except Exception as exc:  # noqa: BLE001
        return {"erro": f"falha ao carregar imagem: {exc}"[:200], "aceito": False}

    if flex:
        modelo = p.com_flex(modelo)

    cabecalhos = {"Authorization": f"Bearer {chave}", "Content-Type": "application/json"}
    url_dados = data_url(conteudo, mime)
    limite = 800
    dados: dict | None = None
    resposta: httpx.Response | None = None

    for tentativa in range(3):
        resposta = httpx.post(
            f"{p.base}/chat/completions",
            headers=cabecalhos,
            timeout=timeout,
            json=_payload(modelo, url_dados, limite),
        )
        if resposta.status_code in (400, 404) and modelo.endswith("-flex"):
            modelo = modelo.removesuffix("-flex")
            resposta = httpx.post(
                f"{p.base}/chat/completions",
                headers=cabecalhos,
                timeout=timeout,
                json=_payload(modelo, url_dados, limite),
            )
        if resposta.status_code != 200:
            return {
                "erro": f"{p.nome} HTTP {resposta.status_code}: {resposta.text[:200]}",
                "aceito": False,
            }

        corpo = resposta.json()
        escolha = corpo["choices"][0]
        texto = escolha["message"].get("content") or ""
        achado = texto[texto.find("{") : texto.rfind("}") + 1]
        try:
            dados = json.loads(achado) if achado else None
        except json.JSONDecodeError:
            dados = None
        if dados is not None:
            break
        # Modelo gastou o orçamento em raciocínio e não sobrou conteúdo.
        if tentativa < 2:
            limite = min(limite * 2, 4800)

    if dados is None:
        return {
            "erro": "sem JSON após 3 tentativas (raciocínio consumiu a saída)",
            "finish_reason": escolha.get("finish_reason") if resposta else None,
            "aceito": False,
        }
    d = corpo
    tipo = dados.get("tipo")
    confianca = float(dados.get("confianca") or 0)
    uso = d.get("usage") or {}
    custo = d.get("cost") or {}
    reportado = custo.get("request_cost_usd")
    return {
        "tipo": tipo,
        "municipio": dados.get("municipio"),
        "tem_listel": dados.get("tem_listel"),
        "marca_dagua": dados.get("marca_dagua"),
        "fundo": dados.get("fundo"),
        "descricao": dados.get("descricao"),
        "confianca": confianca,
        "aceito": tipo in ("brasao", "bandeira") and confianca >= 0.6,
        "rejeitar_motivo": (
            "marca_dagua"
            if dados.get("marca_dagua")
            else "fundo_nao_limpo"
            if dados.get("fundo") not in (None, "limpo")
            else None
        ),
        "kb": round(len(conteudo) / 1024, 1),
        "uso": {
            "provedor": p.nome,
            "modelo": modelo,
            "entrada": uso.get("prompt_tokens"),
            "saida": uso.get("completion_tokens"),
            "reasoning": (uso.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "custo": float(reportado) if reportado is not None else None,
            "moeda": p.moeda if reportado is not None else None,
            "restante": custo.get("allowance_remaining_usd"),
        },
    }
