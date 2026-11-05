"""
Exporta o CSV de textos dos sites para o motor (Micael).

Uma linha por página coletada, juntando `pagina` (texto, status, bloqueio) com o
melhor candidato de `candidato_dominio` (maior confiança) para pegar cnpj e método.
Formato combinado com o Micael; texto truncado em ~5.000 caracteres.

Saída: enriquecimento/cache/textos_sites.csv (fora do Git).

Uso:
    python -m enriquecimento.exportar_textos [caminho_saida.csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import config, io_contratos

MAX_TEXTO_EXPORT = 5000
SAIDA_PADRAO = config.PASTA_ENRIQUECIMENTO / "cache" / "textos_sites.csv"

_CONSULTA = f"""
COPY (
    WITH melhor AS (
        SELECT dominio, cnpj, metodo,
               row_number() OVER (PARTITION BY dominio ORDER BY confianca DESC) AS rn
        FROM candidato_dominio
    )
    SELECT
        m.cnpj                                   AS cnpj,
        p.dominio                                AS site,
        m.metodo                                 AS metodo,
        p.url                                    AS url,
        p.tipo                                   AS tipo,
        left(p.texto, {MAX_TEXTO_EXPORT})        AS texto,
        p.status_http                            AS status_http,
        p.bloqueado                              AS bloqueado,
        p.coletado_em                            AS coletado_em
    FROM pagina p
    LEFT JOIN melhor m ON m.dominio = p.dominio AND m.rn = 1
    ORDER BY m.cnpj NULLS LAST, p.dominio, p.tipo
) TO '{{destino}}' (HEADER, DELIMITER ',')
"""


def exportar(con, destino: str | Path | None = None) -> Path:
    destino = Path(destino) if destino else SAIDA_PADRAO
    destino.parent.mkdir(parents=True, exist_ok=True)
    con.execute(_CONSULTA.format(destino=destino.as_posix()))
    return destino


def main(destino: str | None = None) -> None:
    con = io_contratos.conectar()
    try:
        io_contratos.criar_tabelas(con)
        n_pag = con.execute("SELECT count(*) FROM pagina").fetchone()[0]
        if n_pag == 0:
            print("[exportar] tabela pagina vazia — rode o pipeline antes.")
            return
        caminho = exportar(con, destino)
        total, bloq, com_cnpj = con.execute(
            """
            WITH melhor AS (SELECT dominio, cnpj,
                   row_number() OVER (PARTITION BY dominio ORDER BY confianca DESC) rn
                   FROM candidato_dominio)
            SELECT count(*), count(*) FILTER (WHERE p.bloqueado),
                   count(*) FILTER (WHERE m.cnpj IS NOT NULL)
            FROM pagina p LEFT JOIN melhor m ON m.dominio=p.dominio AND m.rn=1
            """
        ).fetchone()
        print(f"[exportar] {total} linha(s) -> {caminho}")
        print(f"[exportar] com cnpj: {com_cnpj} | bloqueadas: {bloq}")
    finally:
        con.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
