"""CLI do projeto: catalogo, coleta e chamadas ao Sabia/S5."""

from __future__ import annotations

import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

from . import (
    DATA,
    NOMES_UF_COMMONS,
    SPIKE,
    UFS,
    USER_AGENT,
    catalogo,
    centros,
    commons,
    config,
    indice,
    leis,
    lotes,
    malha,
    maritaca,
    pix,
    provedores,
    publicacao,
    r2,
    triagem,
    visao,
    wikidata,
)
from .modelos import Candidato
from .nomes import casar_municipio, classificar_tipo, parece_ruido

COLETA = DATA / "_coleta"
console = Console()
erro = Console(stderr=True)

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Acervo de simbolos municipais")
maritaca_app = typer.Typer(no_args_is_help=True, help="Chamadas ao Sabia/S5 (Maritaca)")
app.add_typer(maritaca_app, name="maritaca")


# ---------------------------------------------------------------- catalogo


@app.command("catalogo")
def catalogo_cmd() -> None:
    """Gera data/estados.json e data/municipios.json a partir da API do IBGE."""
    estados, municipios = catalogo.escrever()
    console.print(f"catalogo: [bold]{estados}[/] estados, [bold]{municipios}[/] municipios")


# ---------------------------------------------------------------- coleta


@app.command("wikidata")
def wikidata_cmd(
    sem_imageinfo: Annotated[bool, typer.Option("--sem-imageinfo", help="so o mapa")] = False,
) -> None:
    """Mapa canonico municipio -> arquivo (P1585 / P94 / P41)."""
    mapa = wikidata.mapa()
    destino = COLETA / "wikidata.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(mapa, ensure_ascii=False, indent=0) + "\n")

    total = len(catalogo.carregar())
    com_brasao = sum(1 for v in mapa.values() if v.get("brasao"))
    com_bandeira = sum(1 for v in mapa.values() if v.get("bandeira"))
    console.print(
        f"wikidata: {len(mapa)} codigos | brasao {com_brasao} ({100 * com_brasao / total:.1f}%)"
        f" | bandeira {com_bandeira} ({100 * com_bandeira / total:.1f}%)"
    )

    if sem_imageinfo:
        return

    municipios = catalogo.por_codigo()
    arquivos = sorted({wikidata.titulo_normalizado(t) for t in wikidata.titulos(mapa)})
    arquivos = [t for t in arquivos if "://" not in t]
    console.print(f"resolvendo {len(arquivos)} arquivos no Commons...")
    infos = commons.imageinfo(arquivos)

    candidatos: list[Candidato] = []
    for codigo, item in mapa.items():
        m = municipios.get(codigo)
        if not m:
            continue
        for tipo in ("brasao", "bandeira"):
            arquivo = item.get(tipo)
            if not arquivo:
                continue
            info = infos.get(commons.chave(wikidata.titulo_normalizado(arquivo)))
            if not info:
                continue
            candidatos.append(
                commons.candidato(
                    codigo=codigo,
                    uf=m["uf"],
                    municipio=m["nome"],
                    tipo=tipo,
                    info=info,
                    metodo="wikidata",
                    evidencia={
                        "propriedade": "P94" if tipo == "brasao" else "P41",
                        "arquivo": arquivo,
                    },
                )
            )
    commons.escrever_jsonl(COLETA / "wikidata-candidatos.jsonl", candidatos)
    svg = sum(1 for c in candidatos if c.mime == "image/svg+xml")
    console.print(f"  {len(candidatos)} candidatos ({svg} SVG)")


@app.command("commons")
def commons_cmd(
    uf: Annotated[
        list[str] | None, typer.Option("--uf", help="UF (repetivel); padrao todas")
    ] = None,
) -> None:
    """Coleta por categoria do Commons (brasao + subcategoria SVG)."""
    ufs = uf or UFS
    todos: list[Candidato] = []
    sem_casamento: list[dict] = []

    for sigla in ufs:
        municipios = catalogo.carregar(sigla)
        nome_uf = NOMES_UF_COMMONS[sigla]
        categorias = [
            f"Coats of arms of municipalities of {nome_uf}",
            f"SVG coats of arms of municipalities of {nome_uf}",
        ]
        titulos: dict[str, str] = {}
        for cat in categorias:
            try:
                membros = commons.membros_categoria(cat)
            except RuntimeError as exc:
                erro.print(f"  {sigla} {cat}: {exc}")
                continue
            for t in membros:
                titulos.setdefault(t, "brasao")
            console.print(f"  {sigla} {cat}: {len(membros)} arquivos")

        if not titulos:
            continue
        infos = commons.imageinfo(list(titulos))
        for titulo in titulos:
            info = infos.get(commons.chave(titulo))
            if not info:
                continue
            nome_arq = titulo.removeprefix("File:")
            if parece_ruido(nome_arq):
                continue
            municipio, motivo = casar_municipio(nome_arq, municipios, sigla)
            if not municipio:
                sem_casamento.append({"uf": sigla, "arquivo": nome_arq})
                continue
            tipo = classificar_tipo(nome_arq)
            avisos: list[str] = []
            if tipo == "indefinido":
                tipo = "brasao"
                avisos.append("tipo_presumido_pela_categoria")
            cand = commons.candidato(
                codigo=municipio["codigo"],
                uf=sigla,
                municipio=municipio["nome"],
                tipo=tipo,
                info=info,
                metodo="commons-categoria",
                evidencia={
                    "categoria": f"Category:{nome_uf}",
                    "arquivo": titulo,
                    "casamento": motivo,
                },
            )
            cand.avisos = avisos
            todos.append(cand)
        console.print(f"{sigla}: {len(todos)} candidatos acumulados")

    sufixo = "tudo" if uf is None else "-".join(ufs)
    destino = COLETA / f"commons-{sufixo}.jsonl"
    commons.escrever_jsonl(destino, todos)
    (COLETA / f"commons-sem-casamento-{sufixo}.json").write_text(
        json.dumps(sem_casamento, ensure_ascii=False, indent=1) + "\n"
    )
    console.print(
        f"commons: {len(todos)} candidatos | {len(sem_casamento)} sem casamento -> {destino}"
    )


# ---------------------------------------------------------------- spike


def _amostra(n_por_uf: int = 2, semente: int = 20261107) -> list[dict]:
    rng = random.Random(semente)
    por_uf: dict[str, list[dict]] = defaultdict(list)
    for m in catalogo.carregar():
        por_uf[m["uf"]].append(m)
    amostra: list[dict] = []
    for sigla in UFS:
        lista = sorted(por_uf[sigla], key=lambda m: m["nome"])
        if len(lista) <= n_por_uf:
            amostra += lista
        else:
            amostra.append(lista[0])
            amostra.append(rng.choice(lista[1:]))
    return amostra


def _melhor(itens: list[Candidato]) -> Candidato | None:
    if not itens:
        return None
    return max(itens, key=lambda c: (c.mime == "image/svg+xml", c.largura or 0, c.bytes or 0))


def _resumo(candidatos: list[Candidato], amostra: list[dict]) -> dict:
    por_codigo: dict[str, list[Candidato]] = defaultdict(list)
    for c in candidatos:
        por_codigo[c.codigo_ibge].append(c)
    linhas = []
    for m in amostra:
        itens = por_codigo.get(m["codigo"], [])
        br = [c for c in itens if c.tipo == "brasao"]
        ba = [c for c in itens if c.tipo == "bandeira"]
        melhor = _melhor(br)
        linhas.append(
            {
                "codigo": m["codigo"],
                "uf": m["uf"],
                "municipio": m["nome"],
                "brasao": bool(br),
                "bandeira": bool(ba),
                "svg": bool(melhor and melhor.mime == "image/svg+xml"),
                "balde": melhor.licenca.balde if melhor else None,
                "mime": melhor.mime if melhor else None,
                "fonte": melhor.coleta.metodo if melhor else None,
            }
        )
    total = len(linhas) or 1
    return {
        "amostra": len(linhas),
        "com_brasao": sum(1 for x in linhas if x["brasao"]),
        "com_bandeira": sum(1 for x in linhas if x["bandeira"]),
        "com_svg": sum(1 for x in linhas if x["svg"]),
        "baldes": dict(Counter(x["balde"] for x in linhas if x["balde"])),
        "detalhe": linhas,
        "percentual": {
            "brasao": round(100 * sum(1 for x in linhas if x["brasao"]) / total, 1),
            "bandeira": round(100 * sum(1 for x in linhas if x["bandeira"]) / total, 1),
            "svg": round(100 * sum(1 for x in linhas if x["svg"]) / total, 1),
        },
    }


@app.command()
def spike(n_por_uf: Annotated[int, typer.Option("--n-por-uf")] = 2) -> None:
    """Relatorio de rendimento da coleta na amostra estratificada."""
    amostra = _amostra(n_por_uf)
    caminho = COLETA / "commons-tudo.jsonl"
    if not caminho.exists():
        raise typer.BadParameter(f"rode antes: simbolos commons  ({caminho} nao existe)")

    candidatos = [
        Candidato.model_validate_json(linha)
        for linha in caminho.read_text().splitlines()
        if linha.strip()
    ]
    wd = COLETA / "wikidata-candidatos.jsonl"
    if wd.exists():
        candidatos += [
            Candidato.model_validate_json(linha)
            for linha in wd.read_text().splitlines()
            if linha.strip()
        ]

    resumo = _resumo(candidatos, amostra)
    total = len(catalogo.carregar())
    br = {c.codigo_ibge for c in candidatos if c.tipo == "brasao"}
    ba = {c.codigo_ibge for c in candidatos if c.tipo == "bandeira"}
    svg = {c.codigo_ibge for c in candidatos if c.tipo == "brasao" and c.mime == "image/svg+xml"}
    resumo["catalogo"] = {
        "total": total,
        "brasao": len(br),
        "bandeira": len(ba),
        "svg": len(svg),
        "pct_brasao": round(100 * len(br) / total, 1),
        "pct_bandeira": round(100 * len(ba) / total, 1),
        "pct_svg": round(100 * len(svg) / total, 1),
    }

    SPIKE.mkdir(parents=True, exist_ok=True)
    (SPIKE / "relatorio.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1) + "\n")

    t = Table(title=f"catalogo ({total} municipios)")
    t.add_column("medida")
    t.add_column("municipios", justify="right")
    t.add_column("%", justify="right")
    cat = resumo["catalogo"]
    t.add_row("brasao", str(cat["brasao"]), str(cat["pct_brasao"]))
    t.add_row("bandeira", str(cat["bandeira"]), str(cat["pct_bandeira"]))
    t.add_row("brasao SVG", str(cat["svg"]), str(cat["pct_svg"]))
    console.print(t)
    p = resumo["percentual"]
    console.print(
        f"amostra {resumo['amostra']}: brasao {p['brasao']}% | bandeira "
        f"{p['bandeira']}% | SVG {p['svg']}%"
    )


# ---------------------------------------------------------------- maritaca


@maritaca_app.command("modelos")
def maritaca_modelos() -> None:
    """Lista modelos disponiveis e contexto."""
    t = Table(title="modelos Maritaca")
    t.add_column("id")
    t.add_column("contexto", justify="right")
    for m in maritaca.modelos():
        t.add_row(m.get("id", "?"), f"{m.get('context_length', 0):,}")
    console.print(t)


@maritaca_app.command("saldo")
def maritaca_saldo(
    provedor: Annotated[str, typer.Option(help="maritaca | neuralwatt")] = "maritaca",
) -> None:
    """Saldo e uso do provedor."""
    d = maritaca.saldo(provedor)
    simbolo = "R$" if d["moeda"] == "BRL" else "US$"
    console.print(f"saldo {d['provedor']}: [bold]{simbolo} {d['saldo']:.2f}[/]")
    periodo = d.get("periodo")
    if periodo:
        console.print(f"periodo {periodo.get('start_date')} -> {periodo.get('end_date')}")
    uso = d.get("uso") or {}
    if uso:
        console.print(
            f"uso: {uso.get('total_requests', 0)} requisicoes | "
            f"R$ {uso.get('total_cost', 0):.4f} | "
            f"{uso.get('input_tokens', 0):,} in / {uso.get('output_tokens', 0):,} out | "
            f"{uso.get('cached_tokens', 0):,} cache"
        )


def _ler_entrada(url: str | None, arquivo: Path | None) -> tuple[str, str]:
    if url:
        r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=60.0, follow_redirects=True)
        r.raise_for_status()
        return r.text, url
    if arquivo:
        return arquivo.read_text(errors="ignore"), str(arquivo)
    raise typer.BadParameter("informe --url ou --arquivo")


@maritaca_app.command("extrair")
def maritaca_extrair(
    url: Annotated[str | None, typer.Option(help="pagina a analisar")] = None,
    arquivo: Annotated[Path | None, typer.Option(help="HTML local")] = None,
    provedor: Annotated[
        str | None, typer.Option(help="maritaca | neuralwatt (padrao: neuralwatt)")
    ] = None,
    modelo: Annotated[str | None, typer.Option(help="padrao do provedor")] = None,
    max_tokens: Annotated[int, typer.Option("--max-tokens")] = maritaca.MAX_TOKENS_PADRAO,
    flex: Annotated[bool, typer.Option("--flex/--sem-flex", help="fila -30%")] = False,
    verificar: Annotated[bool, typer.Option(help="confere a URL do ativo com HEAD")] = True,
) -> None:
    """Extrai o simbolo de uma pagina, com citacao verificada."""
    html, base = _ler_entrada(url, arquivo)
    res = maritaca.extrair(
        html, base, provedor=provedor, modelo=modelo, max_tokens=max_tokens, flex=flex
    )
    res["html_kb"] = round(len(html) / 1024, 1)

    if verificar and res.get("url_ativo"):
        try:
            h = httpx.head(
                res["url_ativo"],
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
                follow_redirects=True,
            )
            res["ativo_http"] = h.status_code
            res["ativo_tipo"] = h.headers.get("content-type")
        except Exception as exc:  # noqa: BLE001
            res["ativo_http"] = f"erro: {exc}"

    console.print_json(json.dumps(res, ensure_ascii=False))


@maritaca_app.command("provedores")
def maritaca_provedores() -> None:
    """Provedores configurados e se a chave esta presente no ambiente."""
    t = Table(title="provedores")
    t.add_column("nome")
    t.add_column("modelo")
    t.add_column("chave")
    t.add_column("moeda")
    t.add_column("preco (in/out por M)")
    t.add_column("status")
    for p, tem_chave in provedores.disponiveis():
        status = "descontinuado" if p.descontinuado else "ativo"
        preco = (
            f"{p.preco_entrada:.2f} / {p.preco_saida:.2f}"
            if p.preco_entrada is not None
            else "reportado por requisição"
        )
        t.add_row(
            p.nome,
            p.modelo,
            "ok" if tem_chave else f"falta {p.env}",
            p.moeda,
            preco,
            status,
        )
    console.print(t)


@maritaca_app.command("perguntar")
def maritaca_perguntar(
    sistema: Annotated[Path, typer.Option(help="arquivo com o prompt de sistema")],
    arquivo: Annotated[Path, typer.Option(help="arquivo com o conteudo (texto/HTML)")],
    provedor: Annotated[
        str | None, typer.Option(help="maritaca | neuralwatt (padrao: neuralwatt)")
    ] = None,
    modelo: Annotated[str | None, typer.Option(help="padrao do provedor")] = None,
    max_tokens: Annotated[int, typer.Option("--max-tokens")] = maritaca.MAX_TOKENS_PADRAO,
    json_saida: Annotated[bool, typer.Option("--json", help="imprime o JSON parseado")] = False,
) -> None:
    """Chamada crua: prompt de sistema + conteudo. Util para experimentos."""
    mensagens = [
        {"role": "system", "content": sistema.read_text()},
        {"role": "user", "content": arquivo.read_text(errors="ignore")},
    ]
    with console.status(f"chamando {provedor}/{modelo or 'padrao'}..."):
        resp = maritaca.chamar(mensagens, provedor=provedor, modelo=modelo, max_tokens=max_tokens)
    console.print(
        f"[dim]{resp.provedor}/{resp.modelo} | {resp.entrada:,} in / {resp.saida:,} out "
        f"({resp.reasoning:,} raciocínio) | {resp.tentativas} tentativa(s) | "
        f"{resp.finish_reason} | {maritaca.formatar_custo(resp)}[/]"
    )
    if json_saida:
        console.print_json(json.dumps(resp.json(), ensure_ascii=False))
    else:
        console.print(resp.conteudo)


@maritaca_app.command("lote")
def maritaca_lote(
    entrada: Annotated[Path, typer.Option(help="arquivo com uma URL por linha")],
    saida: Annotated[Path, typer.Option(help="JSONL de resultado (retomavel)")],
    provedor: Annotated[
        str | None, typer.Option(help="maritaca | neuralwatt (padrao: neuralwatt)")
    ] = None,
    modelo: Annotated[str | None, typer.Option(help="padrao do provedor")] = None,
    max_tokens: Annotated[int, typer.Option("--max-tokens")] = maritaca.MAX_TOKENS_PADRAO,
    flex: Annotated[bool, typer.Option("--flex/--sem-flex", help="fila -30%")] = True,
    limite: Annotated[int, typer.Option(help="0 = todas")] = 0,
) -> None:
    """Extrai em lote de uma lista de URLs, retomando de onde parou."""
    urls = [u.strip() for u in entrada.read_text().splitlines() if u.strip()]
    feitos = set()
    if saida.exists():
        for linha in saida.read_text().splitlines():
            try:
                feitos.add(json.loads(linha)["url"])
            except Exception:  # noqa: BLE001, S110
                pass
    pendentes = [u for u in urls if u not in feitos]
    if limite:
        pendentes = pendentes[:limite]

    custos: dict[str, float] = {}
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("a") as f:
        for i, url in enumerate(pendentes, 1):
            try:
                html = httpx.get(
                    url, headers={"User-Agent": USER_AGENT}, timeout=60.0, follow_redirects=True
                ).text
                res = maritaca.extrair(
                    html,
                    url,
                    provedor=provedor,
                    modelo=modelo,
                    max_tokens=max_tokens,
                    flex=flex,
                )
            except Exception as exc:  # noqa: BLE001
                res = {"encontrado": False, "erro": str(exc)[:200]}
            res["url"] = url
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            f.flush()
            uso = res.get("uso") or {}
            if uso.get("custo") is not None and uso.get("moeda"):
                custos[uso["moeda"]] = custos.get(uso["moeda"], 0.0) + uso["custo"]
            acumulado = " ".join(f"{m} {v:.6f}" for m, v in custos.items()) or "-"
            console.print(
                f"[{i}/{len(pendentes)}] {url} -> "
                f"{'OK' if res.get('aceito') else 'nao'} ({acumulado})"
            )
            time.sleep(1.0)


# ---------------------------------------------------------------- leis


def _cobertos() -> set[str]:
    """Codigos que ja tem brasao coletado (Wikidata ou Commons)."""
    cobertos: set[str] = set()
    for nome in ("wikidata-candidatos.jsonl", "commons-tudo.jsonl"):
        caminho = COLETA / nome
        if not caminho.exists():
            continue
        for linha in caminho.read_text().splitlines():
            if not linha.strip():
                continue
            try:
                item = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if item.get("tipo") == "brasao":
                cobertos.add(item["codigo_ibge"])
    return cobertos


@app.command("leis")
def leis_cmd(
    uf: Annotated[str | None, typer.Option(help="sigla da UF; padrao todas")] = None,
    limite: Annotated[int, typer.Option(help="0 = todos")] = 0,
    saida: Annotated[Path, typer.Option(help="JSONL de resultado (retomavel)")] = COLETA
    / "leis.jsonl",
    provedor: Annotated[
        str | None, typer.Option(help="maritaca | neuralwatt (padrao: neuralwatt)")
    ] = None,
    modelo: Annotated[str | None, typer.Option(help="padrao do provedor")] = None,
    paginas: Annotated[int, typer.Option(help="paginas candidatas por site")] = 3,
    flex: Annotated[bool, typer.Option("--flex/--sem-flex", help="fila -30%")] = True,
    paralelismo: Annotated[int, typer.Option(help="municipios simultaneos")] = 3,
    pausa: Annotated[float, typer.Option(help="segundos entre municipios")] = 0.0,
) -> None:
    """Caca a lei que instituiu o simbolo nos municipios sem cobertura."""
    cobertos = _cobertos()
    faltantes = [m for m in catalogo.carregar(uf) if m["codigo"] not in cobertos]
    if limite:
        faltantes = faltantes[:limite]
    if not faltantes:
        console.print("nada a fazer: todos os municipios da selecao ja tem brasao coletado")
        return

    console.print(
        f"{len(faltantes)} municipios sem cobertura | provedor {provedor} | saida {saida}"
    )
    resumo = leis.coletar_lote(
        faltantes,
        saida,
        provedor=provedor,
        modelo=modelo,
        limite_paginas=paginas,
        flex=flex,
        paralelismo=paralelismo,
        pausa=pausa,
    )
    console.print(
        f"processados {resumo['processados']} | com ato {resumo['com_ato']} | "
        f"com PDF {resumo['com_pdf']} | com PDF vetorial {resumo['com_pdf_vetorial']} | "
        + (" ".join(f"{k} {v:.6f}" for k, v in resumo["custos"].items()) or "custo -")
    )


@app.command("visao")
def visao_cmd(
    url: Annotated[str, typer.Option(help="URL ou caminho local da imagem")],
    motor: Annotated[str, typer.Option(help="decisao (clef-flash) | chat")] = "decisao",
    modelo: Annotated[str | None, typer.Option(help="padrao do motor")] = None,
    flex: Annotated[bool, typer.Option("--flex/--sem-flex", help="fila -30%")] = False,
) -> None:
    """Classifica uma imagem: brasao, bandeira, logo ou outro."""
    if motor == "decisao":
        res = visao.verificar_decisao(url, modelo=modelo or visao.MODELO_DECISAO)
    else:
        res = visao.verificar(url, modelo=modelo or visao.MODELO_VISAO, flex=flex)
    console.print_json(json.dumps(res, ensure_ascii=False))
    if res.get("tipo"):
        console.print(
            f"[bold]{res['tipo']}[/] | confianca {res.get('confianca')} | "
            f"{'aceito' if res.get('aceito') else 'rejeitado'}"
        )


@maritaca_app.command("batch")
def maritaca_batch(
    entrada: Annotated[Path, typer.Option(help="arquivo com uma URL por linha")],
    saida: Annotated[Path, typer.Option(help="JSONL de resultado")],
    modelo: Annotated[str, typer.Option(help="modelo do batch")] = "S5",
    max_paginas: Annotated[int, typer.Option("--max-paginas", help="0 = todas")] = 0,
    esperar_segundos: Annotated[int, typer.Option("--timeout", help="0 = nao esperar")] = 1500,
) -> None:
    """Extracao em lote pelo batch da Maritaca (~50% mais barato)."""
    urls = [u.strip() for u in entrada.read_text().splitlines() if u.strip()]
    if max_paginas:
        urls = urls[:max_paginas]

    paginas: list[tuple[str, str]] = []
    for url in urls:
        try:
            html = httpx.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=60.0, follow_redirects=True
            ).text
            paginas.append((url, html))
        except Exception as exc:  # noqa: BLE001
            erro.print(f"{url}: {exc}"[:160])

    if not paginas:
        raise typer.BadParameter("nenhuma pagina carregada")

    res = lotes.executar(
        paginas,
        modelo=modelo,
        timeout=float(esperar_segundos),
        apenas_enviar=esperar_segundos == 0,
    )
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")

    console.print(
        f"batch {res['batch_id']} | {res['paginas']} paginas | status {res['status']}"
        + (" (timeout)" if res.get("timeout") else "")
    )
    for item in res.get("resultados", []):
        console.print(f"  {item.get('url')} -> {'OK' if item.get('aceito') else 'nao'}")
    console.print(f"-> {saida}")


@app.command("triar")
def triar_cmd(
    saida: Annotated[Path, typer.Option(help="catalogo JSON")] = DATA
    / "_catalogo"
    / "catalogo.json",
) -> None:
    """Escolhe um candidato por municipio/tipo e monta o catalogo."""
    caminhos = [
        COLETA / "wikidata-candidatos.jsonl",
        COLETA / "commons-tudo.jsonl",
    ]
    cat = triagem.montar(caminhos)
    if not cat:
        raise typer.BadParameter("nenhum candidato: rode wikidata e commons antes")

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(cat, ensure_ascii=False, indent=0) + "\n")

    r = triagem.relatorio(cat)
    total_municipios = len(catalogo.carregar())
    t = Table(title=f"catalogo: {r['municipios']} municipios de {total_municipios}")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("com brasao", f"{r['com_brasao']} ({100 * r['com_brasao'] / total_municipios:.1f}%)")
    t.add_row(
        "com bandeira", f"{r['com_bandeira']} ({100 * r['com_bandeira'] / total_municipios:.1f}%)"
    )
    t.add_row("com os dois", str(r["com_os_dois"]))
    t.add_row(
        "brasao vetorial",
        f"{r['brasao_svg']} ({100 * r['brasao_svg'] / max(r['com_brasao'], 1):.1f}% dos brasoes)",
    )
    t.add_row("precisam de visao", str(r["precisam_visao"]))
    t.add_row("com alternativas", str(r["com_alternativas"]))
    console.print(t)
    console.print(f"baldes: {r['baldes']}")
    console.print(f"formatos: {r['formatos']}")
    console.print(f"-> {saida}")


@app.command("publicar")
def publicar_cmd(
    raiz: Annotated[Path, typer.Option(help="destino da arvore de embed")] = DATA.parent / "dist",
    limite: Annotated[int, typer.Option(help="0 = todos")] = 0,
    uf: Annotated[str | None, typer.Option(help="sigla da UF")] = None,
) -> None:
    """Baixa, renderiza e grava /embed/v1 a partir do catalogo triado."""
    fonte = DATA / "_catalogo" / "catalogo.json"
    if not fonte.exists():
        raise typer.BadParameter("rode antes: simbolos triar")
    catalogo = json.loads(fonte.read_text())

    with console.status("publicando..."):
        r = publicacao.publicar(catalogo, raiz, limite=limite, uf=uf)

    t = Table(title="publicacao local")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("itens tentados", str(r["itens"]))
    t.add_row("publicados", str(r["publicados"]))
    t.add_row("falhas", str(r["falhas"]))
    t.add_row("pulados (ja feitos)", str(r.get("pulados", 0)))
    t.add_row("reconstruidos do disco", str(r.get("reconstruidos", 0)))
    t.add_row("tamanho", f"{r['bytes'] / 1024 / 1024:.1f} MB")
    console.print(t)
    if r["motivos"]:
        console.print(f"motivos de falha: {r['motivos']}")
    console.print(f"-> {raiz}/embed/v1/... e {raiz}/catalogo.json")


@app.command("fontes")
def fontes_cmd(
    arquivo: Annotated[Path, typer.Option(help="catalogo publicado")] = DATA.parent
    / "dist"
    / "catalogo.json",
    raiz: Annotated[Path, typer.Option(help="arvore de embed")] = DATA.parent / "dist",
    limite: Annotated[int, typer.Option(help="0 = todos")] = 0,
    uf: Annotated[str | None, typer.Option(help="sigla da UF")] = None,
) -> None:
    """Rebaixa e arquiva o arquivo de origem dos itens ja publicados.

    Fecha a lacuna da safra publicada antes de a fonte ser guardada: sem o
    original, a rendition de 512 px vira a unica copia e a procedencia deixa de
    ser refazivel. Divergencia de hash nao e corrigida em silencio.
    """
    if not arquivo.exists():
        raise typer.BadParameter("nada publicado ainda: rode simbolos publicar")
    registros = json.loads(arquivo.read_text())
    with console.status("baixando fontes..."):
        r = publicacao.baixar_fontes(
            registros, raiz=raiz, destino_catalogo=arquivo, limite=limite, uf=uf
        )

    t = Table(title="fontes arquivadas")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("itens", str(r["itens"]))
    t.add_row("baixadas", str(r["baixadas"]))
    t.add_row("puladas (ja tinham)", str(r["puladas"]))
    t.add_row("divergentes", str(r["divergentes"]))
    t.add_row("falhas", str(r["falhas"]))
    t.add_row("tamanho", f"{r['bytes'] / 1024 / 1024:.1f} MB")
    console.print(t)
    if r["divergentes"]:
        console.print("atencao: hash diferente do publicado — arquivos em data/fontes/conflito/")
    console.print(f"-> {publicacao.FONTES_REL}/{{brasao|bandeira}}/{{cod}}.{{ext}}")


@app.command("r2")
def r2_cmd(
    arquivo: Annotated[Path, typer.Option(help="catalogo publicado")] = DATA.parent
    / "dist"
    / "catalogo.json",
    raiz: Annotated[Path, typer.Option(help="arvore de embed")] = DATA.parent / "dist",
    concorrencia: Annotated[int, typer.Option(help="uploads simultaneos")] = 16,
    limite: Annotated[int, typer.Option(help="0 = todos")] = 0,
    prefixo: Annotated[str, typer.Option(help="so chaves com este prefixo")] = "",
    forcar: Annotated[
        bool, typer.Option("--forcar/--incremental", help="reenvia mesmo com hash igual")
    ] = False,
) -> None:
    """Sobe embed/ e meta/ para o bucket publico (simbolos-br-cdn)."""
    if not arquivo.exists():
        raise typer.BadParameter("nada publicado ainda: rode simbolos publicar")
    registros = json.loads(arquivo.read_text())
    with console.status(f"enviando para {r2.nome_bucket('cdn')}..."):
        res = r2.enviar_cdn(
            raiz,
            registros,
            concorrencia=concorrencia,
            limite=limite,
            forcar=forcar,
            prefixo=prefixo,
        )

    t = Table(title=f"R2 · {r2.nome_bucket('cdn')}")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("objetos", str(res["objetos"]))
    t.add_row("enviados", str(res["enviados"]))
    t.add_row("pulados (hash igual)", str(res["pulados"]))
    t.add_row("falhas", str(len(res["falhas"])))
    t.add_row("tamanho", f"{res['bytes'] / 1024 / 1024:.1f} MB")
    console.print(t)
    for chave, erro in list(res["falhas"].items())[:10]:
        console.print(f"  {chave}: {erro}", style="red")


@app.command("acervo")
def acervo_cmd(
    concorrencia: Annotated[int, typer.Option(help="uploads simultaneos")] = 8,
    limite: Annotated[int, typer.Option(help="0 = todos")] = 0,
    forcar: Annotated[
        bool, typer.Option("--forcar/--incremental", help="reenvia mesmo com hash igual")
    ] = False,
) -> None:
    """Backup privado: fontes originais (data/fontes) e evidencias (data/evidencias)."""
    with console.status(f"enviando para {r2.nome_bucket('acervo')}..."):
        res = r2.enviar_acervo(concorrencia=concorrencia, limite=limite, forcar=forcar)

    t = Table(title=f"R2 · {r2.nome_bucket('acervo')} (privado)")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("objetos", str(res["objetos"]))
    t.add_row("enviados", str(res["enviados"]))
    t.add_row("pulados (hash igual)", str(res["pulados"]))
    t.add_row("falhas", str(len(res["falhas"])))
    t.add_row("tamanho", f"{res['bytes'] / 1024 / 1024:.1f} MB")
    console.print(t)


@app.command("pix")
def pix_cmd(
    codigo: Annotated[
        str | None, typer.Option(help="BR Code; sem ele regenera do data/pix.json")
    ] = None,
) -> None:
    """Valida o BR Code do PIX e gera o QR que o site publica."""
    r = pix.registrar(codigo) if codigo else pix.gerar()
    t = Table(title="pix")
    t.add_column("medida")
    t.add_column("valor")
    t.add_row("CRC", f"{r['crc']} ({'confere' if r['ok'] else 'NAO CONFERE'})")
    t.add_row("chave", r["chave"] or "-")
    t.add_row("titular", r["nome"] or "-")
    t.add_row("cidade", r["cidade"] or "-")
    t.add_row("valor", r["valor"] or "livre")
    t.add_row("QR", f"{r['bytes_qr'] / 1024:.1f} KB")
    console.print(t)


@app.command("malha")
def malha_cmd() -> None:
    """Fatiar a malha municipal do IBGE em celulas de 1 grau."""
    r = malha.fatiar()
    t = Table(title="malha municipal (IBGE)")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("celulas", str(r["celulas"]))
    t.add_row("tamanho total", f"{r['bytes'] / 1024 / 1024:.1f} MB")
    t.add_row("maior celula", f"{r['maior_kb']} KB")
    t.add_row("media por celula", f"{r['media_kb']} KB")
    console.print(t)
    console.print("-> site/public/api/v1/malha/{lat}_{lon}.json")


@app.command("centros")
def centros_cmd() -> None:
    """Coleta no Wikidata a coordenada da sede de cada municipio."""
    r = centros.coletar()
    t = Table(title="coordenadas dos municipios")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("municipios", str(r["municipios"]))
    t.add_row("linhas do SPARQL", str(r["linhas"]))
    t.add_row("tamanho", f"{r['bytes'] / 1024:.0f} KB")
    t.add_row("tempo", f"{r['segundos']}s")
    console.print(t)
    console.print("-> data/centros.json (rode `simbolos indice` depois)")


@app.command("indice")
def indice_cmd(
    destino: Annotated[Path, typer.Option(help="pasta public/api/v1 do site")] = DATA.parent
    / "site"
    / "public"
    / "api"
    / "v1",
) -> None:
    """Gera o indice de busca e o resumo de cobertura que o site carrega."""
    r = indice.gerar(destino)
    t = Table(title="indice do site")
    t.add_column("medida")
    t.add_column("valor", justify="right")
    t.add_row("entradas", str(r["entradas"]))
    t.add_row("municipios", str(r["resumo"]["municipios"]))
    t.add_row("publicados", str(r["resumo"]["publicados"]))
    t.add_row("com brasao", str(r["resumo"]["municipios_com_brasao"]))
    t.add_row("vetoriais", str(r["resumo"]["vetoriais"]))
    t.add_row("indice", f"{r['bytes_indice'] / 1024:.0f} KB")
    t.add_row("resumo", f"{r['bytes_resumo'] / 1024:.1f} KB")
    console.print(t)
    console.print(f"-> {destino}/municipios.json e resumo.json")


@app.command("urls")
def urls_cmd(
    arquivo: Annotated[Path, typer.Option(help="catalogo publicado")] = DATA.parent
    / "dist"
    / "catalogo.json",
    raiz: Annotated[Path, typer.Option(help="arvore de embed")] = DATA.parent / "dist",
) -> None:
    """Preenche as URLs publicas de cada item, no catalogo e no sidecar."""
    if not arquivo.exists():
        raise typer.BadParameter("nada publicado ainda: rode simbolos publicar")
    registros = json.loads(arquivo.read_text())
    for reg in registros:
        if reg.get("estado") == "publicado":
            reg["urls"] = config.urls_do_item(reg)
            # O sidecar e a verdade do item: se ele nao tem a URL, o consumidor
            # precisa baixar o catalogo inteiro para descobrir onde o arquivo esta.
            publicacao.gravar_meta(raiz, reg)
    arquivo.write_text(json.dumps(registros, ensure_ascii=False, indent=1) + "\n")
    console.print(f"{sum(1 for r in registros if r.get('urls'))} itens com URL")
    console.print(f"site: {config.SITE_BASE}")
    console.print(f"cdn:  {config.CDN_BASE}")
    exemplo = next((r for r in registros if r.get("urls")), None)
    if exemplo:
        console.print(f"exemplo: {exemplo['urls']['png']}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
