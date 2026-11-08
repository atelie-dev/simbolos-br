"""Provedores OpenAI-compatíveis: Maritaca, DeepSeek, Zhipu/GLM.

Todos falam `/chat/completions` no mesmo formato, então o transporte é um só e o
que muda é base URL, variável de ambiente da chave, modelo padrão e preço.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Provedor:
    nome: str
    base: str
    env: str
    modelo: str
    preco_entrada: float | None = None  # por milhão de tokens, na moeda do provedor
    preco_saida: float | None = None
    moeda: str = "BRL"
    descontinuado: bool = False
    nota: str = ""

    @property
    def chat(self) -> str:
        return f"{self.base}/chat/completions"

    @property
    def modelos(self) -> str:
        return f"{self.base}/models"

    def chave(self) -> str | None:
        return os.environ.get(self.env)

    def custo(
        self,
        entrada: int,
        saida: int,
        *,
        cache: int = 0,
        tier: str | None = None,
        modelo: str | None = None,
    ) -> float | None:
        """Estimativa quando o provedor não reporta custo.

        Aplica os descontos que a doc declara: tier flex = 50%; token em cache
        paga 25% do preço de entrada (10% nos modelos S5). Descontos não se
        multiplicam entre si — cache e tier incidem sobre partes diferentes.
        """
        if self.preco_entrada is None or self.preco_saida is None:
            return None
        alvo = (modelo or self.modelo).upper()
        fator_tier = 0.5 if tier == "flex" else 1.0
        fator_cache = 0.10 if alvo.startswith("S5") else 0.25
        nao_cache = max(entrada - cache, 0)
        entrada_efetiva = (nao_cache * fator_tier + cache * fator_cache) / 1e6
        saida_efetiva = saida * fator_tier / 1e6
        return entrada_efetiva * self.preco_entrada + saida_efetiva * self.preco_saida

    def com_flex(self, modelo: str) -> str:
        """Variante de fila (Neuralwatt): mesmo modelo, ~30% mais barato."""
        if self.nome == "neuralwatt" and not modelo.endswith("-flex"):
            return f"{modelo}-flex"
        return modelo

    @property
    def usa_service_tier(self) -> bool:
        """Maritaca usa `service_tier: flex` no corpo em vez de sufixo no modelo."""
        return self.nome == "maritaca"


PROVEDORES: dict[str, Provedor] = {
    "maritaca": Provedor(
        nome="maritaca",
        base="https://chat.maritaca.ai/api",
        env="MARITACA_API_KEY",
        modelo="S5",
        preco_entrada=0.50,
        preco_saida=2.50,
        nota="S5: 1M de contexto, cobra tokens de raciocínio como saída",
    ),
    "deepseek": Provedor(
        nome="deepseek",
        base="https://api.deepseek.com/v1",
        env="DEEPSEEK_API_KEY",
        modelo="deepseek-chat",
        moeda="USD",
        descontinuado=True,
        nota="DESCONTINUADO: usar neuralwatt/deepseek-v4.1-flash (mesmos modelos, fatura única)",
    ),
    "glm": Provedor(
        nome="glm",
        base="https://open.bigmodel.cn/api/paas/v4",
        env="GLM_API_KEY",
        modelo="glm-5.3",
        moeda="CNY",
        nota="Zhipu direto; o mesmo GLM 5.3 também sai pelo Neuralwatt",
    ),
    "neuralwatt": Provedor(
        nome="neuralwatt",
        base="https://api.neuralwatt.com/v1",
        env="NEURALWATT_API_KEY",
        modelo="glm-5.3",
        moeda="USD",
        nota="rota oficial: deepseek-v4.1-flash, glm-5.3/5.3-flash, kimi-k3; reporta custo por request",
    ),
}

PADRAO = "maritaca"

# Extracao de pagina unica: o A/B mediu 3/3 a US$ 0,0012 nos 3 casos, contra
# R$ 0,0238 do S5. Modelo de raciocinio fica para documento longo.
EXTRACAO_PADRAO: tuple[str, str] = ("neuralwatt", "deepseek-v4.1-flash")


def resolver_extracao(provedor: str | None, modelo: str | None) -> tuple[str, str | None]:
    if provedor is None:
        nome, padrao = EXTRACAO_PADRAO
        return nome, modelo or padrao
    return provedor, modelo


def obter(nome: str | None = None) -> Provedor:
    return PROVEDORES[(nome or PADRAO).lower()]


def disponiveis() -> list[tuple[Provedor, bool]]:
    return [(p, bool(p.chave())) for p in PROVEDORES.values()]
