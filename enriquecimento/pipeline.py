"""
Pipeline da camada 2 (Roger), ponta a ponta:

    candidatos  ->  Método 1 (e-mail)  ->  coletor  ->  Método 2 (rodapé)
                                                     ->  Método 3 (nome × título)
                 ->  consolidação (melhor domínio por CNPJ)

Roda com uma conexão só no geno.duckdb. Usa o candidatos.parquet real quando
existir; senão, o CSV de exemplo.

Uso:
    python -m enriquecimento.pipeline [caminho_candidatos.csv]
"""
from __future__ import annotations

import sys

import httpx

from . import (
    coletor,
    config,
    io_contratos,
    metodo1_email,
    metodo2_rodape,
    metodo3_nome_titulo,
)


def _coletar(con) -> int:
    dominios = [d for (d,) in con.execute(
        "SELECT DISTINCT dominio FROM candidato_dominio ORDER BY dominio"
    ).fetchall()]
    if not dominios:
        print("[pipeline] nenhum domínio candidato para coletar.")
        return 0
    print(f"[pipeline] coletando {len(dominios)} domínio(s)...")
    total = 0
    with httpx.Client(headers={"User-Agent": config.USER_AGENT}) as client:
        for dom in dominios:
            total += coletor.gravar(con, coletor.coletar_dominio(client, dom))
    return total


def consolidar(con) -> None:
    """Melhor domínio por CNPJ (maior confiança), com os métodos que o sustentam."""
    rows = con.execute(
        """
        WITH por_par AS (
            SELECT cnpj, dominio,
                   max(confianca)              AS confianca,
                   string_agg(DISTINCT metodo, '+') AS metodos,
                   bool_or(validado)           AS validado
            FROM candidato_dominio
            GROUP BY cnpj, dominio
        ), ranqueado AS (
            SELECT *, row_number() OVER (PARTITION BY cnpj ORDER BY confianca DESC) AS rn
            FROM por_par
        )
        SELECT cnpj, dominio, confianca, metodos, validado
        FROM ranqueado WHERE rn = 1 ORDER BY confianca DESC, cnpj
        """
    ).fetchall()
    print("\n[consolidação] melhor domínio por CNPJ:")
    print(f"{'cnpj':<16} {'dominio':<28} {'conf':>5}  metodos")
    for cnpj, dominio, conf, metodos, _val in rows:
        print(f"{cnpj:<16} {dominio:<28} {conf:>5.2f}  {metodos}")


def _contagens(con) -> None:
    print("\n[contagens] candidato_dominio por método:")
    for metodo, n in con.execute(
        "SELECT metodo, count(*) FROM candidato_dominio GROUP BY metodo ORDER BY metodo"
    ).fetchall():
        print(f"  {metodo:<14} {n}")
    pag, bloq = con.execute(
        "SELECT count(*), count(*) FILTER (WHERE bloqueado) FROM pagina"
    ).fetchone()
    print(f"[contagens] paginas: {pag} (bloqueadas: {bloq})")


def main(caminho: str | None = None) -> None:
    candidatos = io_contratos.ler_candidatos(caminho)
    con = io_contratos.conectar()
    try:
        io_contratos.criar_tabelas(con)

        print("\n== Método 1 — domínio do e-mail ==")
        metodo1_email.gravar(con, metodo1_email.gerar_candidatos_email(candidatos))

        print("\n== Coletor ==")
        _coletar(con)

        print("\n== Método 2 — CNPJ no rodapé ==")
        metodo2_rodape.gravar(
            con, metodo2_rodape.gerar_candidatos_rodape(con, set(candidatos["cnpj"]))
        )

        print("\n== Método 3 — nome fantasia × título ==")
        metodo3_nome_titulo.gravar(
            con, metodo3_nome_titulo.gerar_candidatos_titulo(con, candidatos)
        )

        _contagens(con)
        consolidar(con)
    finally:
        con.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
