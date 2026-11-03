"""Copia o geno.duckdb para um Postgres do Supabase (dono: Lucas).

Lê a connection string da variável de ambiente SUPABASE_DB_URL (nunca de arquivo do projeto) e copia
todas as tabelas e views do banco local, usando a extensão postgres do DuckDB. As views viram tabelas
no Postgres (a sintaxe das views é de DuckDB). Depois liga o Row Level Security em todas as tabelas,
sem nenhuma policy: a API REST pública do Supabase (chave anon) não enxerga nada, e só quem tem a
connection string consegue ler.

    python -m dados.etl.publicar_supabase --listar     # só mostra o que seria copiado
    python -m dados.etl.publicar_supabase              # copia (apaga e recria as tabelas no schema 'geno')

Use a connection string do "Session pooler" (porta 5432 do pooler), que funciona em redes só IPv4.
Formato: postgresql://postgres.<ref>:<senha>@aws-0-<regiao>.pooler.supabase.com:5432/postgres
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import duckdb
import yaml

RAIZ = Path(__file__).resolve().parents[2]
SCHEMA_PG = "geno"


def caminho_db() -> Path:
    env = os.environ.get("GENO_DB")
    if env:
        return Path(env)
    cfg = yaml.safe_load((RAIZ / "dados" / "config.yaml").read_text(encoding="utf-8"))
    return RAIZ / cfg["caminhos"]["db"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Publica o geno.duckdb no Supabase")
    ap.add_argument("--listar", action="store_true", help="só lista tabelas e views e as contagens")
    args = ap.parse_args(argv)

    db = caminho_db()
    if not db.exists():
        print(f"ERRO: {db} não existe. Rode python -m dados.etl.construir_db.", file=sys.stderr)
        return 1
    local = duckdb.connect(str(db), read_only=True)
    objetos = [r[0] for r in local.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY 1").fetchall()]
    contagens = {t: local.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in objetos}
    local.close()

    print(f"{len(objetos)} objetos em {db.name}:")
    for t in objetos:
        print(f"  {t:28s} {contagens[t]:>10,}".replace(",", "."))
    if args.listar:
        return 0

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("ERRO: defina SUPABASE_DB_URL com a connection string do Supabase (Session pooler).", file=sys.stderr)
        return 1

    con = duckdb.connect(str(db), read_only=True)
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("ATTACH ? AS pg (TYPE postgres)", [url])
    con.execute(f"CALL postgres_execute('pg', 'DROP SCHEMA IF EXISTS {SCHEMA_PG} CASCADE; CREATE SCHEMA {SCHEMA_PG};')")
    falhas = []
    for t in objetos:
        try:
            con.execute(f'CREATE TABLE pg.{SCHEMA_PG}."{t}" AS SELECT * FROM main."{t}"')
            con.execute(f"CALL postgres_execute('pg', 'ALTER TABLE {SCHEMA_PG}.\"{t}\" ENABLE ROW LEVEL SECURITY')")
            n = con.execute(f'SELECT count(*) FROM pg.{SCHEMA_PG}."{t}"').fetchone()[0]
            marca = "OK " if n == contagens[t] else "DIVERGE"
            print(f"  {marca} {t}: {n} linhas")
            if n != contagens[t]:
                falhas.append(t)
        except Exception as e:  # uma tabela com tipo sem suporte não derruba as outras
            print(f"  FALHOU {t}: {e}", file=sys.stderr)
            falhas.append(t)
    con.close()
    if falhas:
        print(f"\nAtenção: problemas em {', '.join(falhas)}", file=sys.stderr)
        return 2
    print("\nPronto. RLS ligado em todas as tabelas, sem policy (a API pública não lê nada).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
