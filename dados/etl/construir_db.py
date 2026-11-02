"""Monta o banco dados/geno.duckdb a partir dos Parquet do ETL (dono: Lucas).

Cria as tabelas do contrato 1 (contratos/01_schema.sql), carrega a camada 1 (identidade) já com
tipos tratados, carrega o seed motivo_classe aplica as views de dados/sql/ e, no fim, gera as métricas (etl/gerar_metricas.py).
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
SCHEMA_EXTRA = RAIZ / "dados" / "sql" / "01_schema_extra.sql"
VIEWS = [RAIZ / "dados" / "sql" / n for n in ("02_views.sql", "03_views_publicas.sql")]


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

    for tabela, arq in (("pais", "paises"), ("qualificacao", "qualificacoes")):
        con.execute(f"INSERT INTO {tabela} SELECT codigo, descricao FROM read_parquet({pq(f'dominio/{arq}.parquet')})")
    con.executemany("INSERT INTO situacao_cadastral VALUES (?, ?)", list(cfg["situacao_cadastral"].items()))

    con.execute(f"""
        INSERT INTO simples
        SELECT cnpj_basico, nullif(opcao_simples, ''),
               {data('data_opcao_simples')}, {data('data_exclusao_simples')},
               nullif(opcao_mei, ''),
               {data('data_opcao_mei')}, {data('data_exclusao_mei')}
        FROM read_parquet({pq('simples/parte_*.parquet')})""")

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

    seed = RAIZ / cfg["caminhos"]["seed_motivos"]
    con.execute(f"INSERT INTO motivo_classe SELECT * FROM read_csv({q(seed.as_posix())}, header=true, all_varchar=true)")
    codigos_seed = {r[0] for r in con.execute("SELECT codigo_motivo FROM motivo_classe").fetchall()}
    codigos_motivo = {r[0] for r in con.execute("SELECT codigo FROM motivo").fetchall()}
    if codigos_seed != codigos_motivo:
        raise SystemExit(f"ERRO: o seed {seed.name} não cobre exatamente a tabela motivo "
                         f"(faltam {sorted(codigos_motivo - codigos_seed)}, sobram {sorted(codigos_seed - codigos_motivo)}).")
    ruins = con.execute("SELECT DISTINCT classe FROM motivo_classe WHERE classe NOT IN ('voluntaria', 'oficio', 'outra')").fetchall()
    if ruins:
        raise SystemExit(f"ERRO: classes inválidas no seed: {[r[0] for r in ruins]}")


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
        ("pais", f"SELECT count(*) FROM read_parquet({pq('dominio/paises.parquet')})"),
        ("qualificacao", f"SELECT count(*) FROM read_parquet({pq('dominio/qualificacoes.parquet')})"),
        ("simples", f"SELECT count(*) FROM read_parquet({pq('simples/parte_*.parquet')})"),
    ]
    for tabela, sql_origem in pares:
        banco, origem = um(f"SELECT count(*) FROM {tabela}"), um(sql_origem)
        print(f"  {tabela:16s} {banco:>9,} (parquet {origem:,})")
        if banco != origem:
            raise SystemExit(f"ERRO: {tabela} tem {banco:,} linhas no banco e {origem:,} no Parquet.")
    # Join com Simples não pode ter duplicado nem perdido empresas (verificado acima em `empresa`),
    # e toda data de abertura precisa ter sido lida (nenhum AAAAMMDD inválido no recorte).
    sem_situacao = um("SELECT count(*) FROM estabelecimento e WHERE NOT EXISTS "
                      "(SELECT 1 FROM situacao_cadastral s WHERE s.codigo = e.situacao)")
    print(f"  estabelecimentos com situação fora do layout: {sem_situacao:,}")
    if sem_situacao:
        raise SystemExit("ERRO: há códigos de situação cadastral que não estão no layout oficial.")
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
    con.execute(SCHEMA_EXTRA.read_text(encoding="utf-8"))
    for arquivo in VIEWS:
        con.execute(arquivo.read_text(encoding="utf-8"))
    carregar(con, cfg)
    print(f"Banco montado em {destino.relative_to(RAIZ)}:")
    conferir(con, cfg)
    con.execute("CHECKPOINT")
    con.close()
    provisorio.replace(destino)
    print(f"OK: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1e6:,.1f} MB)")
    from dados.etl.gerar_metricas import gerar   # import tardio: precisa do banco já no lugar
    gerar()
    print("OK: dados/METRICAS.md e dados/metricas.json regenerados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
