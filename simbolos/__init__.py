"""simbolos-br: acervo aberto dos simbolos municipais brasileiros."""

from pathlib import Path

from dotenv import load_dotenv

__version__ = "0.1.0"

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SPIKE = DATA / "_spike"

# .env montado pelo 1Password no diretorio do projeto (gitignored). Se nao
# existir, as chaves vem do ambiente normalmente.
_env = RAIZ / ".env"
if _env.exists():
    load_dotenv(_env)

# Wikimedia exige UA descritivo com contato. Trocar o e-mail quando o dominio existir.
USER_AGENT = (
    "simbolos-br/0.1 (https://github.com/simbolos-br/simbolos-br; "
    "acervo de simbolos municipais; contato@simbolos.br)"
)

# 27 UFs na ordem oficial do IBGE (2 digitos = codigo da UF).
UFS = [
    "RO",
    "AC",
    "AM",
    "RR",
    "PA",
    "AP",
    "TO",
    "MA",
    "PI",
    "CE",
    "RN",
    "PB",
    "PE",
    "AL",
    "SE",
    "BA",
    "MG",
    "ES",
    "RJ",
    "SP",
    "PR",
    "SC",
    "RS",
    "MS",
    "MT",
    "GO",
    "DF",
]

NOMES_UF = {
    "RO": "Rondonia",
    "AC": "Acre",
    "AM": "Amazonas",
    "RR": "Roraima",
    "PA": "Para",
    "AP": "Amapa",
    "TO": "Tocantins",
    "MA": "Maranhao",
    "PI": "Piaui",
    "CE": "Ceara",
    "RN": "Rio Grande do Norte",
    "PB": "Paraiba",
    "PE": "Pernambuco",
    "AL": "Alagoas",
    "SE": "Sergipe",
    "BA": "Bahia",
    "MG": "Minas Gerais",
    "ES": "Espirito Santo",
    "RJ": "Rio de Janeiro",
    "SP": "Sao Paulo",
    "PR": "Parana",
    "SC": "Santa Catarina",
    "RS": "Rio Grande do Sul",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "GO": "Goias",
    "DF": "Distrito Federal",
}

# Grafia usada nos nomes de categoria do Commons (com acento).
NOMES_UF_COMMONS = {
    "RO": "Rondônia",
    "AC": "Acre",
    "AM": "Amazonas",
    "RR": "Roraima",
    "PA": "Pará",
    "AP": "Amapá",
    "TO": "Tocantins",
    "MA": "Maranhão",
    "PI": "Piauí",
    "CE": "Ceará",
    "RN": "Rio Grande do Norte",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "AL": "Alagoas",
    "SE": "Sergipe",
    "BA": "Bahia",
    "MG": "Minas Gerais",
    "ES": "Espírito Santo",
    "RJ": "Rio de Janeiro",
    "SP": "São Paulo",
    "PR": "Paraná",
    "SC": "Santa Catarina",
    "RS": "Rio Grande do Sul",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "GO": "Goiás",
    "DF": "Distrito Federal",
}
