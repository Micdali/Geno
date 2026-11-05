"""
Gabarito — empresas anotadas à mão (campos da classificação do contrato 3), para
medir a precisão da LLM do Micael. Carrega a tabela `gabarito` do geno.duckdb a
partir de um CSV de empresas reais (default: dados/empresas_reais.csv).

Uso:
    python -m enriquecimento.gabarito [caminho_empresas.csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import config, io_contratos

ANOTADOR = "roger (assistido por IA)"
CAMPOS = ["cnpj", "publico_atendido", "produto_servico", "canal_atendimento",
          "problema_resolvido", "modelo_receita"]


def carregar(con, caminho: str | Path | None = None) -> int:
    origem = Path(caminho) if caminho else config.PASTA_ENRIQUECIMENTO / "dados" / "empresas_reais.csv"
    df = pd.read_csv(origem, dtype=str).fillna("")
    falta = [c for c in CAMPOS if c not in df.columns]
    if falta:
        raise ValueError(f"CSV sem colunas do gabarito: {falta}")
    g = df[CAMPOS].copy()
    g["anotador"] = ANOTADOR
    g["anotado_em"] = pd.Timestamp.now()

    con.register("_gab", g)
    con.execute(
        """
        INSERT OR REPLACE INTO gabarito
            (cnpj, publico_atendido, produto_servico, canal_atendimento,
             problema_resolvido, modelo_receita, anotador, anotado_em)
        SELECT cnpj, publico_atendido, produto_servico, canal_atendimento,
               problema_resolvido, modelo_receita, anotador, anotado_em
        FROM _gab
        """
    )
    con.unregister("_gab")
    return len(g)


def main(caminho: str | None = None) -> None:
    con = io_contratos.conectar()
    try:
        io_contratos.criar_tabelas(con)
        n = carregar(con, caminho)
        total = con.execute("SELECT count(*) FROM gabarito").fetchone()[0]
        print(f"[gabarito] {n} empresa(s) anotada(s); total na tabela: {total}")
        print(con.execute(
            "SELECT modelo_receita, count(*) FROM gabarito GROUP BY modelo_receita ORDER BY 2 DESC"
        ).df().to_string(index=False))
    finally:
        con.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
