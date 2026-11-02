"""Consultas sobre o geno.duckdb usadas pelo motor (dono: Lucas).

As assinaturas abaixo fazem parte do contrato entre dados/ e motor/.
Mudou uma assinatura? Avise o Micael antes (ver CONTRIBUTING.md).
"""
from __future__ import annotations

import os

import duckdb
import pandas as pd

DB_PATH = os.getenv("GENO_DB", "dados/geno.duckdb")


def conectar(somente_leitura: bool = True) -> duckdb.DuckDBPyConnection:
    """Abre o banco. O app e o motor sempre abrem em modo somente leitura."""
    return duckdb.connect(DB_PATH, read_only=somente_leitura)


def _serie(cnpjs: list[str] | None, ano_inicial: int) -> pd.DataFrame:
    """Aberturas e baixas por ano; cnpjs=None considera todo o recorte.

    Baixas de ofício (baixa_em_massa) ficam de fora; as demais contam (ver dados/sql/02_views.sql). O ano corrente é parcial.
    """
    filtro = "" if cnpjs is None else "AND cnpj IN (SELECT unnest(?::VARCHAR[]))"
    params = [] if cnpjs is None else [list(cnpjs)]
    sql = f"""
        SELECT ano,
               count(*) FILTER (WHERE tipo = 'abertura') AS aberturas,
               count(*) FILTER (WHERE tipo = 'baixa')    AS baixas
        FROM (
            SELECT ano_abertura AS ano, 'abertura' AS tipo
            FROM vw_eventos WHERE ano_abertura IS NOT NULL {filtro}
            UNION ALL
            SELECT ano_baixa, 'baixa'
            FROM vw_eventos WHERE NOT baixa_em_massa AND ano_baixa IS NOT NULL {filtro}
        ) t
        WHERE ano >= ?
        GROUP BY ano ORDER BY ano"""
    con = conectar()
    try:
        return con.execute(sql, params + params + [ano_inicial]).df()
    finally:
        con.close()


def saturacao(cnpjs: list[str], ano_inicial: int) -> pd.DataFrame:
    """Série de aberturas e baixas por ano para um conjunto de empresas.

    Retorna as colunas: ano, aberturas, baixas.
    Deve ignorar baixas em massa feitas pela Receita (tratadas pelo motivo da situação).
    """
    return _serie(cnpjs, ano_inicial)


def saturacao_setor_amplo(ano_inicial: int) -> pd.DataFrame:
    """Mesma série, mas para todo o setor piloto.

    É o recuo usado quando o nicho tem poucas empresas fechadas classificadas.
    Nesse caso, o indicador de confiança avisa que não é o nicho exato.
    """
    return _serie(None, ano_inicial)


def dados_publicos(cnpjs: list[str]) -> pd.DataFrame:
    """Dados exibíveis das empresas (lê só vw_publico: sem sócios, sem nome de titular de MEI)."""
    con = conectar()
    try:
        return con.execute(
            "SELECT * FROM vw_publico WHERE cnpj IN (SELECT unnest(?::VARCHAR[])) ORDER BY cnpj",
            [list(cnpjs)],
        ).df()
    finally:
        con.close()
