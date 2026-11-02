"""Testes de dados/geno_db/consultas.py contra o geno.duckdb real.

As conferências usam SQL direto sobre a tabela `estabelecimento`, independente do código testado.
Rodar da raiz do repositório, depois de python -m dados.etl.construir_db:
    python -m pytest tests/test_consultas.py -v
"""
from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from dados.geno_db import consultas

CNAE = "8593700"          # ensino de idiomas: nicho grande e conhecido
CNAE_RECUO = "8599699"    # nicho cuja classe e cujo grupo são maiores que a subclasse


@pytest.fixture(scope="module")
def con():
    p = consultas.caminho_banco()
    if not p.exists():
        pytest.fail(f"{p} não existe. Rode: python -m dados.etl.construir_db")
    c = duckdb.connect(str(p), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="module")
def municipio_maior(con):
    """Município (código da Receita) com mais estabelecimentos do CNAE de teste."""
    return con.execute("SELECT municipio_cod FROM estabelecimento WHERE cnae_principal = ? "
                       "GROUP BY 1 ORDER BY count(*) DESC LIMIT 1", [CNAE]).fetchone()[0]


def _diretas(con, prefixo, ini, fim, municipio=None, secundario=False):
    """Aberturas por contagem direta, sem passar pelas funções do módulo."""
    cond = "starts_with(cnae_principal, ?)"
    params = [prefixo]
    if secundario:
        cond = "(starts_with(cnae_principal, ?) OR len(list_filter(cnaes_secundarios, lambda x: starts_with(x, ?))) > 0)"
        params = [prefixo, prefixo]
    mun = ""
    if municipio:
        mun, params = " AND municipio_cod = ?", params + [municipio]
    return con.execute(f"SELECT count(*) FROM estabelecimento WHERE {cond}{mun} "
                       "AND year(data_inicio) BETWEEN ? AND ?", params + [ini, fim]).fetchone()[0]


@pytest.mark.parametrize("secundario", [False, True])
@pytest.mark.parametrize("com_municipio", [False, True])
def test_soma_das_aberturas_bate_com_contagem_direta(con, municipio_maior, secundario, com_municipio):
    mun = municipio_maior if com_municipio else None
    df = consultas.saturacao([CNAE], municipio=mun, ano_ini=2015, ano_fim=2025, usar_secundario=secundario)
    esperado = _diretas(con, CNAE, 2015, 2025, mun, secundario)
    assert esperado > 100, "teste sem força: nicho pequeno demais"
    assert int(df["aberturas"].sum()) == esperado


def test_colunas_e_tipos_de_saturacao(con):
    df = consultas.saturacao([CNAE])
    assert list(df.columns) == ["ano", "aberturas", "baixas", "baixas_oficio", "saldo", "ativos_fim_ano"]
    assert all(pd.api.types.is_integer_dtype(df[c]) for c in df.columns), df.dtypes
    assert list(df["ano"]) == [2021, 2022, 2023, 2024, 2025]            # período padrão do config.yaml
    assert (df["baixas_oficio"] <= df["baixas"]).all()
    assert (df["saldo"] == df["aberturas"] - (df["baixas"] - df["baixas_oficio"])).all()
    todas = consultas.saturacao([CNAE], excluir_oficio=False)
    assert (todas["saldo"] == todas["aberturas"] - todas["baixas"]).all()
    # 2021 tem baixas de ofício neste nicho, então as duas formas de saldo diferem
    assert int(df["baixas_oficio"].sum()) > 0 and (df["saldo"] != todas["saldo"]).any()


def test_ativos_fim_ano_bate_com_contagem_direta(con):
    df = consultas.saturacao([CNAE], ano_ini=2020, ano_fim=2025)
    for ano, ativos in zip(df["ano"], df["ativos_fim_ano"]):
        fim = f"{ano}-12-31"
        direto = con.execute(
            "SELECT count(*) FROM estabelecimento WHERE starts_with(cnae_principal, ?) AND data_inicio <= ?::DATE "
            "AND NOT (situacao = '08' AND data_situacao <= ?::DATE)", [CNAE, fim, fim]).fetchone()[0]
        assert ativos == direto, ano


def test_colunas_e_tipos_de_mortalidade():
    r = consultas.mortalidade_setor([CNAE])
    assert set(r) == {"dados", "nivel_usado", "cnaes_usados", "n_estab"}
    df = r["dados"]
    assert list(df.columns) == ["ano_coorte", "abertos", "baixados", "baixados_oficio", "taxa"]
    assert pd.api.types.is_float_dtype(df["taxa"])
    assert all(pd.api.types.is_integer_dtype(df[c]) for c in ["ano_coorte", "abertos", "baixados", "baixados_oficio"])
    assert ((df["taxa"] >= 0) & (df["taxa"] <= 1)).all()
    assert isinstance(r["n_estab"], int) and isinstance(r["cnaes_usados"], list)


def test_taxa_da_coorte_bate_com_contagem_direta(con):
    df = consultas.mortalidade_setor([CNAE], ano_ini=2018, ano_fim=2025, horizonte=2)["dados"]
    linha = df[df["ano_coorte"] == 2019].iloc[0]
    abertos, baixados = con.execute("""
        SELECT count(*), count(*) FILTER (WHERE e.situacao = '08' AND coalesce(mc.classe, '') <> 'oficio'
                                            AND year(e.data_situacao) <= 2019 + 2)
        FROM estabelecimento e LEFT JOIN motivo_classe mc ON mc.codigo_motivo = e.motivo_situacao
        WHERE e.cnae_principal = ? AND year(e.data_inicio) = 2019""", [CNAE]).fetchone()
    assert (linha["abertos"], linha["baixados"]) == (abertos, baixados)
    assert linha["taxa"] == pytest.approx(baixados / abertos)


def _n_diretos(con, prefixo):
    return _diretas(con, prefixo, 2021, 2025)


def test_recuo_dispara_e_retorna_o_nivel_certo(con):
    n7, n5, n3 = (_n_diretos(con, CNAE_RECUO[:k]) for k in (7, 5, 3))
    assert n7 < n5 < n3, f"teste sem força: {n7}, {n5}, {n3} não crescem"
    casos = [
        (n7,         "subclasse", CNAE_RECUO,      n7),   # nicho já atinge o mínimo
        (n7 + 1,     "classe",    CNAE_RECUO[:5],  n5),   # subclasse insuficiente, classe basta
        (n5 + 1,     "grupo",     CNAE_RECUO[:3],  n3),   # classe insuficiente, grupo basta
        (10**9,      "grupo",     CNAE_RECUO[:3],  n3),   # limiar impossível: usa o grupo mesmo assim
    ]
    for minimo, nivel, prefixo, n in casos:
        r = consultas.mortalidade_setor([CNAE_RECUO], min_estab=minimo)
        assert (r["nivel_usado"], r["cnaes_usados"], r["n_estab"]) == (nivel, [prefixo], n), minimo


def test_recuo_nao_vai_para_nivel_mais_fino_que_o_informado():
    r = consultas.mortalidade_setor(["859"], min_estab=10**9)
    assert (r["nivel_usado"], r["cnaes_usados"]) == ("grupo", ["859"])


@pytest.mark.parametrize("ano_fim,horizonte", [(2025, 2), (2025, 3), (2024, 3), (2023, 1)])
def test_coortes_incompletas_nao_aparecem(ano_fim, horizonte):
    df = consultas.mortalidade_setor([CNAE], ano_ini=2018, ano_fim=ano_fim, horizonte=horizonte)["dados"]
    assert not df.empty
    assert df["ano_coorte"].max() == ano_fim - horizonte      # a coorte mais nova que completou o horizonte
    assert df["ano_coorte"].min() >= 2018
    assert list(df["ano_coorte"]) == sorted(df["ano_coorte"])


def test_entradas_invalidas_sao_recusadas():
    for ruim in ["8593700'; DROP TABLE estabelecimento; --", "85937", "", "abc", "12"]:
        if len(ruim) in range(3, 8) and ruim.isdigit():
            continue
        with pytest.raises(ValueError):
            consultas.saturacao([ruim])
    with pytest.raises(ValueError):
        consultas.saturacao("8593700")                         # string solta, não lista
    with pytest.raises(ValueError):
        consultas.saturacao([CNAE], ano_ini=2025, ano_fim=2021)
    with pytest.raises(ValueError):
        consultas.mortalidade_setor([CNAE], horizonte=0)


def test_conexao_e_somente_leitura():
    con = consultas.conectar()
    try:
        with pytest.raises(duckdb.Error):
            con.execute("CREATE TABLE intruso (x INTEGER)")
    finally:
        con.close()
