"""Caminhos e configuração do módulo de enriquecimento."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# geno/ (raiz do projeto local) = pai da pasta enriquecimento/
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# Pastas
PASTA_ENRIQUECIMENTO = RAIZ / "enriquecimento"
PASTA_SQL = PASTA_ENRIQUECIMENTO / "sql"

# Exemplo do contrato 2. No repo é contratos/exemplos/candidatos.exemplo.csv (RJ);
# fora dele, cai no exemplo local. Usa o primeiro que existir.
_EXEMPLOS = [
    RAIZ / "contratos" / "exemplos" / "candidatos.exemplo.csv",
    PASTA_ENRIQUECIMENTO / "dados" / "exemplos" / "candidatos.exemplo.csv",
]
EXEMPLO_CANDIDATOS = next((p for p in _EXEMPLOS if p.exists()), _EXEMPLOS[-1])

# candidatos.parquet real do Lucas (fora do Git) — usado quando existir
PARQUET_CANDIDATOS = RAIZ / "dados" / "parquet" / "candidatos.parquet"

# Banco DuckDB (único arquivo compartilhado do projeto)
DUCKDB_PATH = RAIZ / os.getenv("GENO_DUCKDB", "geno.duckdb")

# Coleta responsável
USER_AGENT = os.getenv(
    "GENO_USER_AGENT",
    "GENO-pesquisa-academica/0.1 (+contato: configure o .env)",
)

# Colunas do contrato 2 (candidatos.parquet). Tudo texto; nunca tratar CNPJ como número.
COLUNAS_CANDIDATOS = [
    "cnpj",
    "nome_fantasia",
    "razao_social",
    "dominio_email",
    "municipio",
    "uf",
    "situacao",
    "cnae_principal",
]
