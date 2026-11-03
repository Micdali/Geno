"""Comando único: recria o geno.duckdb do zero (dono: Lucas).

Encadeia as etapas do bloco de dados, nesta ordem, e mostra quanto cada uma levou:
  1. filtrar     ZIPs da Receita -> Parquet do recorte (baixa um ZIP por vez e apaga depois de validar)
  2. candidatos  candidatos.parquet (contrato 2)
  3. construir   geno.duckdb, views, e no fim METRICAS.md e metricas.json

    python -m dados.etl.recriar                  # do zero, com download (≈ 7,1 GB)
    python -m dados.etl.recriar --sem-download   # reaproveita os Parquet que já existem em dados/parquet/

Os parâmetros (UF, CNAEs, competência, período, limiares) vêm de dados/config.yaml. Etapas que já têm
saída pronta são puladas pelo `filtrar`; use --refazer para reprocessar tudo.
"""
from __future__ import annotations

import argparse
import sys
import time

from dados.etl import candidatos, construir_db, filtrar
from dados.etl.baixar import CONFIG_PADRAO, carregar_config


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Recria o geno.duckdb do zero")
    ap.add_argument("--sem-download", action="store_true",
                    help="não baixa nada: usa os Parquet de dados/parquet/ (falha se não existirem)")
    ap.add_argument("--refazer", action="store_true", help="reprocessa os ZIPs mesmo que o Parquet já exista")
    args = ap.parse_args(argv)

    tempos: list[tuple[str, float]] = []

    def etapa(nome: str, fn) -> None:
        print(f"\n===== {nome} =====", flush=True)
        t0 = time.time()
        rc = fn()
        tempos.append((nome, time.time() - t0))
        if rc not in (None, 0):
            print(f"\nERRO na etapa '{nome}' (código {rc}). Parado.", file=sys.stderr)
            raise SystemExit(rc)

    filtro_args = [] if args.sem_download else ["--baixar"]
    if args.refazer:
        filtro_args.append("--refazer")
    etapa("1/3 filtrar (Receita -> Parquet)", lambda: filtrar.main(filtro_args))
    def gerar_candidatos() -> int:
        candidatos.gerar(carregar_config(CONFIG_PADRAO))
        return 0

    etapa("2/3 candidatos.parquet", gerar_candidatos)
    etapa("3/3 geno.duckdb, views e métricas", construir_db.main)

    print("\n===== tempos =====")
    for nome, s in tempos:
        print(f"  {nome:40s} {int(s // 60)} min {int(s % 60):02d} s")
    print(f"  {'total':40s} {int(sum(s for _, s in tempos) // 60)} min {int(sum(s for _, s in tempos) % 60):02d} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
