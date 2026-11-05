"""
Fronteira de dados da camada 2 (Roger).

Entra: candidatos.parquet (contrato 2) — ou o CSV de exemplo enquanto o parquet
       real do Lucas não existir.
Sai:   tabelas DuckDB candidato_dominio, pagina, gabarito (contrato 1), criadas
       de forma idempotente no geno.duckdb.

Uso:
    python -m enriquecimento.io_contratos
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from . import config

# Colunas de texto que nunca podem virar número (CNPJ, códigos com zero à esquerda)
_COLUNAS_TEXTO = {"cnpj", "situacao", "cnae_principal", "uf"}


def ler_candidatos(caminho: str | Path | None = None) -> pd.DataFrame:
    """Lê os candidatos do contrato 2.

    Ordem de busca quando `caminho` não é dado:
    1. parquet real do Lucas (dados/parquet/candidatos.parquet), se existir;
    2. CSV de exemplo (enriquecimento/dados/exemplos/candidatos.exemplo.csv).

    Garante que todas as colunas do contrato existam e que os códigos fiquem
    como texto (CNPJ, situacao, cnae_principal, uf).
    """
    if caminho is not None:
        caminho = Path(caminho)
        df = _ler_arquivo(caminho)
        origem = str(caminho)
    elif config.PARQUET_CANDIDATOS.exists():
        df = pd.read_parquet(config.PARQUET_CANDIDATOS)
        origem = str(config.PARQUET_CANDIDATOS)
    else:
        df = pd.read_csv(config.EXEMPLO_CANDIDATOS, dtype=str)
        origem = f"{config.EXEMPLO_CANDIDATOS} (exemplo — parquet do Lucas ainda não existe)"

    df = _normalizar(df)
    print(f"[candidatos] {len(df)} linhas de: {origem}")
    return df


def _ler_arquivo(caminho: Path) -> pd.DataFrame:
    if caminho.suffix.lower() == ".parquet":
        return pd.read_parquet(caminho)
    return pd.read_csv(caminho, dtype=str)


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    faltando = [c for c in config.COLUNAS_CANDIDATOS if c not in df.columns]
    if faltando:
        raise ValueError(
            f"candidatos sem as colunas do contrato 2: {faltando}. "
            f"Esperado: {config.COLUNAS_CANDIDATOS}"
        )
    df = df[config.COLUNAS_CANDIDATOS].copy()

    # Códigos sempre como texto (CNPJ alfanumérico; zeros à esquerda importam)
    for col in _COLUNAS_TEXTO:
        df[col] = df[col].astype("string").str.strip()
    # CNPJ: 14 posições, preenchendo zero à esquerda quando vier numérico
    df["cnpj"] = df["cnpj"].str.replace(r"\D", "", regex=True).str.zfill(14)
    return df


def conectar(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Abre (ou cria) o geno.duckdb."""
    return duckdb.connect(str(db_path or config.DUCKDB_PATH))


def criar_tabelas(con: duckdb.DuckDBPyConnection) -> None:
    """Cria/garante as tabelas da camada 2 (idempotente)."""
    sql = (config.PASTA_SQL / "schema_camada2.sql").read_text(encoding="utf-8")
    con.execute(sql)


def _resumo(con: duckdb.DuckDBPyConnection) -> None:
    for tabela in ("candidato_dominio", "pagina", "gabarito"):
        (n,) = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()
        print(f"[duckdb] {tabela}: {n} linhas")


def main() -> None:
    df = ler_candidatos()
    print(df.to_string(index=False))

    con = conectar()
    try:
        criar_tabelas(con)
        print(f"[duckdb] tabelas da camada 2 prontas em: {config.DUCKDB_PATH}")
        _resumo(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
