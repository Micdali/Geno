"""Monta o banco dados/geno.duckdb a partir dos Parquet do ETL (dono: Lucas).

Cria as tabelas do contrato 1 (contratos/01_schema.sql), carrega a camada 1 (identidade) já com
tipos tratados, preenche motivo_tipo a partir do config.yaml e aplica dados/sql/02_views.sql.
As camadas 2 a 4 ficam criadas e vazias (são preenchidas por Roger e Micael).

O banco é montado num arquivo provisório e só substitui o anterior depois de validado.

Uso: python -m dados.etl.construir_db
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from dados.etl.baixar import CONFIG_PADRAO, RAIZ, carregar_config
from dados.etl.filtrar import cnaes_do_recorte, q

SCHEMA = RAIZ / "contratos" / "01_schema.sql"
VIEWS = RAIZ / "dados" / "sql" / "02_views.sql"


def data(coluna: str) -> str:
    """AAAAMMDD -> DATE; vazio, 00000000 e datas impossíveis viram NULL."""
    return f"try_strptime(nullif(nullif({coluna}, '00000000'), ''), '%Y%m%d')::DATE"


def carregar(con: duckdb.DuckDBPyConnection, cfg: dict) -> None:
    base = RAIZ / cfg["caminhos"]["parquet"]
    pq = lambda sub: q((base / sub).as_posix())  # noqa: E731
    cnaes = ", ".join(q(c) for c in cnaes_do_recorte(cfg))

    for tabela, arq in (("cnae", "cnaes"), ("municipio", "municipios"), ("motivo", "motivos"),
                        ("natureza", "naturezas")):
        con.execute(f"INSERT INTO {tabela} SELECT codigo, descricao FROM read_parquet({pq(f'dominio/{arq}.parquet')})")

    con.execute(f"""
        INSERT INTO empresa
        SELECT e.cnpj_basico,
               nullif(trim(e.razao_social), ''),
               e.natureza_juridica,
               e.porte_empresa,
               try_cast(replace(nullif(e.capital_social, ''), ',', '.') AS DECIMAL(18,2)),
               s.opcao_mei = 'S'                  -- NULL quando a empresa não está no Simples
        FROM read_parquet({pq('empresas/parte_*.parquet')}) e
        LEFT JOIN read_parquet({pq('simples/parte_*.parquet')}) s USING (cnpj_basico)""")

    con.execute(f"""
        INSERT INTO estabelecimento
        SELECT cnpj,
               cnpj_basico,
               identificador_matriz_filial = '1',
               nullif(trim(nome_fantasia), ''),
               situacao_cadastral,
               {data('data_situacao_cadastral')},
               nullif(motivo_situacao_cadastral, ''),
               {data('data_inicio_atividade')},
               cnae_fiscal_principal,
               CASE WHEN coalesce(cnae_fiscal_secundaria, '') = '' THEN []::VARCHAR[]
                    ELSE string_split(cnae_fiscal_secundaria, ',') END,
               cnae_fiscal_principal NOT IN ({cnaes}),   -- entrou só pela atividade secundária
               uf,
               municipio,
               nullif(trim(bairro), ''),
               nullif(cep, ''),
               dominio_email
        FROM read_parquet({pq('estabelecimentos/parte_*.parquet')})""")

    linhas = [(cod, tipo) for tipo, cods in cfg["baixas"].items() for cod in cods]
    con.executemany("INSERT INTO motivo_tipo VALUES (?, ?)", linhas)


def conferir(con: duckdb.DuckDBPyConnection, cfg: dict) -> None:
    """Contagens do banco contra os Parquet de origem; qualquer divergência aborta."""
    base = RAIZ / cfg["caminhos"]["parquet"]
    um = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    pq = lambda sub: q((base / sub).as_posix())  # noqa: E731
    pares = [
        ("estabelecimento", f"SELECT count(*) FROM read_parquet({pq('estabelecimentos/parte_*.parquet')})"),
        ("empresa", f"SELECT count(*) FROM read_parquet({pq('empresas/parte_*.parquet')})"),
        ("municipio", f"SELECT count(*) FROM read_parquet({pq('dominio/municipios.parquet')})"),
        ("cnae", f"SELECT count(*) FROM read_parquet({pq('dominio/cnaes.parquet')})"),
        ("motivo", f"SELECT count(*) FROM read_parquet({pq('dominio/motivos.parquet')})"),
        ("natureza", f"SELECT count(*) FROM read_parquet({pq('dominio/naturezas.parquet')})"),
    ]
    for tabela, sql_origem in pares:
        banco, origem = um(f"SELECT count(*) FROM {tabela}"), um(sql_origem)
        print(f"  {tabela:16s} {banco:>9,} (parquet {origem:,})")
        if banco != origem:
            raise SystemExit(f"ERRO: {tabela} tem {banco:,} linhas no banco e {origem:,} no Parquet.")
    # Join com Simples não pode ter duplicado nem perdido empresas (verificado acima em `empresa`),
    # e toda data de abertura precisa ter sido lida (nenhum AAAAMMDD inválido no recorte).
    sem_data = um("SELECT count(*) FROM estabelecimento WHERE data_inicio IS NULL")
    print(f"  estabelecimentos sem data_inicio: {sem_data:,}")
    if sem_data:
        raise SystemExit("ERRO: há datas de início que não foram convertidas.")
    orfaos = um("SELECT count(*) FROM estabelecimento e WHERE NOT EXISTS "
                "(SELECT 1 FROM empresa m WHERE m.cnpj_basico = e.cnpj_basico)")
    print(f"  estabelecimentos sem empresa: {orfaos:,}")
    if orfaos:
        raise SystemExit("ERRO: estabelecimentos sem linha em empresa.")


def main() -> int:
    cfg = carregar_config(CONFIG_PADRAO)
    destino = RAIZ / cfg["caminhos"]["db"]
    provisorio = destino.with_name(destino.name + ".tmp")
    for p in (provisorio, provisorio.with_name(provisorio.name + ".wal")):
        p.unlink(missing_ok=True)
    if not (RAIZ / cfg["caminhos"]["parquet"] / "estabelecimentos").exists():
        raise SystemExit("ERRO: faltam os Parquet do ETL. Rode python -m dados.etl.filtrar antes.")

    con = duckdb.connect(str(provisorio))
    con.execute(SCHEMA.read_text(encoding="utf-8"))
    con.execute(VIEWS.read_text(encoding="utf-8"))
    carregar(con, cfg)
    print(f"Banco montado em {destino.relative_to(RAIZ)}:")
    conferir(con, cfg)
    con.execute("CHECKPOINT")
    con.close()
    provisorio.replace(destino)
    print(f"OK: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1e6:,.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
