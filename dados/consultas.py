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


def saturacao(cnpjs: list[str], ano_inicial: int) -> pd.DataFrame:
    """Série de aberturas e baixas por ano para um conjunto de empresas.

    Retorna as colunas: ano, aberturas, baixas.
    Deve ignorar baixas em massa feitas pela Receita (tratadas pelo motivo da situação).
    """
    raise NotImplementedError("Lucas: implementar (ver seção 10.2 do relatório técnico)")


def saturacao_setor_amplo(ano_inicial: int) -> pd.DataFrame:
    """Mesma série, mas para todo o setor piloto.

    É o recuo usado quando o nicho tem poucas empresas fechadas classificadas.
    Nesse caso, o indicador de confiança avisa que não é o nicho exato.
    """
    raise NotImplementedError("Lucas: implementar")


def dados_publicos(cnpjs: list[str]) -> pd.DataFrame:
    """Dados exibíveis das empresas (lê só vw_publico: sem sócios, sem nome de titular de MEI)."""
    raise NotImplementedError("Lucas: implementar")
