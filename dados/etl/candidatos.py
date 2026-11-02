"""Gera dados/parquet/candidatos.parquet (contrato 2: Lucas -> Roger).

Lista os estabelecimentos do recorte para os quais o enriquecimento vai procurar o site.
Segue o contrato (contratos/02_candidatos.md) e o relatório técnico:
  - todas as situações cadastrais entram (empresas baixadas também: o domínio do e-mail
    continua na base e permite buscar o site arquivado);
  - sem telefone e sem e-mail completo, só `dominio_email` (provedores genéricos viram NULL);
  - `razao_social` existe só para busca manual e NÃO pode ser exibida (MEI traz o nome do titular).
Arquivo de uso interno do pipeline: nunca versionar (o .gitignore já cobre *.parquet).

Uso: python -m dados.etl.candidatos
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from dados.etl.baixar import CONFIG_PADRAO, RAIZ, carregar_config
from dados.etl.filtrar import q

COLUNAS = ["cnpj", "nome_fantasia", "razao_social", "dominio_email", "municipio", "uf", "situacao",
           "cnae_principal"]


def gerar(cfg: dict) -> Path:
    base = RAIZ / cfg["caminhos"]["parquet"]
    destino = base / "candidatos.parquet"
    pendentes = [p for p in ("estabelecimentos", "empresas", "dominio/municipios.parquet")
                 if not (base / p).exists()]
    if pendentes:
        raise SystemExit(f"ERRO: faltam saídas do filtro em {base}: {', '.join(pendentes)}. "
                         "Rode python -m dados.etl.filtrar antes.")

    glob = lambda sub: q((base / sub / "parte_*.parquet").as_posix())  # noqa: E731
    con = duckdb.connect()
    consulta = f"""
        SELECT e.cnpj,
               nullif(trim(e.nome_fantasia), '')                 AS nome_fantasia,
               nullif(trim(emp.razao_social), '')                AS razao_social,
               e.dominio_email,
               m.descricao                                       AS municipio,
               e.uf,
               e.situacao_cadastral                              AS situacao,
               e.cnae_fiscal_principal                           AS cnae_principal
        FROM read_parquet({glob('estabelecimentos')}) e
        LEFT JOIN read_parquet({glob('empresas')}) emp USING (cnpj_basico)
        LEFT JOIN read_parquet({q((base / 'dominio' / 'municipios.parquet').as_posix())}) m
               ON m.codigo = e.municipio
        ORDER BY e.cnpj"""
    esperado = con.execute(f"SELECT count(*) FROM read_parquet({glob('estabelecimentos')})").fetchone()[0]
    provisorio = destino.with_name(destino.name + ".tmp")
    provisorio.unlink(missing_ok=True)
    escritas = con.execute(f"COPY ({consulta}) TO {q(provisorio.as_posix())} "
                           "(FORMAT PARQUET, COMPRESSION ZSTD)").fetchone()[0]
    if escritas != esperado:
        raise SystemExit(f"ERRO: candidatos tem {escritas:,} linhas e estabelecimentos {esperado:,} "
                         "(join duplicou ou perdeu linhas). Nada foi gravado.")
    provisorio.replace(destino)
    print(f"candidatos.parquet: {escritas:,} linhas -> {destino.relative_to(RAIZ)}")
    return destino


if __name__ == "__main__":
    gerar(carregar_config(CONFIG_PADRAO))
    sys.exit(0)
