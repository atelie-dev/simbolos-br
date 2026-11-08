"""Testes da política de guarda: o que conta como espelho e o que vira risco.

São funções puras de propósito — a decisão de risco não lê disco nem rede, então
o teste fixa a regra, não a infraestrutura.
"""

from __future__ import annotations

import unittest

from simbolos import guarda

URL_COMMONS = (
    "https://upload.wikimedia.org/wikipedia/commons/2/26/"
    "Bras%C3%A3o_de_Porto_Velho.svg?utm_source=commons.wikimedia.org&utm_content=original"
)


def _registro(**campos) -> dict:
    base = {
        "codigo_ibge": "1100205",
        "tipo": "brasao",
        "uf": "RO",
        "municipio": "Porto Velho",
        "origem": URL_COMMONS,
        "balde": "livre",
        "formato_origem": "image/png",
        "estado": "publicado",
    }
    base.update(campos)
    return base


class TituloCommonsTest(unittest.TestCase):
    def test_deriva_titulo_da_url_do_upload(self):
        self.assertEqual(guarda.titulo_commons(URL_COMMONS), "File:Brasão_de_Porto_Velho.svg")

    def test_descarta_query_string(self):
        self.assertEqual(
            guarda.titulo_commons(
                "https://upload.wikimedia.org/wikipedia/commons/a/ab/Bandeira.svg?x=1"
            ),
            "File:Bandeira.svg",
        )

    def test_recusa_origem_fora_do_commons(self):
        self.assertIsNone(guarda.titulo_commons("https://www.portovelho.ro.gov.br/brasao.png"))

    def test_sem_origem(self):
        self.assertIsNone(guarda.titulo_commons(None))


class ClassificarTest(unittest.TestCase):
    def test_raster_livre_confirmado_no_commons_e_baixo(self):
        situacao = guarda.classificar(_registro(verificacao={"estado": "igual"}))
        self.assertEqual(situacao["risco"], "baixo")
        self.assertEqual(situacao["espelhos"], ["commons"])

    def test_raster_pendente_fica_sem_espelho(self):
        situacao = guarda.classificar(_registro(balde="pendente", verificacao={"estado": "igual"}))
        self.assertEqual(situacao["risco"], "alto")
        self.assertEqual(situacao["espelhos"], [])
        self.assertIn("licenca_pendente", situacao["motivo"])

    def test_vetor_pendente_continua_baixo_por_decisao(self):
        situacao = guarda.classificar(
            _registro(balde="pendente", formato_origem="svg", verificacao={"estado": "igual"})
        )
        self.assertEqual(situacao["risco"], "baixo")
        self.assertIn("vetor_versionavel", situacao["motivo"])

    def test_divergencia_tira_o_espelho_do_commons(self):
        situacao = guarda.classificar(_registro(verificacao={"estado": "divergente"}))
        self.assertEqual(situacao["espelhos"], [])
        self.assertEqual(situacao["risco"], "alto")

    def test_renomeado_mantem_o_espelho(self):
        situacao = guarda.classificar(_registro(verificacao={"estado": "renomeado"}))
        self.assertEqual(situacao["espelhos"], ["commons"])

    def test_origem_fora_do_commons_e_risco_alto(self):
        situacao = guarda.classificar(
            _registro(
                origem="https://www.portovelho.ro.gov.br/brasao.png",
                verificacao={"estado": "igual"},
            )
        )
        self.assertEqual(situacao["risco"], "alto")
        self.assertIn("origem_fora_do_commons", situacao["motivo"])

    def test_nao_verificado_e_registrado(self):
        situacao = guarda.classificar(_registro())
        self.assertIn("nao_verificado", situacao["motivo"])


class RelatorioTest(unittest.TestCase):
    def test_lista_apenas_os_de_risco_alto(self):
        regs = [
            _registro(verificacao={"estado": "igual"}),
            _registro(codigo_ibge="3550308", balde="pendente", verificacao={"estado": "igual"}),
        ]
        r = guarda.relatorio(regs)
        self.assertEqual(r["resumo"]["itens"], 2)
        self.assertEqual(r["resumo"]["risco_alto"], 1)
        self.assertEqual([x["codigo_ibge"] for x in r["risco_alto"]], ["3550308"])

    def test_ignora_item_nao_publicado(self):
        r = guarda.relatorio([_registro(estado="falhou")])
        self.assertEqual(r["resumo"]["itens"], 0)


if __name__ == "__main__":
    unittest.main()
