"""Testes das métricas oficiais (dados/METRICAS.md e dados/metricas.json) e dos parâmetros decididos.

Rodar da raiz do repositório, depois de python -m dados.etl.construir_db:
    python -m pytest tests/test_metricas.py -v
"""
from __future__ import annotations

import copy
import re

import duckdb
import pytest
import yaml

from dados.etl import gerar_metricas
from dados.geno_db import consultas

DECISOES = gerar_metricas.RAIZ / "dados" / "decisoes" / "DECISOES.md"


@pytest.fixture(scope="module")
def gerado():
    if not consultas.caminho_banco().exists():
        pytest.fail("geno.duckdb não existe. Rode: python -m dados.etl.construir_db")
    md, d = gerar_metricas.gerar()
    return md, d


def _sem_data(md: str, d: dict):
    """Remove só a data de geração, o único campo que pode mudar entre duas execuções seguidas."""
    d = copy.deepcopy(d)
    d["fonte"].pop("data_geracao")
    return re.sub(r"^- Data de geração:.*$", "", md, flags=re.M), d


def test_porcentagens_por_situacao_somam_100(gerado):
    md, d = gerado
    soma_json = sum(s["pct"] for s in d["estoque"]["situacoes"])
    assert soma_json == pytest.approx(100, abs=0.3), soma_json          # 5 linhas arredondadas a 0,1
    secao = md.split("## Estoque")[1].split("## Por CNAE")[0]
    soma_md = sum(float(x.replace(",", ".")) for x in re.findall(r"\| (\d+,\d)% \|", secao))
    assert soma_md == pytest.approx(100, abs=0.3), soma_md
    assert sum(s["n"] for s in d["estoque"]["situacoes"]) == d["estoque"]["total"]


def test_total_do_md_bate_com_contagem_direta(gerado):
    md, d = gerado
    direto = duckdb.connect(str(consultas.caminho_banco()), read_only=True).execute(
        "SELECT count(*) FROM estabelecimento").fetchone()[0]
    no_md = int(re.search(r"Total de estabelecimentos no recorte: \*\*([\d.]+)\*\*", md).group(1).replace(".", ""))
    assert no_md == direto == d["estoque"]["total"]
    assert direto > 100_000, "teste sem força: recorte pequeno demais"


def test_formato_ptbr_no_md_e_ponto_no_json(gerado):
    md, d = gerado
    assert re.search(r"Ativas: \*\*\d+,\d%\*\*", md)                    # vírgula decimal no artigo
    assert isinstance(d["estoque"]["pct_ativas"], float)                # ponto (número JSON) no estruturado
    assert "." not in str(d["estoque"]["pct_ativas"]).replace(".", "", 1)


def test_rodar_duas_vezes_da_o_mesmo_resultado_exceto_a_data():
    md1, d1 = gerar_metricas.gerar()
    md2, d2 = gerar_metricas.gerar()
    assert _sem_data(md1, d1) == _sem_data(md2, d2)
    assert md1.count("Data de geração") == 1


def test_eventos_e_mortalidade_coerentes(gerado):
    _, d = gerado
    ini, fim = d["recorte"]["periodo"]
    assert [e["ano"] for e in d["eventos"]] == list(range(ini, fim + 1))
    assert all(e["baixas_oficio"] <= e["baixas"] for e in d["eventos"])
    anos = [c["ano"] for c in d["mortalidade"]["coortes"]]
    assert max(anos) == fim - d["mortalidade"]["horizonte_anos"]        # só coortes completas
    assert all(0 <= c["taxa_pct"] <= 100 for c in d["mortalidade"]["coortes"])


def _config():
    with open(consultas.CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_config_tem_todos_os_parametros_decididos_e_bate_com_o_decisoes_md():
    c = _config()["consultas"]
    for chave in ("periodo", "limiar_recuo", "lacuna_max_abs", "lacuna_max_pct", "anos_atipicos"):
        assert chave in c, f"falta {chave} em config.yaml > consultas"
    texto = DECISOES.read_text(encoding="utf-8")
    ini, fim = map(int, re.search(r"período \*\*(\d{4}) a (\d{4})\*\*", texto).groups())
    assert c["periodo"] == [ini, fim]
    assert c["limiar_recuo"] == int(re.search(r"`limiar_recuo = (\d+)`", texto).group(1))
    assert c["lacuna_max_abs"] == int(re.search(r"`lacuna_max_abs = (\d+)`", texto).group(1))
    assert c["lacuna_max_pct"] == pytest.approx(float(re.search(r"`lacuna_max_pct = ([\d.]+)`", texto).group(1)))
    assert c["periodo"][1] < int(_config()["fonte"]["competencia"][:4])  # ano da competência fica de fora


def test_funcoes_de_consulta_leem_os_parametros_do_config(monkeypatch):
    c = _config()["consultas"]
    anos = list(consultas.saturacao(["8593700"])["ano"])
    assert anos == list(range(c["periodo"][0], c["periodo"][1] + 1))      # período padrão vem do config

    base = consultas.mortalidade_setor(["8593700"])
    assert base["nivel_usado"] == "subclasse"                              # nicho grande: sem recuo no limiar do config
    assert base["dados"]["ano_coorte"].max() == c["periodo"][1] - 2

    alterado = copy.deepcopy(_config())
    alterado["consultas"]["limiar_recuo"] = 10**9
    alterado["consultas"]["periodo"] = [c["periodo"][0], c["periodo"][1] - 1]
    monkeypatch.setattr(consultas, "_config", lambda: alterado)
    forcado = consultas.mortalidade_setor(["8593700"])
    assert forcado["nivel_usado"] == "grupo"                               # o limiar do config é o que decide
    assert forcado["dados"]["ano_coorte"].max() == c["periodo"][1] - 1 - 2  # e o período também
