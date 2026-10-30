"""Validação final do ETL: contagens do recorte, cobertura de e-mail, rejeitados e tamanho.

Uso: python -m dados.etl.validar
"""
from __future__ import annotations

import csv
import sys

import duckdb

from dados.etl.baixar import CONFIG_PADRAO, RAIZ, carregar_config
from dados.etl.filtrar import cnaes_do_recorte, q

SITUACOES = {"01": "nula", "02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada"}


def tabela(titulo: str, linhas: list[tuple], cabecalho: tuple) -> None:
    print(f"\n{titulo}")
    larguras = [max(len(str(x)) for x in col) for col in zip(cabecalho, *linhas)]
    for linha in (cabecalho, *linhas):
        print("  " + "  ".join(str(v).ljust(w) if i == 0 else str(v).rjust(w)
                               for i, (v, w) in enumerate(zip(linha, larguras))))


def main() -> int:
    cfg = carregar_config(CONFIG_PADRAO)
    base = RAIZ / cfg["caminhos"]["parquet"]
    glob = lambda sub: q((base / sub / "parte_*.parquet").as_posix())  # noqa: E731
    est = f"read_parquet({glob('estabelecimentos')})"
    con = duckdb.connect()
    um = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731

    total = um(f"SELECT count(*) FROM {est}")
    print(f"Recorte: UF={cfg['recorte']['uf']}, CNAEs={', '.join(cnaes_do_recorte(cfg))}")
    print(f"Competência: {cfg['fonte']['competencia']}")
    print(f"\nEstabelecimentos no recorte: {total:,}")
    print(f"  CNPJ de 14 posições únicos: {um(f'SELECT count(DISTINCT cnpj) FROM {est}'):,}")
    print(f"  Raízes de CNPJ (empresas) distintas: {um(f'SELECT count(DISTINCT cnpj_basico) FROM {est}'):,}")

    linhas = con.execute(f"SELECT situacao_cadastral, count(*) FROM {est} GROUP BY 1 ORDER BY 1").fetchall()
    tabela("Por situação cadastral",
           [(f"{s} {SITUACOES.get(s, '?')}", f"{n:,}", f"{100 * n / total:.1f}%") for s, n in linhas],
           ("situação", "estabelecimentos", "%"))

    dom = q((base / "dominio" / "cnaes.parquet").as_posix())
    linhas = con.execute(f"""SELECT e.cnae_fiscal_principal, coalesce(c.descricao, '?'), count(*)
                             FROM {est} e LEFT JOIN read_parquet({dom}) c ON c.codigo = e.cnae_fiscal_principal
                             GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15""").fetchall()
    tabela("Por CNAE principal (15 maiores)", [(c, d[:45], f"{n:,}") for c, d, n in linhas],
           ("cnae", "descrição", "estabelecimentos"))
    fora = um(f"SELECT count(*) FROM {est} WHERE cnae_fiscal_principal NOT IN ({', '.join(q(c) for c in cnaes_do_recorte(cfg))})")
    print(f"  Entraram só pelo CNAE secundário (principal fora do setor): {fora:,}")

    ativos = um(f"SELECT count(*) FROM {est} WHERE situacao_cadastral = '02'")
    ativos_dom = um(f"SELECT count(*) FROM {est} WHERE situacao_cadastral = '02' AND dominio_email IS NOT NULL")
    todos_dom = um(f"SELECT count(*) FROM {est} WHERE dominio_email IS NOT NULL")
    baix = um(f"SELECT count(*) FROM {est} WHERE situacao_cadastral = '08'")
    baix_dom = um(f"SELECT count(*) FROM {est} WHERE situacao_cadastral = '08' AND dominio_email IS NOT NULL")
    print("\nCobertura de dominio_email (indicador de quantas empresas terão site provável)")
    print(f"  Ativos com dominio_email:   {ativos_dom:,} de {ativos:,} ({100 * ativos_dom / max(ativos, 1):.1f}%)")
    print(f"  Baixados com dominio_email: {baix_dom:,} de {baix:,} ({100 * baix_dom / max(baix, 1):.1f}%)")
    print(f"  Todos:                      {todos_dom:,} de {total:,} ({100 * todos_dom / total:.1f}%)")
    print(f"  Domínios distintos: {um(f'SELECT count(DISTINCT dominio_email) FROM {est}'):,}")
    topo = con.execute(f"""SELECT dominio_email, count(*) FROM {est} WHERE dominio_email IS NOT NULL
                           GROUP BY 1 ORDER BY 2 DESC LIMIT 5""").fetchall()
    print("  Mais repetidos (provável contador ou provedor a descartar no enriquecimento): "
          + ", ".join(f"{d} ({n})" for d, n in topo))

    emp = f"read_parquet({glob('empresas')})"
    sim = f"read_parquet({glob('simples')})"
    n_emp, n_sim = um(f"SELECT count(*) FROM {emp}"), um(f"SELECT count(*) FROM {sim}")
    n_raiz = um(f"SELECT count(DISTINCT cnpj_basico) FROM {est}")
    sem_emp = um(f"SELECT count(DISTINCT cnpj_basico) FROM {est} WHERE cnpj_basico NOT IN (SELECT cnpj_basico FROM {emp})")
    print(f"\nEmpresas: {n_emp:,} linhas ({sem_emp:,} raízes do recorte sem linha em Empresas)")
    print(f"Simples:  {n_sim:,} linhas (nem toda empresa tem registro; raízes no recorte: {n_raiz:,})")

    cand = base / "candidatos.parquet"
    if cand.exists():
        n_cand = um(f"SELECT count(*) FROM read_parquet({q(cand.as_posix())})")
        print(f"candidatos.parquet: {n_cand:,} linhas (esperado {total:,}) {'OK' if n_cand == total else 'DIVERGE'}")
    else:
        print("candidatos.parquet: ainda não gerado")

    rej_total = 0
    log = RAIZ / cfg["caminhos"]["log"]
    if log.exists():
        with open(log, encoding="utf-8") as f:
            rej_total = sum(int(r["linhas_rejeitadas"]) for r in csv.DictReader(f))
    print(f"\nLinhas rejeitadas (malformadas) em todos os arquivos: {rej_total:,}")
    rej = RAIZ / cfg["caminhos"]["rejeitados"]
    if rej_total and rej.exists():
        with open(rej, encoding="utf-8") as f:
            for r in list(csv.DictReader(f))[:5]:
                print(f"  {r['arquivo']} linha {r['linha']}: {r['tipo_erro']} ({r['coluna']}) {r['linha_csv'][:120]}")

    tam = sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
    print(f"\nTamanho de {base.relative_to(RAIZ)}/: {tam / 1e6:,.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
