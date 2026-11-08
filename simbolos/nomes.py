"""Normalizacao de nomes e casamento arquivo -> municipio."""

import re
import unicodedata

_NAO_ALNUM = re.compile(r"[^a-z0-9]+")


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """'São Paulo' -> 'sao paulo'. Espaco unico, sem acento, minusculo."""
    return " ".join(_NAO_ALNUM.sub(" ", sem_acento(texto).lower()).split())


def slug(texto: str) -> str:
    """'São Paulo' -> 'sao-paulo'; 'D'Oeste' -> 'd-oeste'."""
    return _NAO_ALNUM.sub("-", sem_acento(texto).lower()).strip("-")


def compacto(texto: str) -> str:
    """'São Paulo das Missões' -> 'saopaulodasmissoes' (padrao de dominio gov.br)."""
    return re.sub(r"[^a-z0-9]", "", sem_acento(texto).lower())


def normalizar_arquivo(nome: str) -> str:
    """Nome de arquivo do Commons vira texto comparavel.

    'Brasão de Eunápolis.svg'         -> 'brasao de eunapolis'
    'BANDEIRAMURICI.svg'              -> 'bandeiramurici'
    '500px-Bandeira_de_Canapi_AL.png' -> '500px bandeira de canapi al'
    """
    nome = re.sub(r"\.(svg|png|jpe?g|gif|webp|tiff?)$", "", nome, flags=re.IGNORECASE)
    return normalizar(nome.replace("_", " ").replace("-", " "))


# Palavras que identificam o tipo de simbolo no nome do arquivo.
_PISTAS_BRASAO = ("brasao", "brasoes", "escudo", "coat of arms", "armas", "brasao de armas")
_PISTAS_BANDEIRA = ("bandeira", "bandeiras", "flag", "pavilhao", "estandarte")
_PISTAS_RUIDO = (
    "mapa",
    "map",
    "localizacao",
    "location",
    "bandeira do brasil",
    "flag of brazil",
    "selo",
    "logotipo",
    "logo",
    "brasao do estado",
    "bandeira do estado",
)


def classificar_tipo(nome_arquivo: str) -> str:
    """Retorna 'brasao' | 'bandeira' | 'indefinido' pelo nome do arquivo.

    'indefinido' e o resultado honesto quando o nome nao diz; a triagem humana
    resolve depois. Nunca chutar 'brasao' por padrao.
    """
    n = normalizar_arquivo(nome_arquivo)
    brasao = any(p in n for p in _PISTAS_BRASAO)
    bandeira = any(p in n for p in _PISTAS_BANDEIRA)
    if brasao and not bandeira:
        return "brasao"
    if bandeira and not brasao:
        return "bandeira"
    if brasao and bandeira:
        # "Bandeira, Brasão de X": o arquivo tem os dois; o mais seguro e revisar.
        return "indefinido"
    return "indefinido"


def parece_ruido(nome_arquivo: str) -> bool:
    n = normalizar_arquivo(nome_arquivo)
    return any(p in n for p in _PISTAS_RUIDO)


def casar_municipio(
    nome_arquivo: str,
    municipios: list[dict],
    uf: str,
) -> tuple[dict | None, str]:
    """Casa um nome de arquivo com um municipio da mesma UF.

    Ordem: nome mais longo primeiro, para 'Rio de Janeiro' ganhar de 'Rio'.
    Retorna (municipio | None, motivo).
    """
    n = normalizar_arquivo(nome_arquivo)
    candidatos = sorted(municipios, key=lambda m: len(m["nome_norm"]), reverse=True)

    for m in candidatos:
        alvo = m["nome_norm"]
        if not alvo:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(alvo)}(?![a-z0-9])", n):
            return m, "nome_exato"

    for m in candidatos:
        alvo = m["nome_norm"]
        if len(alvo) >= 5 and alvo in n.replace(" ", ""):
            return m, "nome_colado"

    return None, "sem_casamento"
